# -*- coding: utf-8 -*-
"""Un même code de bus (B1, B2...), sur une même ligne et un même jour,
   a-t-il des horaires cohérents (croissants dans le temps), ou des
   chevauchements suspects entre périodes (ex. un bus 'MIDI' qui part
   après un bus 'SOIR' du même code) ?"""

from app.config import connexion
from datetime import time

conn = connexion(); cur = conn.cursor()

cur.execute("""
    SELECT ligne_ref, jour, code_bus, periode, heure_depart
    FROM horaires
    WHERE heure_depart IS NOT NULL
    ORDER BY ligne_ref, jour, code_bus, heure_depart;
""")
lignes = cur.fetchall()

# Regrouper par (ligne, jour, code_bus) et vérifier la cohérence des périodes
from collections import defaultdict
groupes = defaultdict(list)
for ligne_ref, jour, code_bus, periode, heure in lignes:
    groupes[(ligne_ref, jour, code_bus)].append((heure, periode))

ORDRE_PERIODE = {"MATIN": 0, "MIDI": 1, "SOIR": 2}
anomalies = 0
total_groupes = 0
for (ligne_ref, jour, code_bus), horaires in groupes.items():
    total_groupes += 1
    horaires_tries = sorted(horaires, key=lambda x: x[0])
    periodes_num = [ORDRE_PERIODE.get(p, -1) for _, p in horaires_tries]
    # Une vraie anomalie : la période "recule" alors que l'heure avance
    for i in range(1, len(periodes_num)):
        if periodes_num[i] < periodes_num[i-1]:
            anomalies += 1
            print(f"  ANOMALIE : {ligne_ref} / {jour} / bus {code_bus} : "
                  f"{horaires_tries[i-1][1]} ({horaires_tries[i-1][0]}) suivi de "
                  f"{horaires_tries[i][1]} ({horaires_tries[i][0]})")
            break

print(f"\n{total_groupes} groupes (ligne/jour/bus) vérifiés.")
print(f"Groupes avec anomalie de période : {anomalies} ({anomalies/total_groupes*100:.1f}%)")

cur.close(); conn.close()
