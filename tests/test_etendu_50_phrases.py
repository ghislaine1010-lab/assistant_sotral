# -*- coding: utf-8 -*-
"""Jeu de test étendu (50 phrases) -- deuxième vague, pour une évaluation
   encore plus robuste, sur un échantillon plus large et plus varié
   (02/09), suite à la recommandation du directeur de mémoire."""
from app.assistant import repondre
from app.nlp import charger_arrets

CAS_DE_TEST = [
    # --- Formulations bien orthographiées (12) ---
    ("Je suis à Bè Lagune et je veux aller à BIA", "reussite"),
    ("Je pars d'Adidogomé pour aller à Kodjoviakopé", "reussite"),
    ("Je suis à Adakpamé, je veux aller à Agoè", "reussite"),
    ("Depuis Tokoin, comment aller à Nyékonakpoè ?", "reussite"),
    ("Je suis à BIA et je veux aller à Bè", "reussite"),
    ("Comment aller de Totsi à Agbalépédogan ?", "reussite"),
    ("Je pars de Bè vers Akodésséwa", "reussite"),
    ("Je suis à Hédzranawoé, je vais à Amoutivé", "reussite"),
    ("Depuis Bè, je veux me rendre à Adidogomé", "reussite"),
    ("Trajet de Kodjoviakopé à Tokoin", "reussite"),
    ("Je suis à la Poste et je veux aller à BIA", "reussite"),
    ("Depuis Agoè, comment rejoindre Bè ?", "reussite"),

    # --- Fautes d'orthographe et accents manquants (12) ---
    ("Je suis a Be et je veux aller a BIA", "reussite"),
    ("je suis a adidogome je veux aller a kodjoviakope", "reussite"),
    ("Je suis a Adakpame, je veux aller a Ago", "reussite"),
    ("depuis Tokoin comment aller a Nyekonakpoe", "reussite"),
    ("je pars de be vers akodessewa", "reussite"),
    ("je suis a hedzranawoe je vais a amoutive", "reussite"),
    ("trajet de kodjoviakope a tokoin", "reussite"),
    ("Je suis a BIa et je veux aller a  Be", "reussite"),
    ("je suis a la poste je veux aller a bia", "reussite"),
    ("depuis ago comment rejoindre be", "reussite"),
    ("je suis a totsi je vais a agbalepedogan", "reussite"),
    ("Je Suis À BÈ ET JE VEUX ALLER À BIA", "reussite"),

    # --- Synonymes locaux (4) ---
    ("Je suis au Grand Marché et je veux aller à Total Atikoumé", "reussite"),
    ("Je suis au grand marche, je veux aller a Adidogome", "reussite"),
    ("Depuis le Grand Marché, comment aller à Bè ?", "reussite"),
    ("je suis au GRAND MARCHE et je vais a agoe", "reussite"),

    # --- Ambiguïtés légitimes (8) ---
    ("Je suis à Bè et je veux aller à Adidogomé", "ambiguite_attendue"),
    ("Je pars de la gare vers le marché", "ambiguite_attendue"),
    ("Je suis au lycée et je veux aller à l'école", "ambiguite_attendue"),
    ("Depuis l'église, comment aller à la pharmacie ?", "ambiguite_attendue"),
    ("Je suis au carrefour et je vais à la station", "ambiguite_attendue"),
    ("Je pars du marché vers l'hôpital", "ambiguite_attendue"),
    ("Depuis l'arrêt, je veux aller au centre", "ambiguite_attendue"),
    ("Je suis à Adakpamé, je vais à Agoè Assiyéyé", "ambiguite_attendue"),

    # --- Formulations très variées (10) ---
    ("Quel bus prendre pour aller de Bè à BIA ?", "reussite"),
    ("Aide-moi à aller d'Adidogomé à Kodjoviakopé", "reussite"),
    ("Itinéraire Bè -> BIA s'il te plaît", "reussite"),
    ("Je veux aller à Agoè en partant de Adakpamé", "reussite"),
    ("Bè jusqu'à BIA, comment faire ?", "reussite"),
    ("Salut, je suis à Tokoin, je veux aller à Nyékonakpoè", "reussite"),
    ("Bonjour, depuis Hédzranawoé comment je vais à Amoutivé ?", "reussite"),
    ("BIA vers Bè svp", "reussite"),
    ("je cherche a aller a bia je suis a be", "reussite"),
    ("y a moyen d'aller de kodjoviakope a tokoin", "reussite"),

    # --- Cas limites : phrases très courtes ou incomplètes (4) ---
    ("Bè BIA", "reussite"),
    ("Adidogomé Kodjoviakopé", "reussite"),
    ("Je suis à Bè", "ambiguite_attendue"),
    ("Je veux aller à BIA", "ambiguite_attendue"),
]


def executer():
    arrets = charger_arrets()
    resultats = []
    for phrase, categorie in CAS_DE_TEST:
        try:
            reponse = repondre(phrase, arrets)
        except Exception as e:
            print(f"\n*** ERREUR sur la phrase : « {phrase} » ***")
            print(f"*** Type : {type(e).__name__} — {e} ***\n")
            resultats.append((phrase, categorie, False, f"ERREUR: {e}"))
            continue
        itineraire_calcule = ("Montez à" in reponse or "Ligne L" in reponse
                               or "changement" in reponse.lower())
        ambiguite_detectee = ("Lequel voulez-vous dire" in reponse
                               or "correspondent" in reponse
                               or "pourriez-vous préciser" in reponse.lower()
                               or "identifier" in reponse.lower())
        succes = itineraire_calcule or ambiguite_detectee
        resultats.append((phrase, categorie, succes, reponse[:80]))

    total = len(resultats)
    reussites = sum(1 for r in resultats if r[2])

    print(f"\n{'='*70}")
    print(f"RÉSULTAT GLOBAL : {reussites}/{total} ({100*reussites/total:.1f}%)")
    print(f"{'='*70}\n")

    for phrase, categorie, succes, extrait in resultats:
        marque = "✅" if succes else "❌"
        print(f"{marque} [{categorie:20s}] {phrase}")
        if not succes:
            print(f"     -> Réponse obtenue : {extrait}...")

    return reussites, total


if __name__ == "__main__":
    executer()
