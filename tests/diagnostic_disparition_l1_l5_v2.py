# -*- coding: utf-8 -*-
"""Le bon nom cette fois : 'Legbanou', pas 'Amina' (erreur de copier-
   coller dans le diagnostic précédent)."""

from app.config import connexion

conn = connexion(); cur = conn.cursor()

cur.execute("""
    SELECT l.ref, a.nom FROM arrets_lignes al
    JOIN arrets a ON a.id = al.arret_id
    JOIN lignes l ON l.id = al.ligne_id
    WHERE a.nom ILIKE '%legbanou%'
    ORDER BY l.ref;
""")
print("Rattachements actuels de tout arrêt contenant 'Legbanou' :", cur.fetchall())

# Existe-t-il encore un arrêt de ce nom exact dans la base, ligne par ligne ?
cur.execute("SELECT DISTINCT nom FROM arrets WHERE nom ILIKE '%legbanou%';")
print("\nNoms exacts en base contenant 'Legbanou' :", cur.fetchall())

cur.close(); conn.close()
