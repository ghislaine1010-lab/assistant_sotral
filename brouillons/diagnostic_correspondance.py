# -*- coding: utf-8 -*-
"""Diagnostic : quelles lignes desservent Adjololo et AD Zanguéra,
   et ont-elles un arrêt en commun (peu importe l'ordre) ?"""

import psycopg2

conn = psycopg2.connect(host="localhost", dbname="sotral_db",
                         user="sotral_user", password="merci_p@p@10")
cur = conn.cursor()

for lieu in ["Adjololo", "AD Zanguéra"]:
    cur.execute("""
        SELECT DISTINCT l.ref, l.nom
        FROM arrets_lignes al
        JOIN arrets a ON a.id = al.arret_id
        JOIN lignes l ON l.id = al.ligne_id
        WHERE a.nom = %s;
    """, (lieu,))
    print(f"\nLignes desservant « {lieu} » :")
    for ref, nom in cur.fetchall():
        print(f"  {ref} : {nom}")

# Les lignes de Adjololo ont-elles un arrêt en commun (même nom) avec les lignes de AD Zanguéra ?
cur.execute("""
    SELECT DISTINCT l1.ref, l1.nom, a_commun.nom, l2.ref, l2.nom
    FROM arrets_lignes al_dep
    JOIN arrets a_dep ON a_dep.id = al_dep.arret_id AND a_dep.nom = 'Adjololo'
    JOIN lignes l1 ON l1.id = al_dep.ligne_id
    JOIN arrets_lignes al_c1 ON al_c1.ligne_id = al_dep.ligne_id
    JOIN arrets a_commun ON a_commun.id = al_c1.arret_id
    JOIN arrets a_c2 ON a_c2.nom = a_commun.nom
    JOIN arrets_lignes al_c2 ON al_c2.arret_id = a_c2.id AND al_c2.ligne_id <> al_dep.ligne_id
    JOIN lignes l2 ON l2.id = al_c2.ligne_id
    JOIN arrets_lignes al_arr ON al_arr.ligne_id = al_c2.ligne_id
    JOIN arrets a_arr ON a_arr.id = al_arr.arret_id AND a_arr.nom = 'AD Zanguéra'
    LIMIT 5;
""")
print("\nCorrespondances possibles (sans contrainte d'ordre) :")
resultats = cur.fetchall()
if resultats:
    for r in resultats:
        print(" ", r)
else:
    print("  Aucune — ces deux zones ne se rejoignent pas en un seul changement.")

cur.close(); conn.close()
