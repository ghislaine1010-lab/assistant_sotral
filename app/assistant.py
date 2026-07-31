# -*- coding: utf-8 -*-
"""Pipeline complet (architecture RAG), avec deux garde-fous contre les
   erreurs d'extraction du LLM (variabilité documentée) :
   1) intention mal classée (salutation/autre) malgré un marqueur clair
      d'itinéraire -> on bascule entièrement sur nos règles (app.nlp.analyser) ;
   2) intention correcte mais extraction PARTIELLE (un des deux lieux
      manque, ex. "me rendre à" perturbant le LLM) -> on comble le trou
      manquant avec nos règles, sans toucher au lieu que le LLM a bien trouvé."""

from app.nlp import charger_arrets, trouver_arret, normaliser, analyser
from app.recommandation import trouver_itineraire
from app.llm import interpreter_message
from app.faits import (jours_de_service_connus, lignes_desservant,
                        correspondances_a, statistiques_reseau, prochains_departs,
                        arret_le_plus_proche, coordonnees_arrets)
from app.temps import jour_actuel, extraire_moment

_memoire = {
    "depart": None, "destination": None, "arrets": [], "clarification": None,
    "dernier_depart_resolu": None, "dernier_destination_resolue": None,
}

MOTS_VIDES_COURTS = {"de", "du", "la", "le", "un", "une", "et", "au", "ce", "se",
                      "ne", "je", "tu", "il", "on", "ma", "ta", "sa", "en", "a"}

MARQUEURS_ITINERAIRE = ["je suis a", "je suis ", "je pars de", "je pars du", "en partant de",
                         "aller a", "me rendre a", "je veux aller", "depuis", "jusqu a"]

def _contient_marqueur_itineraire(phrase_normalisee):
    return any(m in phrase_normalisee for m in MARQUEURS_ITINERAIRE)


def _trouver_arret_mentionne(phrase, arrets):
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


def _choisir_parmi_options(phrase, options):
    p_norm = normaliser(phrase)
    mots_phrase = set(p_norm.split())
    meilleur, meilleur_score = None, 0
    for option in options:
        mots_option = set(normaliser(option).replace("arret ", "").split())
        communs = {m for m in (mots_option & mots_phrase)
                   if len(m) >= 2 and m not in MOTS_VIDES_COURTS}
        if communs and len(communs) > meilleur_score:
            meilleur_score = len(communs)
            meilleur = option
    return meilleur


def _verifier(lieu_brut, nom_champ, arrets):
    if not lieu_brut:
        return None, f"votre {nom_champ}", None
    if lieu_brut in arrets:
        return lieu_brut, None, None
    nom, score, methode = trouver_arret(lieu_brut, arrets)
    if methode == "texte-ambigu":
        return None, ", ".join(f"« {o} »" for o in nom), nom
    if nom:
        return nom, None, None
    return None, f"votre {nom_champ} (« {lieu_brut} » non reconnu)", None


def _traiter_resultat_deja_resolu(resultat, phrase):
    global _memoire
    depart, methode_d = resultat["depart"], resultat["methode_depart"]
    destination, methode_a = resultat["destination"], resultat["methode_destination"]

    if methode_d == "texte-ambigu":
        options = ", ".join(f"« {o} »" for o in depart)
        _memoire["clarification"] = {"champ": "depart", "options": depart,
                                      "raw_depart": None, "raw_destination": destination}
        return f"Plusieurs arrêts correspondent à votre départ : {options}. Lequel voulez-vous dire ?"
    if methode_a == "texte-ambigu":
        options = ", ".join(f"« {o} »" for o in destination)
        _memoire["clarification"] = {"champ": "destination", "options": destination,
                                      "raw_depart": depart, "raw_destination": None}
        return f"Plusieurs arrêts correspondent à votre destination : {options}. Lequel voulez-vous dire ?"

    if not depart and _memoire["dernier_depart_resolu"]:
        depart = _memoire["dernier_depart_resolu"]
    if not destination and _memoire["dernier_destination_resolue"]:
        destination = _memoire["dernier_destination_resolue"]

    manquants = []
    if not depart: manquants.append("votre point de départ")
    if not destination: manquants.append("votre destination")
    if manquants:
        return (f"Je n'ai pas réussi à identifier {' et '.join(manquants)}. "
                f"Pourriez-vous préciser un arrêt ou un lieu connu du réseau SOTRAL ?")

    _memoire["dernier_depart_resolu"] = depart
    _memoire["dernier_destination_resolue"] = destination
    return _construire_reponse_itineraire(depart, destination, phrase)


def _resoudre_les_deux(depart_brut, destination_brut, arrets, phrase, position=None):
    global _memoire

    if not depart_brut and _memoire["dernier_depart_resolu"]:
        depart_brut = _memoire["dernier_depart_resolu"]
    if not destination_brut and _memoire["dernier_destination_resolue"]:
        destination_brut = _memoire["dernier_destination_resolue"]

    if not depart_brut and position:
        lat, lon = position
        proche = arret_le_plus_proche(lat, lon)
        if proche:
            depart_brut = proche[0]

    depart, probleme_d, options_d = _verifier(depart_brut, "point de départ", arrets)
    destination, probleme_a, options_a = _verifier(destination_brut, "destination", arrets)

    if options_d:
        _memoire["clarification"] = {"champ": "depart", "options": options_d,
                                      "raw_depart": depart_brut, "raw_destination": destination_brut}
        return f"Plusieurs arrêts correspondent à votre départ : {probleme_d}. Lequel voulez-vous dire ?"
    if options_a:
        _memoire["clarification"] = {"champ": "destination", "options": options_a,
                                      "raw_depart": depart_brut, "raw_destination": destination_brut}
        return f"Plusieurs arrêts correspondent à votre destination : {probleme_a}. Lequel voulez-vous dire ?"

    manquants = [x for x in (probleme_d, probleme_a) if x]
    if manquants:
        return (f"Je n'ai pas réussi à identifier {' et '.join(manquants)}. "
                f"Pourriez-vous préciser un arrêt ou un lieu connu du réseau SOTRAL ?")

    _memoire["dernier_depart_resolu"] = depart
    _memoire["dernier_destination_resolue"] = destination
    return _construire_reponse_itineraire(depart, destination, phrase)


def _construire_reponse_itineraire(depart, destination, phrase):
    global _memoire
    itineraire = trouver_itineraire(depart, destination)
    if itineraire["type"] == "aucun":
        return itineraire["texte"]

    _memoire["depart"], _memoire["destination"] = depart, destination
    _memoire["arrets"] = itineraire.get("arrets", [])
    _memoire["clarification"] = None

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


def dernier_itineraire_carte():
    return coordonnees_arrets(_memoire.get("arrets") or [])


def repondre(phrase, arrets=None, position=None):
    global _memoire
    if arrets is None:
        arrets = charger_arrets()
    p = phrase.lower()
    p_norm = normaliser(phrase)

    if _memoire["clarification"]:
        clar = _memoire["clarification"]
        choix = _choisir_parmi_options(phrase, clar["options"])
        if choix:
            depart_brut = choix if clar["champ"] == "depart" else clar["raw_depart"]
            destination_brut = choix if clar["champ"] == "destination" else clar["raw_destination"]
            _memoire["clarification"] = None
            return _resoudre_les_deux(depart_brut, destination_brut, arrets, phrase, position)
        _memoire["clarification"] = None

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

    comprehension = interpreter_message(phrase)
    intention = comprehension.get("intention")
    depart_brut = comprehension.get("depart")
    destination_brut = comprehension.get("destination")

    # ---------- Garde-fou 1 : intention mal classée malgré un marqueur clair ----------
    if intention in ("salutation", "autre") and _contient_marqueur_itineraire(p_norm):
        resultat_regles = analyser(phrase, arrets)
        if resultat_regles["depart"] or resultat_regles["destination"]:
            return _traiter_resultat_deja_resolu(resultat_regles, phrase)

    # ---------- Garde-fou 2 : intention correcte mais extraction PARTIELLE ----------
    if intention == "itineraire" and (not depart_brut or not destination_brut) and _contient_marqueur_itineraire(p_norm):
        resultat_regles = analyser(phrase, arrets)
        if not depart_brut and resultat_regles["methode_depart"] == "texte-ambigu":
            options = resultat_regles["depart"]
            _memoire["clarification"] = {"champ": "depart", "options": options,
                                          "raw_depart": None, "raw_destination": destination_brut}
            return (f"Plusieurs arrêts correspondent à votre départ : "
                     f"{', '.join(f'« {o} »' for o in options)}. Lequel voulez-vous dire ?")
        if not depart_brut and resultat_regles["depart"]:
            depart_brut = resultat_regles["depart"]

        if not destination_brut and resultat_regles["methode_destination"] == "texte-ambigu":
            options = resultat_regles["destination"]
            _memoire["clarification"] = {"champ": "destination", "options": options,
                                          "raw_depart": depart_brut, "raw_destination": None}
            return (f"Plusieurs arrêts correspondent à votre destination : "
                     f"{', '.join(f'« {o} »' for o in options)}. Lequel voulez-vous dire ?")
        if not destination_brut and resultat_regles["destination"]:
            destination_brut = resultat_regles["destination"]

    type_moment, _ = extraire_moment(phrase)
    if not depart_brut and not destination_brut and type_moment and _memoire["depart"] and _memoire["destination"]:
        return _construire_reponse_itineraire(_memoire["depart"], _memoire["destination"], phrase)

    if intention == "salutation":
        return comprehension.get("reponse") or "Comment puis-je vous aider ?"

    if intention == "autre":
        return ("Cette information (par exemple les tarifs) ne figure pas dans les données "
                "du réseau SOTRAL dont nous disposons pour ce prototype. Je peux vous renseigner "
                "sur les lignes, les arrêts, les horaires et les correspondances du réseau.")

    if not depart_brut and not destination_brut and _memoire["depart"] and _memoire["destination"]:
        return ("Je n'ai pas identifié de nouvelle demande. Voulez-vous continuer sur le trajet "
                f"« {_memoire['depart']} → {_memoire['destination']} », ou en préciser un autre ?")

    return _resoudre_les_deux(depart_brut, destination_brut, arrets, phrase, position)
