# -*- coding: utf-8 -*-
"""Résoudre précisément les deux causes restantes."""

from app.nlp import charger_arrets, trouver_arret, normaliser

arrets = charger_arrets()

print("===== Cas 1 : le vrai nom de l'arrêt Djagblé =====")
candidats = [a for a in arrets if "djag" in normaliser(a)]
print("Arrêts contenant 'djag' dans la base :", candidats or "AUCUN")

print("\n===== Cas 2 : 'Zangéra' (sans le u) est-il bien reconnu ? =====")
print("trouver_arret('Zangéra') :", trouver_arret("Zangéra", arrets))
print("trouver_arret('Adidogome') :", trouver_arret("Adidogome", arrets))
