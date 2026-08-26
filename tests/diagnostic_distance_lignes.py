# -*- coding: utf-8 -*-
"""Existe-t-il des paires de lignes qui nécessitent AU MOINS DEUX
   correspondances pour être reliées (donc hors de portée du moteur
   actuel, qui ne gère qu'une seule correspondance) ?"""

from app.config import connexion
from collections import defaultdict, deque

conn = connexion(); cur = conn.cursor()
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

lignes = sorted(graphe.keys())
paires_a_2_sauts_ou_plus = []

for depart in lignes:
    distances = {depart: 0}
    file_attente = deque([depart])
    while file_attente:
        courante = file_attente.popleft()
        for voisine in graphe[courante]:
            if voisine not in distances:
                distances[voisine] = distances[courante] + 1
                file_attente.append(voisine)
    for cible, dist in distances.items():
        if dist >= 2 and depart < cible:
            paires_a_2_sauts_ou_plus.append((depart, cible, dist))

print(f"Paires de lignes nécessitant AU MOINS 2 correspondances : {len(paires_a_2_sauts_ou_plus)}")
for a, b, d in sorted(paires_a_2_sauts_ou_plus, key=lambda x: -x[2])[:10]:
    print(f"  {a} <-> {b} : distance minimale = {d} correspondance(s)")
