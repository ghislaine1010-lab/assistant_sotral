# -*- coding: utf-8 -*-
"""Quelles sont exactement les 8 paires qui diffèrent entre la table
   stockée et l'état réel actuel ? Ont-elles disparu (obsolètes) ou
   sont-elles nouvelles (apparues grâce à nos corrections récentes) ?"""

from app.config import connexion

conn = connexion(); cur = conn.cursor()

cur.execute("""
    SELECT DISTINCT LEAST(ligne_a, ligne_b) || '-' || GREATEST(ligne_a, ligne_b)
    FROM correspondances;
""")
stockees = {r[0] for r in cur.fetchall()}

cur.execute("""
    SELECT DISTINCT LEAST(l1.ref, l2.ref) || '-' || GREATEST(l1.ref, l2.ref)
    FROM arrets_lignes al1
    JOIN arrets a1 ON a1.id = al1.arret_id
    JOIN lignes l1 ON l1.id = al1.ligne_id
    JOIN arrets a2 ON a2.nom = a1.nom
    JOIN arrets_lignes al2 ON al2.arret_id = a2.id
    JOIN lignes l2 ON l2.id = al2.ligne_id
    WHERE l1.ref <> l2.ref;
""")
reelles = {r[0] for r in cur.fetchall()}

print(f"Dans la table mais plus valides aujourd'hui : {sorted(stockees - reelles)}")
print(f"Valides aujourd'hui mais absentes de la table : {sorted(reelles - stockees)}")

cur.close(); conn.close()
