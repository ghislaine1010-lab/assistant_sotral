# -*- coding: utf-8 -*-
"""Vérifie le score réel de similarité pour le contexte utilisé,
   afin de savoir si le seuil de 45 est bien calibré."""

from sentence_transformers import SentenceTransformer
from app.config import connexion

modele = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

contexte = "aller a l'universite"
vecteur = modele.encode(contexte).tolist()

conn = connexion()
cur = conn.cursor()
cur.execute("""
    SELECT DISTINCT ON (nom) nom, embedding <=> %s::vector AS distance
    FROM arrets WHERE embedding IS NOT NULL
    ORDER BY nom, distance ASC LIMIT 10;
""", (vecteur,))
resultats = sorted(cur.fetchall(), key=lambda r: r[1])
cur.close(); conn.close()

print(f"Contexte testé : « {contexte} »\n")
for nom, distance in resultats:
    similarite = (1 - distance) * 100
    print(f"  {nom:35s} -> similarité {similarite:.1f}")
