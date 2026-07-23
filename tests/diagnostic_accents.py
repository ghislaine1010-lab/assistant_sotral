# -*- coding: utf-8 -*-
"""Le manque d'accents dégrade-t-il vraiment la recherche sémantique ?"""

from sentence_transformers import SentenceTransformer
from app.config import connexion

modele = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

def tester(contexte):
    vecteur = modele.encode(contexte).tolist()
    conn = connexion()
    cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT ON (nom) nom, embedding <=> %s::vector AS distance
        FROM arrets WHERE embedding IS NOT NULL
        ORDER BY nom, distance ASC LIMIT 3;
    """, (vecteur,))
    resultats = sorted(cur.fetchall(), key=lambda r: r[1])
    cur.close(); conn.close()
    print(f"\nContexte : « {contexte} »")
    for nom, distance in resultats:
        print(f"  {nom:35s} -> similarité {(1-distance)*100:.1f}")

tester("aller a l'universite")       # sans accents (ce que le code envoie actuellement)
tester("aller à l'université")        # avec accents (texte original)
