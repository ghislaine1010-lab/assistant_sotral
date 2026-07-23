# -*- coding: utf-8 -*-
"""Calcule l'embedding de chaque arrêt et l'enregistre dans PostgreSQL
   (colonne 'embedding' de la table 'arrets'). À lancer une seule fois."""

from sentence_transformers import SentenceTransformer
from app.config import connexion

print("Chargement du modèle...")
modele = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

conn = connexion()
cur = conn.cursor()
cur.execute("SELECT id, nom FROM arrets;")
lignes = cur.fetchall()
print(f"{len(lignes)} arrêts à encoder...")

noms = [nom for _, nom in lignes]
vecteurs = modele.encode(noms, show_progress_bar=True)

for (id_arret, _), vecteur in zip(lignes, vecteurs):
    cur.execute(
        "UPDATE arrets SET embedding = %s WHERE id = %s;",
        (vecteur.tolist(), id_arret)
    )

conn.commit()
cur.close(); conn.close()
print("Terminé : embeddings enregistrés dans la base.")
