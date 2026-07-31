# -*- coding: utf-8 -*-
"""Que renvoie exactement le LLM sur la phrase de l'usager, et que
   devient ce texte une fois passé dans trouver_arret ?"""

from app.llm import interpreter_message
from app.nlp import charger_arrets, trouver_arret, nettoyer_fragment, normaliser

phrase = "je suis a avedji et je veux aller a adidogome est ce que c'est possible?"
arrets = charger_arrets()

comprehension = interpreter_message(phrase)
print("Ce que le LLM a extrait :", comprehension)

depart_brut = comprehension.get("depart")
print(f"\nFragment brut du départ : « {depart_brut} »")
print(f"Après nettoyage : « {nettoyer_fragment(depart_brut or '')} »")
print(f"Après normalisation : « {normaliser(nettoyer_fragment(depart_brut or ''))} »")

resultat = trouver_arret(depart_brut, arrets)
print(f"\nRésultat de trouver_arret() : {resultat}")

# Test direct, pour comparer
print("\nTest direct avec juste 'avedji' :", trouver_arret("avedji", arrets))
