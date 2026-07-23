# -*- coding: utf-8 -*-
"""Module NLP v2 — corrige deux problèmes observés en v1 :
   1) marqueurs de départ/destination détectés quel que soit leur ordre dans la phrase
   2) suppression des petits mots parasites (le, la, les, l') avant la comparaison floue"""

import re
import unicodedata
import psycopg2
from rapidfuzz import process, fuzz

def charger_arrets():
    connexion = psycopg2.connect(
        host="localhost", dbname="sotral_db",
        user="sotral_user", password="merci_p@p@10")
    curseur = connexion.cursor()
    curseur.execute("SELECT DISTINCT nom FROM arrets;")
    arrets = [ligne[0] for ligne in curseur.fetchall()]
    curseur.close(); connexion.close()
    return arrets

def normaliser(texte):
    texte = unicodedata.normalize("NFD", texte.lower())
    texte = texte.encode("ascii", "ignore").decode()
    return " ".join(texte.split())

MOTS_VIDES = {"le", "la", "les", "l", "du", "de", "des", "un", "une"}
def nettoyer_fragment(fragment):
    """Retire les petits mots parasites en début de fragment ('le chu' -> 'chu')."""
    mots = fragment.strip(" .!?,").split()
    while mots and mots[0] in MOTS_VIDES:
        mots.pop(0)
    return " ".join(mots)

def trouver_arret(fragment, arrets, seuil=70):
    fragment = nettoyer_fragment(fragment or "")
    if not fragment:
        return None, 0
    candidats = {a: normaliser(a).replace("arret ", "") for a in arrets}
    resultat = process.extractOne(normaliser(fragment), candidats, scorer=fuzz.WRatio)
    if resultat and resultat[1] >= seuil:
        return resultat[2], round(resultat[1])
    return None, 0

MARQUEURS = [
    ("depart", r"je suis a"), ("depart", r"je pars du"), ("depart", r"je pars de"),
    ("depart", r"en partant de"), ("depart", r"depuis"), ("depart", r"\bde\b"),
    ("destination", r"je veux aller a"), ("destination", r"je souhaite me rendre a"),
    ("destination", r"aller a"), ("destination", r"me rendre a"),
    ("destination", r"jusqu'a"), ("destination", r"jusqu a"),
    ("destination", r"a destination de"), ("destination", r"\bvers\b"), ("destination", r"\bpour\b"),
]

def analyser(phrase, arrets):
    p = normaliser(phrase)

    occurrences = []
    for kind, motif in MARQUEURS:
        for m in re.finditer(motif, p):
            occurrences.append((m.start(), m.end(), kind))
    occurrences.sort(key=lambda x: x[0])

    retenues = []
    for start, end, kind in occurrences:
        if not any(s <= start and end <= e for s, e, k in retenues):
            retenues.append((start, end, kind))
    retenues.sort(key=lambda x: x[0])

    fragments = {"depart": None, "destination": None}
    for i, (start, end, kind) in enumerate(retenues):
        fin_segment = retenues[i + 1][0] if i + 1 < len(retenues) else len(p)
        fragments[kind] = p[end:fin_segment]

    depart, score_d = trouver_arret(fragments["depart"], arrets)
    destination, score_a = trouver_arret(fragments["destination"], arrets)
    return {"depart": depart, "score_depart": score_d,
            "destination": destination, "score_destination": score_a}

if __name__ == "__main__":
    arrets = charger_arrets()
    print(f"{len(arrets)} arrêts chargés depuis la base.\n")
    phrases_test = [
        "Je suis à Adidogomé et je veux aller à BIA",
        "je pars de zangera pour le CHU",
        "comment aller a todman depuis atikoume ?",
        "Je souhaite me rendre à la douane adidogome",
    ]
    for phrase in phrases_test:
        r = analyser(phrase, arrets)
        print(f"Phrase : {phrase}")
        print(f"  Départ      : {r['depart']} (score {r['score_depart']})")
        print(f"  Destination : {r['destination']} (score {r['score_destination']})\n")
