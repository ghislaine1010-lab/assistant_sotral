# -*- coding: utf-8 -*-
"""Comparaison LLM vs analyseur par règles sur la phrase qui a échoué,
   pour savoir si nos propres règles s'en sortent mieux."""

from app.llm import interpreter_message
from app.nlp import charger_arrets, analyser

arrets = charger_arrets()
phrase = "je suis a be je veux me rendre a bia"

print("--- Ce que le LLM extrait (plusieurs essais) ---")
for i in range(3):
    r = interpreter_message(phrase)
    print(f"  Essai {i+1} : intention={r.get('intention')!r}, depart={r.get('depart')!r}, destination={r.get('destination')!r}")

print("\n--- Ce que notre analyseur par règles (app.nlp.analyser) extrait ---")
r2 = analyser(phrase, arrets)
print(" ", r2)
