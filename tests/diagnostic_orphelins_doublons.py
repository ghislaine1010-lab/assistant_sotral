# -*- coding: utf-8 -*-
"""Les arrêts orphelins sont-ils en réalité des DOUBLONS de noms
   (un jumeau déjà attaché à une ligne existe sous le même nom) ?"""

from app.config import connexion

conn = connexion(); cur = conn.cursor()

cur.execute("""
    SELECT a.nom FROM arrets a
    LEFT JOIN arrets_lignes al ON al.arret_id = a.id
    WHERE al.id IS NULL;
""")
orphelins = [r[0] for r in cur.fetchall()]

avec_jumeau_attache = 0
vrais_isoles = []
for nom in orphelins:
    cur.execute("""
        SELECT COUNT(*) FROM arrets a
        JOIN arrets_lignes al ON al.arret_id = a.id
        WHERE a.nom = %s;
    """, (nom,))
    n = cur.fetchone()[0]
    if n > 0:
        avec_jumeau_attache += 1
    else:
        vrais_isoles.append(nom)

print(f"Total orphelins : {len(orphelins)}")
print(f"  Ayant un jumeau du MÊME NOM déjà attaché à une ligne : {avec_jumeau_attache}")
print(f"  Vraiment isolés (aucun jumeau attaché, nom unique orphelin) : {len(vrais_isoles)}")
print("\nExemples de vrais isolés :")
for nom in vrais_isoles[:15]:
    print(f"  - {nom}")

cur.close(); conn.close()
