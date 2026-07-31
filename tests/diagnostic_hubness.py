# -*- coding: utf-8 -*-
"""Vérifie si l'écart entre le 1er et le 2e résultat permet de
   distinguer un vrai match d'un « point hub » qui attire tout."""

from sentence_transformers import SentenceTransformer
from app.config import connexion

modele = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

def top5(texte):
    vecteur = modele.encode(texte).tolist()
    conn = connexion(); cur = conn.cursor()
    cur.execute("""
        SELECT nom, distance FROM (
            SELECT DISTINCT ON (nom) nom, embedding <=> %s::vector AS distance
            FROM arrets WHERE embedding IS NOT NULL
            ORDER BY nom, distance ASC
        ) sous_requete ORDER BY distance ASC LIMIT 5;
    """, (vecteur,))
    r = cur.fetchall(); cur.close(); conn.close()
    return [(nom, round((1-d)*100,1)) for nom, d in r]

for texte in ["aller a l'universite", "Djagble", "xyzabc123", "aller au marche central"]:
    resultats = top5(texte)
    ecart = resultats[0][1] - resultats[1][1] if len(resultats) > 1 else 0
    print(f"\n« {texte} » -> {resultats}")
    print(f"  Écart 1er/2e : {ecart:.1f} points")
