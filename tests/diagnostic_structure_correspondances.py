# -*- coding: utf-8 -*-
"""Est-ce qu'on compare vraiment la même chose ? Combien de PAIRES DE
   LIGNES UNIQUES contient la table correspondances (au lieu du nombre
   total de lignes d'enregistrement) ?"""

from app.config import connexion

conn = connexion(); cur = conn.cursor()

cur.execute("SELECT COUNT(*) FROM correspondances;")
total_lignes_table = cur.fetchone()[0]

cur.execute("""
    SELECT COUNT(DISTINCT LEAST(ligne_a, ligne_b) || '-' || GREATEST(ligne_a, ligne_b))
    FROM correspondances;
""")
paires_uniques_table = cur.fetchone()[0]

cur.execute("SELECT arret_nom, ligne_a, ligne_b FROM correspondances LIMIT 5;")
exemples = cur.fetchall()

print(f"Nombre total de lignes dans la table correspondances : {total_lignes_table}")
print(f"Nombre de PAIRES DE LIGNES UNIQUES dans cette même table : {paires_uniques_table}")
print(f"\nExemples de lignes de la table :")
for r in exemples:
    print(" ", r)

cur.close(); conn.close()
