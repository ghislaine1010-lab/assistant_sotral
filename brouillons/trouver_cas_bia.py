# -*- coding: utf-8 -*-
"""Cherche deux arrêts sur deux LIGNES DIFFÉRENTES (par référence, pas
   par sens) qui passent toutes deux par BIA, pour tester la correspondance."""

import psycopg2
from moteur_recommandation import recommander

conn = psycopg2.connect(host="localhost", dbname="sotral_db",
                         user="sotral_user", password="merci_p@p@10")
cur = conn.cursor()

# Références de lignes distinctes passant par BIA (L1, L3, L6...)
cur.execute("""
    SELECT DISTINCT l.ref FROM arrets_lignes al
    JOIN arrets a ON a.id = al.arret_id AND a.nom = 'BIA'
    JOIN lignes l ON l.id = al.ligne_id
    ORDER BY l.ref LIMIT 2;
""")
refs = [r[0] for r in cur.fetchall()]
print("Deux références de lignes distinctes retenues :", refs)
ref1, ref2 = refs[0], refs[1]

def id_ligne(ref):
    cur.execute("SELECT id FROM lignes WHERE ref = %s LIMIT 1;", (ref,))
    return cur.fetchone()[0]

def arret_lointain(ref_ligne, ref_autre):
    cur.execute("""
        SELECT a.nom FROM arrets_lignes al
        JOIN arrets a ON a.id = al.arret_id
        JOIN lignes l ON l.id = al.ligne_id
        WHERE l.ref = %s AND a.nom <> 'BIA'
          AND a.nom NOT IN (
              SELECT a2.nom FROM arrets_lignes al2
              JOIN arrets a2 ON a2.id = al2.arret_id
              JOIN lignes l2 ON l2.id = al2.ligne_id
              WHERE l2.ref = %s)
        ORDER BY al.ordre DESC LIMIT 1;
    """, (ref_ligne, ref_autre))
    row = cur.fetchone()
    return row[0] if row else None

depart = arret_lointain(ref1, ref2)
destination = arret_lointain(ref2, ref1)

print(f"\nTest : « {depart} » (ligne {ref1}) -> « {destination} » (ligne {ref2})")
print(recommander(depart, destination))

cur.close(); conn.close()
