# -*- coding: utf-8 -*-
"""Audit systématique : pour chaque ligne du réseau, l'ordre des arrêts
   communs entre le sens aller et le sens retour est-il bien INVERSÉ
   (normal) ou quasi IDENTIQUE (défaut de géométrie, comme L18) ?"""

from app.config import connexion

conn = connexion(); cur = conn.cursor()

cur.execute("SELECT DISTINCT ref FROM lignes ORDER BY ref;")
refs = [r[0] for r in cur.fetchall()]

suspects = []
for ref in refs:
    cur.execute("SELECT DISTINCT nom FROM lignes WHERE ref = %s ORDER BY nom;", (ref,))
    sens = [r[0] for r in cur.fetchall()]
    if len(sens) != 2:
        continue  # ligne à sens unique ou données incomplètes, on l'ignore ici

    cur.execute("""
        SELECT a.nom,
               MAX(CASE WHEN l.nom = %s THEN al.ordre END) AS ordre_1,
               MAX(CASE WHEN l.nom = %s THEN al.ordre END) AS ordre_2
        FROM arrets_lignes al
        JOIN lignes l ON l.id = al.ligne_id AND l.ref = %s
        JOIN arrets a ON a.id = al.arret_id
        GROUP BY a.nom
        HAVING MAX(CASE WHEN l.nom = %s THEN al.ordre END) IS NOT NULL
           AND MAX(CASE WHEN l.nom = %s THEN al.ordre END) IS NOT NULL;
    """, (sens[0], sens[1], ref, sens[0], sens[1]))
    paires = cur.fetchall()

    if len(paires) < 3:
        continue  # pas assez d'arrêts communs pour juger

    # Une géométrie correcte : "ordre_1 + ordre_2" doit être ~constant
    # (somme des positions symétriques). Une géométrie défaillante :
    # "ordre_1 - ordre_2" est ~constant à la place (même sens, pas inversé).
    diffs = [abs(o1 - o2) for _, o1, o2 in paires]
    sommes = [o1 + o2 for _, o1, o2 in paires]
    variation_diff = max(diffs) - min(diffs)
    variation_somme = max(sommes) - min(sommes)

    if variation_diff < variation_somme:
        suspects.append((ref, len(paires), variation_diff, variation_somme))

print(f"{len(refs)} lignes vérifiées.\n")
print("Lignes suspectes (géométrie retour probablement NON inversée) :")
for ref, n, vd, vs in suspects:
    print(f"  {ref:5s} | {n:2d} arrêts communs | variation diff={vd:3d} (attendu faible) | variation somme={vs:3d} (attendu faible si correct)")

cur.close(); conn.close()
