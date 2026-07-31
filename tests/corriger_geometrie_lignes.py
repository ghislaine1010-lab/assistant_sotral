# -*- coding: utf-8 -*-
"""Correction générale : pour chaque ligne où le sens retour partage
   quasiment le même ordre que l'aller (au lieu d'être inversé), on
   recalcule l'ordre du second sens comme le MIROIR de son propre ordre
   d'origine. Passage par des valeurs négatives temporaires pour éviter
   toute collision avec la contrainte d'unicité (ligne_id, ordre)
   pendant le calcul."""

from app.config import connexion

conn = connexion(); cur = conn.cursor()

cur.execute("SELECT DISTINCT ref FROM lignes ORDER BY ref;")
refs = [r[0] for r in cur.fetchall()]

lignes_corrigees = []
for ref in refs:
    cur.execute("SELECT DISTINCT nom, id FROM lignes WHERE ref = %s ORDER BY nom;", (ref,))
    lignes_du_ref = cur.fetchall()
    if len(lignes_du_ref) != 2:
        continue
    (nom1, id1), (nom2, id2) = lignes_du_ref

    cur.execute("""
        SELECT a.nom,
               MAX(CASE WHEN al.ligne_id = %s THEN al.ordre END),
               MAX(CASE WHEN al.ligne_id = %s THEN al.ordre END)
        FROM arrets_lignes al
        JOIN arrets a ON a.id = al.arret_id
        WHERE al.ligne_id IN (%s, %s)
        GROUP BY a.nom
        HAVING MAX(CASE WHEN al.ligne_id = %s THEN al.ordre END) IS NOT NULL
           AND MAX(CASE WHEN al.ligne_id = %s THEN al.ordre END) IS NOT NULL;
    """, (id1, id2, id1, id2, id1, id2))
    paires = cur.fetchall()
    if len(paires) < 3:
        continue

    diffs = [abs(o1 - o2) for _, o1, o2 in paires]
    sommes = [o1 + o2 for _, o1, o2 in paires]
    if (max(diffs) - min(diffs)) < (max(sommes) - min(sommes)):
        cur.execute("SELECT MAX(ordre) FROM arrets_lignes WHERE ligne_id = %s;", (id2,))
        ordre_max = cur.fetchone()[0]

        # Étape 1 : passage par des valeurs négatives (jamais en collision
        # avec les valeurs positives existantes, donc aucune violation
        # possible de la contrainte d'unicité pendant ce calcul).
        cur.execute("UPDATE arrets_lignes SET ordre = -ordre WHERE ligne_id = %s;", (id2,))
        # Étape 2 : valeur finale = ordre_max + 1 - ordre_original
        #                         = ordre_max + 1 + ordre_actuel (négatif)
        cur.execute("UPDATE arrets_lignes SET ordre = %s + 1 + ordre WHERE ligne_id = %s;",
                    (ordre_max, id2))

        lignes_corrigees.append((ref, nom2, ordre_max))

conn.commit()
cur.close(); conn.close()

print(f"{len(lignes_corrigees)} lignes corrigées (ordre du 2e sens inversé) :")
for ref, nom, n in lignes_corrigees:
    print(f"  {ref:5s} | sens inversé : « {nom} » ({n} arrêts)")
