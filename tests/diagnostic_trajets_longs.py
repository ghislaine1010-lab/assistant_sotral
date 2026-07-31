# -*- coding: utf-8 -*-
"""Les trajets 'anormalement longs' correspondent-ils tous à la
   dernière course du service (retour au dépôt), plutôt qu'à un vrai
   trajet point à point mal transcrit ?"""

from app.config import connexion
from datetime import datetime
from collections import Counter

conn = connexion(); cur = conn.cursor()
cur.execute("""
    SELECT ligne_ref, jour, course, heure_depart, heure_arrivee
    FROM horaires
    WHERE heure_depart IS NOT NULL AND heure_arrivee IS NOT NULL
    ORDER BY ligne_ref, jour, heure_depart;
""")
lignes = cur.fetchall()

courses_longues = Counter()
arrivees_longues = Counter()
for ligne_ref, jour, course, depart, arrivee in lignes:
    duree_min = (datetime.combine(datetime.today(), arrivee) -
                 datetime.combine(datetime.today(), depart)).total_seconds() / 60
    if duree_min > 90:
        courses_longues[course] += 1
        arrivees_longues[str(arrivee)] += 1

print("Répartition des trajets longs par numéro de course :")
for course, n in courses_longues.most_common():
    print(f"  {course:12s} : {n} cas")

print("\nRépartition des trajets longs par heure d'ARRIVÉE (recherche d'une valeur récurrente) :")
for arrivee, n in arrivees_longues.most_common():
    print(f"  {arrivee} : {n} cas")

cur.close(); conn.close()
