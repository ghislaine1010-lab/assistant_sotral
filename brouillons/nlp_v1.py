# -*- coding: utf-8 -*-
"""Module NLP v1 — extraction du départ et de la destination
   dans une phrase en langage naturel (assistant SOTRAL).
   Répond aux spécifications SF1 (compréhension) et SF2 (tolérance aux fautes)."""

import re
import unicodedata
import psycopg2
from rapidfuzz import process, fuzz

# ---------- 1. Charger les noms d'arrêts depuis la base ----------
def charger_arrets():
    connexion = psycopg2.connect(
        host="localhost", dbname="sotral_db",
        user="sotral_user", password="merci_p@p@10")
    curseur = connexion.cursor()
    curseur.execute("SELECT DISTINCT nom FROM arrets;")
    arrets = [ligne[0] for ligne in curseur.fetchall()]
    curseur.close(); connexion.close()
    return arrets

# ---------- 2. Normalisation du texte (SF2) ----------
def normaliser(texte):
    """minuscules + suppression des accents : 'Adidogomé' -> 'adidogome'"""
    texte = unicodedata.normalize("NFD", texte.lower())
    texte = texte.encode("ascii", "ignore").decode()
    return " ".join(texte.split())

# ---------- 3. Retrouver un arrêt malgré les fautes (SF2) ----------
def trouver_arret(fragment, arrets, seuil=70):
    """Compare le fragment aux noms d'arrêts, renvoie le meilleur candidat."""
    if not fragment:
        return None, 0
    candidats = {a: normaliser(a).replace("arret ", "") for a in arrets}
    resultat = process.extractOne(
        normaliser(fragment), candidats, scorer=fuzz.WRatio)
    if resultat and resultat[1] >= seuil:
        return resultat[2], round(resultat[1])
    return None, 0

# ---------- 4. Analyse de la phrase (SF1) ----------
MARQUEURS_DEPART = r"(je suis a|je pars de|je pars du|depuis|en partant de|de)"
MARQUEURS_DESTINATION = r"(je veux aller a|je souhaite me rendre a|aller a|me rendre a|jusqu'a|jusqu a|vers|pour|a destination de)"

def analyser(phrase, arrets):
    p = normaliser(phrase)
    depart_txt, destination_txt = None, None

    m = list(re.finditer(MARQUEURS_DESTINATION, p))
    if m:
        destination_txt = p[m[-1].end():].strip(" .!?")
        p = p[:m[-1].start()]

    m = list(re.finditer(MARQUEURS_DEPART, p))
    if m:
        depart_txt = p[m[-1].end():].strip(" .!?,")

    depart, score_d = trouver_arret(depart_txt, arrets)
    destination, score_a = trouver_arret(destination_txt, arrets)
    return {"depart": depart, "score_depart": score_d,
            "destination": destination, "score_destination": score_a}

# ---------- 5. Tests ----------
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
