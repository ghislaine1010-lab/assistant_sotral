# -*- coding: utf-8 -*-
"""Le vrai arrêt existe-t-il encore, et quel score de comparaison
   obtient-on exactement avec lui ?"""

from app.nlp import charger_arrets, normaliser
from rapidfuzz import fuzz

arrets = charger_arrets()

candidats = [a for a in arrets if "avedj" in normaliser(a)]
print("Arrêts contenant 'avedj' dans la base :", candidats)

for c in candidats:
    candidat_norm = normaliser(c).replace("arret ", "")
    score = fuzz.WRatio(normaliser("avedji"), candidat_norm)
    print(f"  Score WRatio entre 'avedji' et '{candidat_norm}' : {score}")
