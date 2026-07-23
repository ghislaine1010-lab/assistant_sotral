# -*- coding: utf-8 -*-
"""Test manuel : vérifie que le NLP et le moteur de recommandation
   fonctionnent toujours après la réorganisation du projet."""

from app.nlp import charger_arrets, analyser
from app.recommandation import recommander

print("== Test du module NLP ==")
arrets = charger_arrets()
print(f"{len(arrets)} arrêts chargés.")
resultat = analyser("je pars de zangera pour le CHU", arrets)
print("Résultat :", resultat)

print("\n== Test du moteur de recommandation ==")
print(recommander("BIA", "Togocel Zanguéra"))
