# -*- coding: utf-8 -*-
"""Recherche sémantique directement en SQL grâce à pgvector."""

from sentence_transformers import SentenceTransformer
from app.config import connexion

modele = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

def chercher_par_sens(texte, top_n=5):
    vecteur = modele.encode(texte).tolist()
    conn = connexion()
    cur = conn.cursor()
    cur.execute("""
        SELECT nom, embedding <=> %s::vector AS distance
        FROM arrets
        WHERE embedding IS NOT NULL
        ORDER BY distance ASC
        LIMIT %s;
    """, (vecteur, top_n))
    resultats = cur.fetchall()
    cur.close(); conn.close()
    return resultats

if __name__ == "__main__":
    requete = "je veux aller à l'université"
    print(f"Requête : « {requete} »\n")
    for nom, distance in chercher_par_sens(requete):
        similarite = (1 - distance) * 100
        print(f"  {nom:30s} -> similarité {similarite:.0f}")
