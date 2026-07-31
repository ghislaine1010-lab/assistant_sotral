# -*- coding: utf-8 -*-
"""Vérifie que le tri par distance, effectué APRÈS le dédoublonnage,
   retrouve enfin Campus."""

from sentence_transformers import SentenceTransformer
from app.config import connexion

modele = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
vecteur = modele.encode("aller a l'universite").tolist()

conn = connexion()
cur = conn.cursor()
cur.execute("""
    SELECT nom, distance FROM (
        SELECT DISTINCT ON (nom) nom, embedding <=> %s::vector AS distance
        FROM arrets WHERE embedding IS NOT NULL
        ORDER BY nom, distance ASC
    ) sous_requete
    ORDER BY distance ASC
    LIMIT 10;
""", (vecteur,))
resultats = cur.fetchall()
cur.close(); conn.close()

for nom, distance in resultats:
    print(f"  {nom:35s} -> similarité {(1-distance)*100:.1f}")
