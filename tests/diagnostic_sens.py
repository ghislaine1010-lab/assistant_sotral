# -*- coding: utf-8 -*-
"""Vérifie si les 'sens_direction' de la table horaires correspondent
   bien aux vrais noms de lignes (table lignes / arrets_lignes)."""

from app.config import connexion

conn = connexion(); cur = conn.cursor()

# Les sens disponibles pour L16 dans les HORAIRES (texte transcrit à la main)
cur.execute("SELECT DISTINCT sens_direction FROM horaires WHERE ligne_ref = 'L16';")
print("Sens dans HORAIRES pour L16 :", [r[0] for r in cur.fetchall()])

# Les sens disponibles pour L16 dans les LIGNES (issues du GeoJSON/OSM)
cur.execute("SELECT DISTINCT nom FROM lignes WHERE ref = 'L16';")
print("Sens dans LIGNES (OSM) pour L16 :", [r[0] for r in cur.fetchall()])

cur.close(); conn.close()
