# -*- coding: utf-8 -*-
"""La table 'correspondances' a-t-elle été recalculée après les
   corrections de géométrie et de reconnexion des arrêts, ou décrit-elle
   encore l'ancien état (potentiellement incomplet) du réseau ?"""

from app.config import connexion

conn = connexion(); cur = conn.cursor()

# 1. Nombre de correspondances déjà enregistrées (table matérialisée)
cur.execute("SELECT COUNT(*) FROM correspondances;")
nb_enregistrees = cur.fetchone()[0]

# 2. Nombre de correspondances RÉELLES si on les recalcule à la volée,
#    directement à partir de l'état actuel de arrets_lignes (source de vérité)
cur.execute("""
    SELECT COUNT(DISTINCT LEAST(l1.ref, l2.ref) || '-' || GREATEST(l1.ref, l2.ref))
    FROM arrets_lignes al1
    JOIN arrets a ON a.id = al1.arret_id
    JOIN lignes l1 ON l1.id = al1.ligne_id
    JOIN arrets_lignes al2 ON al2.arret_id = al1.arret_id AND al2.ligne_id <> al1.ligne_id
    JOIN lignes l2 ON l2.id = al2.ligne_id
    WHERE l1.ref <> l2.ref;
""")
nb_reelles = cur.fetchone()[0]

print(f"Correspondances enregistrées dans la table 'correspondances' : {nb_enregistrees}")
print(f"Correspondances réelles recalculées depuis l'état actuel de arrets_lignes : {nb_reelles}")
print(f"Écart : {nb_reelles - nb_enregistrees}")

cur.close(); conn.close()
