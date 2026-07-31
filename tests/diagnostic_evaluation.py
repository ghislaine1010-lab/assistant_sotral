# -*- coding: utf-8 -*-
"""Comprendre précisément les deux échecs du jeu de test."""

from app.nlp import charger_arrets, analyser, trouver_arret
from app.llm import interpreter_message

arrets = charger_arrets()

print("===== Cas 1 : Adjololo / Djagble (échec compréhension ET itinéraire) =====")
phrase1 = "je veux aller à Adjololo en partant de Djagble"
r1 = analyser(phrase1, arrets)
print("Résultat analyser() :", r1)
print("Test direct trouver_arret('Djagble') :", trouver_arret("Djagble", arrets))
print("Test direct trouver_arret('Djagblé') :", trouver_arret("Djagblé", arrets))

print("\n===== Cas 2 : Adidogomé / Zanguéra (échec itinéraire, variabilité LLM ?) =====")
phrase2 = "je suis a adidogome je veux aller a zangera"
comprehension = interpreter_message(phrase2)
print("Ce que le LLM a extrait cette fois :", comprehension)
