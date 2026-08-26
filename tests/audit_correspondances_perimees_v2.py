# -*- coding: utf-8 -*-
"""Reprise du diagnostic précédent, corrigé : comparaison par NOM
   d'arrêt (comme le fait déjà app/recommandation.py depuis la
   correction des variantes), pas par identifiant technique."""

from app.config import connexion

conn = connexion(); cur = conn.cursor()

cur.execute("SELECT COUNT(*) FROM correspondances;")
nb_enregistrees = cur.fetchone()[0]

cur.execute("""
    SELECT COUNT(DISTINCT LEAST(l1.ref, l2.ref) || '-' || GREATEST(l1.ref, l2.ref))
    FROM arrets_lignes al1
    JOIN arrets a1 ON a1.id = al1.arret_id
    JOIN lignes l1 ON l1.id = al1.ligne_id
    JOIN arrets a2 ON a2.nom = a1.nom
    JOIN arrets_lignes al2 ON al2.arret_id = a2.id
    JOIN lignes l2 ON l2.id = al2.ligne_id
    WHERE l1.ref <> l2.ref;
""")
nb_reelles = cur.fetchone()[0]

print(f"Correspondances enregistrées : {nb_enregistrees}")
print(f"Correspondances réelles (comparaison par NOM, corrigée) : {nb_reelles}")
print(f"Écart : {nb_reelles - nb_enregistrees}")

cur.close(); conn.close()
