# -*- coding: utf-8 -*-
"""Le réseau, vu comme un graphe où chaque ligne est un nœud et chaque
   correspondance une arête, forme-t-il un seul bloc connecté, ou
   existe-t-il des îlots de lignes injoignables entre eux, même avec
   plusieurs changements de bus successifs ?"""

from app.config import connexion
from collections import defaultdict, deque

conn = connexion(); cur = conn.cursor()

cur.execute("SELECT DISTINCT ref FROM lignes ORDER BY ref;")
toutes_les_lignes = [r[0] for r in cur.fetchall()]

# Construit le graphe : correspondances calculées EN DIRECT (comme
# app/faits.py depuis la correction du 31/07), pas via une table figée.
cur.execute("""
    SELECT DISTINCT l1.ref, l2.ref
    FROM arrets_lignes al1
    JOIN arrets a1 ON a1.id = al1.arret_id
    JOIN lignes l1 ON l1.id = al1.ligne_id
    JOIN arrets a2 ON a2.nom = a1.nom
    JOIN arrets_lignes al2 ON al2.arret_id = a2.id
    JOIN lignes l2 ON l2.id = al2.ligne_id
    WHERE l1.ref <> l2.ref;
""")
graphe = defaultdict(set)
for ref1, ref2 in cur.fetchall():
    graphe[ref1].add(ref2)
    graphe[ref2].add(ref1)
cur.close(); conn.close()

# Parcours en largeur (BFS) depuis une ligne de référence (L1)
depart = "L1"
visitees = {depart}
file_attente = deque([depart])
while file_attente:
    courante = file_attente.popleft()
    for voisine in graphe[courante]:
        if voisine not in visitees:
            visitees.add(voisine)
            file_attente.append(voisine)

injoignables = sorted(set(toutes_les_lignes) - visitees)
sans_aucune_correspondance = sorted(set(toutes_les_lignes) - set(graphe.keys()))

print(f"{len(toutes_les_lignes)} lignes au total dans le réseau.")
print(f"Lignes atteignables depuis {depart}, avec autant de correspondances que nécessaire : {len(visitees)}")
print(f"\nLignes INJOIGNABLES depuis {depart} (îlot séparé) : {injoignables or 'aucune'}")
print(f"Lignes sans AUCUNE correspondance recensée avec une autre ligne : {sans_aucune_correspondance or 'aucune'}")
