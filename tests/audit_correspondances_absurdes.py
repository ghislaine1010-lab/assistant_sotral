# -*- coding: utf-8 -*-
"""La table correspondances contient-elle des paires absurdes
   (une ligne indiquée comme correspondant avec elle-même) ?"""

from app.config import connexion

conn = connexion(); cur = conn.cursor()
cur.execute("SELECT COUNT(*) FROM correspondances WHERE ligne_a = ligne_b;")
n_absurdes = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM correspondances;")
total = cur.fetchone()[0]

print(f"Correspondances totales : {total}")
print(f"Correspondances absurdes (ligne_a = ligne_b) : {n_absurdes}")

if n_absurdes > 0:
    cur.execute("SELECT DISTINCT arret_nom, ligne_a FROM correspondances WHERE ligne_a = ligne_b LIMIT 10;")
    for arret, ligne in cur.fetchall():
        print(f"  - {arret} : {ligne} <-> {ligne}")

cur.close(); conn.close()
