# -*- coding: utf-8 -*-
"""Pipeline complet (architecture RAG) :
   - questions déterministes (lignes, correspondances, stats, jours) :
     détectées AVANT le LLM, réponse directe depuis la base ;
   - salutation / autre conversation : gérées par le LLM ;
   - itinéraire : LLM propose, la base VÉRIFIE les lieux, utilise la
     géolocalisation (SF5) si aucun départ n'est mentionné, et fournit
     les horaires réels si un moment est précisé (SF4)."""

from app.nlp import charger_arrets, trouver_arret
from app.recommandation import trouver_itineraire
from app.llm import interpreter_message
from app.faits import (jours_de_service_connus, lignes_desservant,
                        correspondances_a, statistiques_reseau, prochains_departs,
                        arret_le_plus_proche)
from app.temps import jour_actuel, extraire_moment

def _trouver_arret_mentionne(phrase, arrets):
    from app.nlp import normaliser
    p_norm = normaliser(phrase)
    mots_phrase = set(p_norm.split())
    meilleur, meilleur_score = None, 0
    for arret in arrets:
        mots_arret = set(normaliser(arret).replace("arret ", "").split())
        communs = {m for m in (mots_arret & mots_phrase) if len(m) >= 3}
        if communs and len(communs) > meilleur_score:
            meilleur_score = len(communs)
            meilleur = arret
    return meilleur

def repondre(phrase, arrets=None, position=None):
    """position : tuple (latitude, longitude) si l'usager a autorisé
       sa géolocalisation ; sert de point de départ par défaut (SF5)
       si aucun départ n'est mentionné dans la phrase."""
    if arrets is None:
        arrets = charger_arrets()
    p = phrase.lower()

    # ========== Questions déterministes, traitées AVANT le LLM ==========
    if any(m in p for m in ["dimanche", "quel jour", "quels jours", "circul", "roule", "service"]):
        jours = jours_de_service_connus()
        return (f"D'après nos données, les bus SOTRAL circulent : {', '.join(jours)}. "
                f"Nous n'avons pas de donnée confirmée pour les autres jours.")

    if any(m in p for m in ["combien de ligne", "combien de bus", "combien d'arret",
                             "taille du reseau", "nombre de ligne"]):
        s = statistiques_reseau()
        return (f"Notre base couvre {s['lignes']} lignes, {s['arrets']} arrêts "
                f"et {s['horaires']} horaires enregistrés pour le réseau SOTRAL.")

    if any(m in p for m in ["quelle ligne", "quelles lignes", "ligne passe", "ligne dessert"]):
        arret = _trouver_arret_mentionne(phrase, arrets)
        if arret:
            lignes = lignes_desservant(arret)
            if lignes:
                return f"L'arrêt « {arret} » est desservi par la (les) ligne(s) : {', '.join(lignes)}."
        return "Pouvez-vous préciser le nom de l'arrêt qui vous intéresse ?"

    if any(m in p for m in ["correspondance", "changer de bus", "changement"]):
        arret = _trouver_arret_mentionne(phrase, arrets)
        if arret:
            lignes = correspondances_a(arret)
            if lignes:
                return f"À l'arrêt « {arret} », vous pouvez changer entre les lignes : {', '.join(lignes)}."
        return "Pouvez-vous préciser à quel arrêt vous souhaitez connaître les correspondances ?"

    # ========== Sinon, on passe par le LLM (salutation / itinéraire / autre) ==========
    comprehension = interpreter_message(phrase)
    intention = comprehension.get("intention")

    if intention == "salutation":
        return comprehension.get("reponse") or "Comment puis-je vous aider ?"

    if intention == "autre":
        return ("Cette information (par exemple les tarifs) ne figure pas dans les données "
                "du réseau SOTRAL dont nous disposons pour ce prototype. Je peux vous renseigner "
                "sur les lignes, les arrêts, les horaires et les correspondances du réseau.")

    # ========== Itinéraire : vérification des lieux proposés par le LLM ==========
    depart_brut = comprehension.get("depart")
    destination_brut = comprehension.get("destination")

    # ---------- SF5 : géolocalisation, utilisée seulement si aucun départ n'est mentionné ----------
    if not depart_brut and position:
        lat, lon = position
        proche = arret_le_plus_proche(lat, lon)
        if proche:
            depart_brut = proche[0]  # le nom de l'arrêt trouvé devient le départ

    def verifier(lieu_brut, nom_champ):
        if not lieu_brut:
            return None, f"votre {nom_champ}"
        nom, score, methode = trouver_arret(lieu_brut, arrets)
        if methode == "texte-ambigu":
            return "AMBIGU", ", ".join(f"« {o} »" for o in nom)
        if nom:
            return nom, None
        return None, f"votre {nom_champ} (« {lieu_brut} » non reconnu)"

    depart, probleme_d = verifier(depart_brut, "point de départ")
    destination, probleme_a = verifier(destination_brut, "destination")

    if depart == "AMBIGU":
        return f"Plusieurs arrêts correspondent à votre départ : {probleme_d}. Lequel voulez-vous dire ?"
    if destination == "AMBIGU":
        return f"Plusieurs arrêts correspondent à votre destination : {probleme_a}. Lequel voulez-vous dire ?"
    manquants = [x for x in (probleme_d, probleme_a) if x]
    if manquants:
        return (f"Je n'ai pas réussi à identifier {' et '.join(manquants)}. "
                f"Pourriez-vous préciser un arrêt ou un lieu connu du réseau SOTRAL ?")

    itineraire = trouver_itineraire(depart, destination)
    if itineraire["type"] == "aucun":
        return itineraire["texte"]

    # ---------- Horaires réels, uniquement si un moment est précisé (SF4) ----------
    type_moment, valeur = extraire_moment(phrase)
    jour = jour_actuel()

    if jour is None:
        note_horaire = "Nous ne disposons pas de données horaires pour la circulation du dimanche."
    elif type_moment is None:
        note_horaire = ("Précisez une heure ou un moment (ex. « vers 14h », « ce matin », « maintenant ») "
                         "pour que je vous indique le prochain départ exact.")
    else:
        ref_principale = itineraire["lignes"][0]
        deps = prochains_departs(ref_principale, jour, type_moment, valeur)
        if deps:
            liste = "; ".join(f"{h.strftime('%Hh%M') if hasattr(h,'strftime') else h} ({per.lower()})"
                               for sens, per, h in deps)
            note_horaire = (f"Sur la ligne {ref_principale} ({jour}), prochain(s) départ(s) connus : {liste}. "
                             f"(Le sens exact de circulation associé à chaque horaire n'est pas garanti "
                             f"par les données sources.)")
        else:
            note_horaire = f"Aucun horaire connu pour la ligne {ref_principale} à ce moment ({jour})."

    return itineraire["texte"] + "\n" + note_horaire


if __name__ == "__main__":
    arrets = charger_arrets()
    phrases_test = [
        "Bonjour, comment vas-tu ?",
        "Je suis à Adidogomé et je veux aller à BIA",
        "je veux partir de Adidogomé vers BIA à 7h",
        "quelles lignes desservent BIA ?",
        "quelles correspondances à BIA ?",
        "combien de lignes avez-vous au total ?",
        "quel est le prix du ticket ?",
    ]
    for phrase in phrases_test:
        print(f"\nUsager : {phrase}")
        print("Assistant :", repondre(phrase, arrets))

    print("\nUsager (géolocalisé, sans préciser de départ) : « Je veux aller à BIA »")
    print("Assistant :", repondre("Je veux aller à BIA", arrets, position=(6.1319, 1.2228)))
