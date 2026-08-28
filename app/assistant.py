# -*- coding: utf-8 -*-
"""Pipeline complet (architecture RAG), avec mémoire conversationnelle
   par utilisateur, garde-fous contre les erreurs du LLM, "arrêts à
   proximité", comparateur d'itinéraires, géocodage de secours,
   trajets récents persistants en base, et désormais (25/08) la liste
   de toutes les lignes du réseau + le détail d'une ligne précise."""

import re
from app.nlp import charger_arrets, trouver_arret, normaliser, analyser
from app.recommandation import trouver_itineraire, comparer_itineraires, formater_comparaison
from app.llm import interpreter_message
from app.faits import (jours_de_service_connus, lignes_desservant,
                        correspondances_a, statistiques_reseau, prochains_departs,
                        arret_le_plus_proche, arrets_proches, coordonnees_arrets, geocoder_lieu,
                        ajouter_trajet_recent_bdd, trajets_recents_bdd,
                        toutes_les_lignes_avec_trajet, informations_ligne, chercher_synonyme)
from app.temps import jour_actuel, extraire_moment

_memoires = {}

def _nouvelle_memoire():
    return {
        "depart": None, "destination": None, "arrets": [], "clarification": None,
        "dernier_depart_resolu": None, "dernier_destination_resolue": None,
        "attente_proximite": False,
        "trajets_recents": [],
        "attente_selection_recent": False,
    }

def _obtenir_memoire(utilisateur):
    cle = utilisateur or "anonyme"
    if cle not in _memoires:
        _memoires[cle] = _nouvelle_memoire()
    return _memoires[cle]


MOTS_VIDES_COURTS = {"de", "du", "la", "le", "un", "une", "et", "au", "ce", "se",
                      "ne", "je", "tu", "il", "on", "ma", "ta", "sa", "en", "a"}

MARQUEURS_ITINERAIRE = ["je suis a", "je suis ", "je pars de", "je pars du", "en partant de",
                         "aller a", "me rendre a", "je veux aller", "depuis", "jusqu a"]

MOTS_PROXIMITE = ["proximite", "pres de moi", "autour de moi", "arrets proches",
                   "arret proche", "arrets a proximite", "quels arrets"]

MOTS_COMPARAISON = ["compare", "comparer", "plusieurs options", "quelles options",
                     "autres options", "d'autres options", "autre option"]

MOTS_RECENTS = ["trajets recents", "trajet recent", "mes trajets", "historique",
                 "mes favoris", "derniers trajets"]

# ---------- Liste globale des lignes (25/08) ----------
MOTS_TOUTES_LIGNES = ["toutes les lignes", "toute les lignes", "liste des lignes",
                       "quelles lignes existent", "quelles sont les lignes",
                       "combien de lignes", "les lignes du reseau"]

# Détecte une question sur UNE ligne précise, ex. "la ligne L1 c'est
# quelle ligne", "ou va la ligne L3", "que dessert la ligne l12"
MOTIF_LIGNE_PRECISE = re.compile(r"\bl(?:igne)?\s*-?\s*(\d{1,2})\b", re.IGNORECASE)
MOTS_QUESTION_LIGNE = ["c'est quelle", "quel trajet", "va ou", "mene a", "mene ou",
                        "dessert quoi", "va vers", "part de ou", "quel itineraire",
                        "quelle direction", "c est quelle ligne"]


def _contient_marqueur_itineraire(phrase_normalisee):
    return any(m in phrase_normalisee for m in MARQUEURS_ITINERAIRE)


def _detecter_question_ligne_precise(phrase, p_norm):
    """Renvoie la référence de ligne (ex. 'L3') si la phrase pose une
    question sur une ligne précise ('la ligne L3 c'est quelle ligne',
    'où va la ligne 12'), sinon None."""
    m = MOTIF_LIGNE_PRECISE.search(phrase)
    if not m:
        return None
    if not any(mot in p_norm for mot in MOTS_QUESTION_LIGNE) and "ligne" not in p_norm:
        return None
    return f"L{m.group(1)}"


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

    # Vérifie d'abord les surnoms locaux connus (27/08), ex. "Grand
    # Marché" -> "BIA", avant la recherche floue habituelle.
    synonyme_trouve = chercher_synonyme(lieu_brut)
    if synonyme_trouve and synonyme_trouve in arrets:
        return synonyme_trouve, None, None

    nom, score, methode = trouver_arret(lieu_brut, arrets)
    if methode == "texte-ambigu":
        return None, ", ".join(f"« {o} »" for o in nom), nom
    if nom:
        return nom, None, None

    position_lieu = geocoder_lieu(lieu_brut)
    if position_lieu:
        proche = arret_le_plus_proche(*position_lieu)
        if proche:
            nom_proche, _, _, distance = proche
            distance_m = round(distance * 111320)
            if distance_m <= 1500:
                return nom_proche, None, None

    return None, f"votre {nom_champ} (« {lieu_brut} » non reconnu, même après recherche géographique)", None


def _ajouter_trajet_recent(memoire, depart, destination, utilisateur=None):
    if utilisateur:
        ajouter_trajet_recent_bdd(utilisateur, depart, destination)
    else:
        paire = {"depart": depart, "destination": destination}
        memoire["trajets_recents"] = [
            t for t in memoire["trajets_recents"]
            if not (t["depart"] == depart and t["destination"] == destination)
        ]
        memoire["trajets_recents"].insert(0, paire)
        memoire["trajets_recents"] = memoire["trajets_recents"][:4]


def _obtenir_trajets_recents(memoire, utilisateur=None):
    if utilisateur:
        return trajets_recents_bdd(utilisateur)
    return memoire["trajets_recents"]


def _formater_trajets_recents(memoire, utilisateur=None):
    recents = _obtenir_trajets_recents(memoire, utilisateur)
    lignes = [f"{i+1}) « {t['depart']} » → « {t['destination']} »" for i, t in enumerate(recents)]
    return ("Vos trajets récents :\n" + "\n".join(lignes) +
            "\n\nTapez simplement le numéro (ex. « 1 ») pour reprendre l'un de ces trajets.")


def _formater_toutes_les_lignes():
    lignes = toutes_les_lignes_avec_trajet()
    if not lignes:
        return "Aucune ligne trouvée dans la base du réseau."
    corps = "\n".join(f"• {ref} : {trajet}" for ref, trajet in lignes)
    return (f"Voici les {len(lignes)} lignes du réseau SOTRAL :\n{corps}\n\n"
            f"Demandez « la ligne L3, où va-t-elle ? » pour le détail d'une ligne précise.")


def _traiter_resultat_deja_resolu(memoire, resultat, phrase, utilisateur=None):
    depart, methode_d = resultat["depart"], resultat["methode_depart"]
    destination, methode_a = resultat["destination"], resultat["methode_destination"]

    if methode_d == "texte-ambigu":
        options = ", ".join(f"« {o} »" for o in depart)
        memoire["clarification"] = {"champ": "depart", "options": depart,
                                     "raw_depart": None, "raw_destination": destination}
        return f"Plusieurs arrêts correspondent à votre départ : {options}. Lequel voulez-vous dire ?"
    if methode_a == "texte-ambigu":
        options = ", ".join(f"« {o} »" for o in destination)
        memoire["clarification"] = {"champ": "destination", "options": destination,
                                     "raw_depart": depart, "raw_destination": None}
        return f"Plusieurs arrêts correspondent à votre destination : {options}. Lequel voulez-vous dire ?"

    if not depart and memoire["dernier_depart_resolu"]:
        depart = memoire["dernier_depart_resolu"]
    if not destination and memoire["dernier_destination_resolue"]:
        destination = memoire["dernier_destination_resolue"]

    manquants = []
    if not depart: manquants.append("votre point de départ")
    if not destination: manquants.append("votre destination")
    if manquants:
        return (f"Je n'ai pas réussi à identifier {' et '.join(manquants)}. "
                f"Pourriez-vous préciser un arrêt ou un lieu connu du réseau SOTRAL ?")

    memoire["dernier_depart_resolu"] = depart
    memoire["dernier_destination_resolue"] = destination
    return _construire_reponse_itineraire(memoire, depart, destination, phrase, utilisateur)


def _resoudre_les_deux(memoire, depart_brut, destination_brut, arrets, phrase, position=None, utilisateur=None):
    if not depart_brut and memoire["dernier_depart_resolu"]:
        depart_brut = memoire["dernier_depart_resolu"]
    if not destination_brut and memoire["dernier_destination_resolue"]:
        destination_brut = memoire["dernier_destination_resolue"]

    if not depart_brut and position:
        lat, lon = position
        proche = arret_le_plus_proche(lat, lon)
        if proche:
            depart_brut = proche[0]

    depart, probleme_d, options_d = _verifier(depart_brut, "point de départ", arrets)
    destination, probleme_a, options_a = _verifier(destination_brut, "destination", arrets)

    if options_d:
        memoire["clarification"] = {"champ": "depart", "options": options_d,
                                     "raw_depart": depart_brut, "raw_destination": destination_brut}
        return f"Plusieurs arrêts correspondent à votre départ : {probleme_d}. Lequel voulez-vous dire ?"
    if options_a:
        memoire["clarification"] = {"champ": "destination", "options": options_a,
                                     "raw_depart": depart_brut, "raw_destination": destination_brut}
        return f"Plusieurs arrêts correspondent à votre destination : {probleme_a}. Lequel voulez-vous dire ?"

    manquants = [x for x in (probleme_d, probleme_a) if x]
    if manquants:
        resultat_regles = analyser(phrase, arrets)
        depart_secours = resultat_regles["depart"] if resultat_regles["methode_depart"] == "texte" else None
        destination_secours = resultat_regles["destination"] if resultat_regles["methode_destination"] == "texte" else None
        if (depart_secours or depart) and (destination_secours or destination):
            memoire["dernier_depart_resolu"] = depart_secours or depart
            memoire["dernier_destination_resolue"] = destination_secours or destination
            return _construire_reponse_itineraire(memoire, depart_secours or depart, destination_secours or destination, phrase, utilisateur)
        return (f"Je n'ai pas réussi à identifier {' et '.join(manquants)}. "
                f"Pourriez-vous préciser un arrêt ou un lieu connu du réseau SOTRAL ?")

    memoire["dernier_depart_resolu"] = depart
    memoire["dernier_destination_resolue"] = destination
    return _construire_reponse_itineraire(memoire, depart, destination, phrase, utilisateur)


def _construire_reponse_itineraire(memoire, depart, destination, phrase, utilisateur=None):
    itineraire = trouver_itineraire(depart, destination)
    if itineraire["type"] == "aucun":
        return itineraire["texte"]

    memoire["depart"], memoire["destination"] = depart, destination
    memoire["arrets"] = itineraire.get("arrets", [])
    memoire["clarification"] = None
    _ajouter_trajet_recent(memoire, depart, destination, utilisateur)

    type_moment, valeur = extraire_moment(phrase)
    jour = jour_actuel()

    if jour is None:
        note_horaire = "Nous ne disposons pas de données horaires pour la circulation du dimanche."
    elif type_moment is None:
        note_horaire = ("Précisez une heure ou un moment (ex. « vers 14h », « ce matin », « maintenant ») "
                         "pour que je vous indique le prochain départ exact. Vous pouvez aussi demander "
                         "« compare » pour voir d'autres options, ou « mes trajets récents ».")
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


def dernier_itineraire_carte(utilisateur=None):
    memoire = _obtenir_memoire(utilisateur)
    return coordonnees_arrets(memoire.get("arrets") or [])


def repondre(phrase, arrets=None, position=None, utilisateur=None):
    memoire = _obtenir_memoire(utilisateur)
    if arrets is None:
        arrets = charger_arrets()
    p = phrase.lower()
    p_norm = normaliser(phrase)
    phrase_brute = phrase.strip()

    if memoire["attente_selection_recent"]:
        memoire["attente_selection_recent"] = False
        chiffre = "".join(c for c in phrase_brute if c.isdigit())
        if chiffre and chiffre.isdigit():
            index = int(chiffre) - 1
            recents = _obtenir_trajets_recents(memoire, utilisateur)
            if 0 <= index < len(recents):
                t = recents[index]
                return _construire_reponse_itineraire(memoire, t["depart"], t["destination"], phrase, utilisateur)

    if memoire["clarification"]:
        clar = memoire["clarification"]
        choix = _choisir_parmi_options(phrase, clar["options"])
        if choix:
            depart_brut = choix if clar["champ"] == "depart" else clar["raw_depart"]
            destination_brut = choix if clar["champ"] == "destination" else clar["raw_destination"]
            memoire["clarification"] = None
            return _resoudre_les_deux(memoire, depart_brut, destination_brut, arrets, phrase, position, utilisateur)
        memoire["clarification"] = None

    if any(m in p for m in ["dimanche", "quel jour", "quels jours", "circul", "roule", "service"]):
        jours = jours_de_service_connus()
        return (f"D'après nos données, les bus SOTRAL circulent : {', '.join(jours)}. "
                f"Nous n'avons pas de donnée confirmée pour les autres jours.")

    # ---------- Liste globale de toutes les lignes (25/08) ----------
    if any(m in p_norm for m in MOTS_TOUTES_LIGNES):
        return _formater_toutes_les_lignes()

    # ---------- Détail d'une ligne précise (25/08) ----------
    ref_ligne = _detecter_question_ligne_precise(phrase, p_norm)
    if ref_ligne:
        trajet = informations_ligne(ref_ligne)
        if trajet:
            return f"La ligne {ref_ligne} circule sur le trajet : {trajet}."
        return f"Je ne trouve pas de ligne référencée « {ref_ligne} » dans le réseau SOTRAL."

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

    if memoire["attente_proximite"] and position:
        memoire["attente_proximite"] = False
        lat, lon = position
        proches = arrets_proches(lat, lon, limite=5)
        if not proches:
            return "Je n'ai pas réussi à trouver d'arrêt proche de votre position."
        liste = "\n".join(f"{i+1}. « {nom} » — environ {dist} m" for i, (nom, dist) in enumerate(proches))
        return f"Voici les arrêts les plus proches de votre position :\n{liste}"

    if any(m in p_norm for m in MOTS_PROXIMITE):
        if not position:
            memoire["attente_proximite"] = True
            return ("Pour vous indiquer les arrêts les plus proches, j'ai besoin de votre position. "
                     "Autorisez la géolocalisation dans votre navigateur, puis renvoyez n'importe quel message.")
        lat, lon = position
        proches = arrets_proches(lat, lon, limite=5)
        if not proches:
            return "Je n'ai pas réussi à trouver d'arrêt proche de votre position."
        liste = "\n".join(f"{i+1}. « {nom} » — environ {dist} m" for i, (nom, dist) in enumerate(proches))
        return f"Voici les arrêts les plus proches de votre position :\n{liste}"

    if any(m in p_norm for m in MOTS_COMPARAISON):
        depart_ref = memoire["dernier_depart_resolu"]
        dest_ref = memoire["dernier_destination_resolue"]
        if depart_ref and dest_ref:
            options = comparer_itineraires(depart_ref, dest_ref)
            return formater_comparaison(depart_ref, dest_ref, options)
        return ("Je n'ai pas encore de trajet en mémoire à comparer. "
                "Précisez d'abord un départ et une destination.")

    if any(m in p_norm for m in MOTS_RECENTS):
        recents = _obtenir_trajets_recents(memoire, utilisateur)
        if not recents:
            return "Vous n'avez pas encore de trajet récent enregistré. Demandez-moi un itinéraire pour commencer !"
        memoire["attente_selection_recent"] = True
        return _formater_trajets_recents(memoire, utilisateur)

    comprehension = interpreter_message(phrase)
    intention = comprehension.get("intention")
    depart_brut = comprehension.get("depart")
    destination_brut = comprehension.get("destination")

    if intention in ("salutation", "autre") and _contient_marqueur_itineraire(p_norm):
        resultat_regles = analyser(phrase, arrets)
        if resultat_regles["depart"] or resultat_regles["destination"]:
            return _traiter_resultat_deja_resolu(memoire, resultat_regles, phrase, utilisateur)

    if intention == "itineraire" and (not depart_brut or not destination_brut) and _contient_marqueur_itineraire(p_norm):
        resultat_regles = analyser(phrase, arrets)
        if not depart_brut and resultat_regles["methode_depart"] == "texte-ambigu":
            options = resultat_regles["depart"]
            memoire["clarification"] = {"champ": "depart", "options": options,
                                         "raw_depart": None, "raw_destination": destination_brut}
            return (f"Plusieurs arrêts correspondent à votre départ : "
                     f"{', '.join(f'« {o} »' for o in options)}. Lequel voulez-vous dire ?")
        if not depart_brut and resultat_regles["depart"]:
            depart_brut = resultat_regles["depart"]

        if not destination_brut and resultat_regles["methode_destination"] == "texte-ambigu":
            options = resultat_regles["destination"]
            memoire["clarification"] = {"champ": "destination", "options": options,
                                         "raw_depart": depart_brut, "raw_destination": None}
            return (f"Plusieurs arrêts correspondent à votre destination : "
                     f"{', '.join(f'« {o} »' for o in options)}. Lequel voulez-vous dire ?")
        if not destination_brut and resultat_regles["destination"]:
            destination_brut = resultat_regles["destination"]

    type_moment, _ = extraire_moment(phrase)
    if not depart_brut and not destination_brut and type_moment and memoire["depart"] and memoire["destination"]:
        return _construire_reponse_itineraire(memoire, memoire["depart"], memoire["destination"], phrase, utilisateur)

    if intention == "salutation":
        return comprehension.get("reponse") or "Comment puis-je vous aider ?"

    if intention == "autre":
        return ("Cette information (par exemple les tarifs) ne figure pas dans les données "
                "du réseau SOTRAL dont nous disposons pour ce prototype. Je peux vous renseigner "
                "sur les lignes, les arrêts, les horaires et les correspondances du réseau.")

    if not depart_brut and not destination_brut and memoire["depart"] and memoire["destination"]:
        return ("Je n'ai pas identifié de nouvelle demande. Voulez-vous continuer sur le trajet "
                f"« {memoire['depart']} → {memoire['destination']} », ou en préciser un autre ?")

    return _resoudre_les_deux(memoire, depart_brut, destination_brut, arrets, phrase, position, utilisateur)
