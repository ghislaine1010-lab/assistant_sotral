# -*- coding: utf-8 -*-
"""Calcule un temps moyen par arrêt, à partir des courses réelles dont
   la durée est connue et plausible (5 à 90 min, cf. audit du 30/07 qui
   avait exclu les cas 'retour dépôt'), rapportée au nombre total
   d'arrêts de la ligne concernée."""

from app.config import connexion
from datetime import datetime

conn = connexion(); cur = conn.cursor()

cur.execute("""
    SELECT ligne_ref, heure_depart, heure_arrivee
    FROM horaires
    WHERE heure_depart IS NOT NULL AND heure_arrivee IS NOT NULL;
""")
courses = cur.fetchall()

ratios = []
for ligne_ref, depart, arrivee in courses:
    duree_min = (datetime.combine(datetime.today(), arrivee) -
                 datetime.combine(datetime.today(), depart)).total_seconds() / 60
    if not (5 <= duree_min <= 90):
        continue  # exclut incohérences et cas "retour dépôt" déjà documentés

    cur.execute("""
        SELECT MAX(al.ordre) FROM arrets_lignes al
        JOIN lignes l ON l.id = al.ligne_id
        WHERE l.ref = %s;
    """, (ligne_ref,))
    nb_arrets_ligne = cur.fetchone()[0]
    if nb_arrets_ligne and nb_arrets_ligne > 1:
        ratios.append(duree_min / nb_arrets_ligne)

cur.close(); conn.close()

moyenne = sum(ratios) / len(ratios)
print(f"{len(ratios)} courses valides utilisées pour le calibrage.")
print(f"Temps moyen par arrêt : {moyenne:.2f} min/arrêt")
print(f"(soit environ {moyenne*60:.0f} secondes par arrêt)")
