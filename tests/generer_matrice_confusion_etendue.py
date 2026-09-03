# -*- coding: utf-8 -*-
"""Version élargie de la matrice de confusion (02/09) : 30 phrases (10
   par classe, au lieu de 5), toujours répétées 3 fois -- soit 90
   prédictions au lieu de 45, pour un résultat statistiquement plus
   robuste, suite à la recommandation du directeur de mémoire."""
import csv
from app.llm import interpreter_message

jeu_de_test = [
    # --- Salutations (10) ---
    ("Bonjour", "salutation"),
    ("Salut, comment vas-tu ?", "salutation"),
    ("Merci beaucoup, au revoir", "salutation"),
    ("Bonsoir", "salutation"),
    ("Coucou !", "salutation"),
    ("Bonjour, comment ça va ?", "salutation"),
    ("Merci pour ton aide", "salutation"),
    ("Salut !", "salutation"),
    ("Au revoir et merci", "salutation"),
    ("Bonne journée à toi", "salutation"),

    # --- Demandes d'itinéraire (10) ---
    ("Je suis à Bè et je veux aller à BIA", "itineraire"),
    ("Comment aller à Adidogomé depuis Zanguéra ?", "itineraire"),
    ("Je pars de Todman pour Atikoumé", "itineraire"),
    ("Quel bus prendre pour aller au campus ?", "itineraire"),
    ("Je veux me rendre à la douane", "itineraire"),
    ("Depuis Kodjoviakopé, comment aller à Tokoin ?", "itineraire"),
    ("Itinéraire de Hédzranawoé à Amoutivé", "itineraire"),
    ("Je suis à Agoè, je veux aller à Adakpamé", "itineraire"),
    ("Comment rejoindre le Grand Marché depuis Bè ?", "itineraire"),
    ("Trajet pour aller à Nyékonakpoè", "itineraire"),

    # --- Autres questions (10) ---
    ("Quel est le prix du ticket ?", "autre"),
    ("Est-ce que les bus roulent le dimanche ?", "autre"),
    ("Qui a créé cet assistant ?", "autre"),
    ("Quelle est la capitale du Togo ?", "autre"),
    ("Peux-tu m'aider avec autre chose ?", "autre"),
    ("Quelle heure est-il ?", "autre"),
    ("Combien coûte un trajet en général ?", "autre"),
    ("Es-tu une intelligence artificielle ?", "autre"),
    ("Quel temps fait-il aujourd'hui ?", "autre"),
    ("Peux-tu parler anglais ?", "autre"),
]

resultats = []
for phrase, attendu in jeu_de_test:
    for essai in range(3):
        r = interpreter_message(phrase)
        predit = r.get("intention", "erreur")
        resultats.append({"phrase": phrase, "attendu": attendu, "predit": predit, "essai": essai + 1})
        print(f"[{attendu:12s}] {phrase[:40]:40s} -> prédit: {predit}")

with open("resultats_classification_intention_etendue.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["phrase", "attendu", "predit", "essai"])
    w.writeheader()
    w.writerows(resultats)

print(f"\n{len(resultats)} prédictions enregistrées dans resultats_classification_intention_etendue.csv")
