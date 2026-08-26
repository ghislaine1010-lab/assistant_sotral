# -*- coding: utf-8 -*-
"""Graphique RÉEL (pas une illustration) : projette en 2D les embeddings
   déjà calculés pour tes arrêts, pour visualiser comment le modèle
   pré-entraîné organise le SENS de tes propres données."""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sklearn.decomposition import PCA
from pgvector.psycopg2 import register_vector
from app.config import connexion

conn = connexion()
register_vector(conn)
cur = conn.cursor()

groupes = {
    "Campus / université": ["Terminus Campus Sud", "Arrêt Campus Nord", "Arrêt CHU Campus"],
    "Marchés": ["Marché Bè", "Marché Hédzranawoé", "Arrêt Marché Totsi"],
    "Adakpamé": ["EPP Adakpamé", "Total Adakpamé", "Eglise des AD Adakpamé"],
    "Zanguéra": ["AD Zanguéra", "Togocel Zanguéra"],
}

points, labels, couleurs_groupe = [], [], []
palette = ["#1F4E79", "#2E74B5", "#ED7D31", "#2F7D5E"]

for i, (groupe, noms) in enumerate(groupes.items()):
    for nom in noms:
        cur.execute("SELECT embedding FROM arrets WHERE nom = %s AND embedding IS NOT NULL LIMIT 1;", (nom,))
        row = cur.fetchone()
        if row:
            # row[0] est un objet pgvector.Vector -> .to_numpy() le convertit
            # proprement en tableau numpy exploitable par scikit-learn
            vecteur = row[0].to_numpy()
            points.append(vecteur)
            labels.append(nom)
            couleurs_groupe.append(palette[i])

cur.close(); conn.close()

points = np.array(points)
reduits = PCA(n_components=2).fit_transform(points)

fig, ax = plt.subplots(figsize=(9, 7))
ax.scatter(reduits[:, 0], reduits[:, 1], c=couleurs_groupe, s=140, edgecolor="black", zorder=3)
for (x, y), label in zip(reduits, labels):
    ax.annotate(label, (x, y), textcoords="offset points", xytext=(6, 6), fontsize=8.5)

for i, groupe in enumerate(groupes.keys()):
    ax.scatter([], [], c=palette[i], s=100, label=groupe)
ax.legend(title="Groupe attendu", loc="best", fontsize=9)
ax.set_title("Projection réelle des embeddings de mes arrêts SOTRAL\n(modèle paraphrase-multilingual-MiniLM-L12-v2)", fontsize=11)
ax.set_xlabel("Composante 1 (PCA)"); ax.set_ylabel("Composante 2 (PCA)")

plt.tight_layout()
plt.savefig("carte_du_sens_reelle.png", dpi=150)
print("Graphique enregistré : carte_du_sens_reelle.png")
