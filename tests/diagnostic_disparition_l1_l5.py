# -*- coding: utf-8 -*-
"""Pourquoi la correspondance L1-L5 (valide dans la table stockée)
   n'est-elle plus détectée aujourd'hui ? Quel arrêt la reliait ?"""

from app.config import connexion

conn = connexion(); cur = conn.cursor()

cur.execute("SELECT arret_nom, ligne_a, ligne_b FROM correspondances WHERE (ligne_a='L1' AND ligne_b='L5') OR (ligne_a='L5' AND ligne_b='L1');")
print("Dans la table stockée :", cur.fetchall())

cur.execute("""
    SELECT l.ref, a.nom FROM arrets_lignes al
    JOIN arrets a ON a.id = al.arret_id
    JOIN lignes l ON l.id = al.ligne_id
    WHERE l.ref IN ('L1','L5') AND a.nom ILIKE '%amina%';
""")
print("\nRattachements actuels des arrêts nommés 'Amina' sur L1/L5 :", cur.fetchall())

cur.close(); conn.close()
