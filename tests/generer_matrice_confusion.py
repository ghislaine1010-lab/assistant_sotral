# -*- coding: utf-8 -*-
"""Construit une VRAIE matrice de confusion à partir du classifieur
   d'intention du LLM (3 classes : salutation, itineraire, autre),
   en répétant chaque phrase 3 fois pour tenir compte de la
   variabilité déjà documentée du modèle."""

import csv
from app.llm import interpreter_message

# (phrase, intention_reelle_attendue) -- 15 phrases, 5 par classe
jeu_de_test = [
    ("Bonjour", "salutation"),
    ("Salut, comment vas-tu ?", "salutation"),
    ("Merci beaucoup, au revoir", "salutation"),
    ("Bonsoir", "salutation"),
    ("Coucou !", "salutation"),
    ("Je suis à Bè et je veux aller à BIA", "itineraire"),
    ("Comment aller à Adidogomé depuis Zanguéra ?", "itineraire"),
    ("Je pars de Todman pour Atikoumé", "itineraire"),
    ("Quel bus prendre pour aller au campus ?", "itineraire"),
    ("Je veux me rendre à la douane", "itineraire"),
    ("Quel est le prix du ticket ?", "autre"),
    ("Est-ce que les bus roulent le dimanche ?", "autre"),
    ("Qui a créé cet assistant ?", "autre"),
    ("Quelle est la capitale du Togo ?", "autre"),
    ("Peux-tu m'aider avec autre chose ?", "autre"),
]

resultats = []
for phrase, attendu in jeu_de_test:
    for essai in range(3):
        r = interpreter_message(phrase)
        predit = r.get("intention", "erreur")
        resultats.append({"phrase": phrase, "attendu": attendu, "predit": predit, "essai": essai + 1})
        print(f"[{attendu:12s}] {phrase[:40]:40s} -> prédit: {predit}")

with open("resultats_classification_intention.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["phrase", "attendu", "predit", "essai"])
    w.writeheader()
    w.writerows(resultats)

print(f"\n{len(resultats)} prédictions enregistrées dans resultats_classification_intention.csv")
