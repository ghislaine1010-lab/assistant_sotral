# -*- coding: utf-8 -*-
"""Vérifie les infos réelles de L18 et le nombre total d'arrêts par sens."""

from app.config import connexion

conn = connexion(); cur = conn.cursor()

cur.execute("SELECT osm_id, nom, terminus_depart, terminus_arrivee, couleur FROM lignes WHERE ref = 'L18';")
print("Ligne L18 (informations en base) :")
for row in cur.fetchall():
    print(" ", row)

cur.execute("""
    SELECT l.nom, COUNT(*) FROM arrets_lignes al
    JOIN lignes l ON l.id = al.ligne_id AND l.ref = 'L18'
    GROUP BY l.nom;
""")
print("\nNombre total d'arrêts par sens :")
for row in cur.fetchall():
    print(" ", row)

cur.close(); conn.close()
