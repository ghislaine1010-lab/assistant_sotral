# -*- coding: utf-8 -*-
"""Comparaison RapidFuzz (comparaison de lettres) vs embeddings
   (comparaison de sens), sur un cas que RapidFuzz ne peut pas résoudre."""

from sentence_transformers import SentenceTransformer, util
from rapidfuzz import fuzz

print("Chargement du modèle pré-entraîné (un peu long la première fois)...")
modele = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

requete = "je veux aller à l'université"
candidats = ["Campus", "Marché Gayobor", "Hôpital", "BIA", "Zanguéra"]

print(f"\nRequête : « {requete} »\n")

print("-- Méthode 1 : RapidFuzz (comparaison de lettres) --")
for c in candidats:
    score = fuzz.WRatio(requete.lower(), c.lower())
    print(f"  {c:20s} -> score {score:.0f}")

print("\n-- Méthode 2 : Embeddings (comparaison de sens) --")
vecteur_requete = modele.encode(requete, convert_to_tensor=True)
vecteurs_candidats = modele.encode(candidats, convert_to_tensor=True)
similarites = util.cos_sim(vecteur_requete, vecteurs_candidats)[0]
for c, s in zip(candidats, similarites):
    print(f"  {c:20s} -> similarité {float(s)*100:.0f}")
