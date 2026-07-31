# -*- coding: utf-8 -*-
"""Audit du pipeline complet sur des cas variés, pour repérer
   les erreurs et les incohérences avant de passer à l'API web."""

from app.assistant import repondre
from app.nlp import charger_arrets

arrets = charger_arrets()

cas_test = [
    ("Salutation simple", "Salut !"),
    ("Salutation + remerciement", "Merci, à bientôt"),
    ("Itinéraire clair", "Je suis à Bè et je veux aller à Adidogomé"),
    ("Itinéraire avec faute", "je veux aller a zangera en partant de todman"),
    ("Lieu isolé (test du contexte sémantique)", "je veux aller à la fac en partant de Bè"),
    ("Ambiguïté attendue", "je pars de Bè pour le CHU"),
    ("Hors périmètre", "quel est le tarif pour les étudiants ?"),
    ("Horaire précis", "je veux aller de BIA à Zanguéra vers 8h"),
    ("Ligne d'un arrêt", "quelle ligne dessert Zanguéra ?"),
    ("Phrase absurde", "raconte-moi une blague"),
]

for titre, phrase in cas_test:
    print(f"\n[{titre}]")
    print(f"Usager : {phrase}")
    try:
        print("Assistant :", repondre(phrase, arrets))
    except Exception as e:
        print(f"❌ ERREUR : {type(e).__name__} : {e}")
