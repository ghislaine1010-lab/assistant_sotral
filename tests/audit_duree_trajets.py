# -*- coding: utf-8 -*-
"""Audit des durées de trajet calculées (heure_arrivee - heure_depart)
   pour repérer des anomalies non détectées par l'audit initial :
   trajets anormalement courts (< 5 min, suspect) ou longs (> 90 min,
   suspect pour un trajet urbain), au-delà des cas déjà exclus comme
   incohérents (arrivée avant départ)."""

from app.config import connexion
from datetime import datetime, timedelta

conn = connexion(); cur = conn.cursor()

cur.execute("""
    SELECT ligne_ref, jour, course, heure_depart, heure_arrivee
    FROM horaires
    WHERE heure_depart IS NOT NULL AND heure_arrivee IS NOT NULL
    ORDER BY ligne_ref, jour, heure_depart;
""")
lignes = cur.fetchall()

tres_courts, tres_longs, normaux = [], [], 0
for ligne_ref, jour, course, depart, arrivee in lignes:
    # depart et arrivee sont déjà des objets time (colonne TIME en base)
    duree_min = (datetime.combine(datetime.today(), arrivee) -
                 datetime.combine(datetime.today(), depart)).total_seconds() / 60
    if duree_min < 0:
        continue  # déjà exclu par l'audit initial (incohérent), on l'ignore ici
    if duree_min < 5:
        tres_courts.append((ligne_ref, jour, course, depart, arrivee, duree_min))
    elif duree_min > 90:
        tres_longs.append((ligne_ref, jour, course, depart, arrivee, duree_min))
    else:
        normaux += 1

total = len(tres_courts) + len(tres_longs) + normaux
print(f"{total} trajets valides (arrivée après départ) analysés.\n")
print(f"Trajets normaux (5 à 90 min) : {normaux} ({normaux/total*100:.1f}%)")
print(f"Trajets très courts (< 5 min) : {len(tres_courts)} ({len(tres_courts)/total*100:.1f}%)")
for r in tres_courts[:10]:
    print(f"    {r[0]:5s} | {r[1]:15s} | {r[3]}->{r[4]} | {r[5]:.0f} min")
print(f"\nTrajets très longs (> 90 min) : {len(tres_longs)} ({len(tres_longs)/total*100:.1f}%)")
for r in tres_longs[:10]:
    print(f"    {r[0]:5s} | {r[1]:15s} | {r[3]}->{r[4]} | {r[5]:.0f} min")

cur.close(); conn.close()
