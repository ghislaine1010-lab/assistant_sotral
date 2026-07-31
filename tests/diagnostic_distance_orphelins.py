# -*- coding: utf-8 -*-
"""Les arrêts orphelins sont-ils juste hors du seuil de 30m (limite de
   notre méthode), ou vraiment isolés de tout tracé de ligne ?"""

from app.config import connexion
import math

conn = connexion(); cur = conn.cursor()

MPD_LAT = 111320.0
MPD_LON = 111320.0 * math.cos(math.radians(6.2))

# Récupère tous les tracés de lignes (coordonnées)
cur.execute("SELECT id FROM lignes;")
# On a besoin des géométries -> on les recharge depuis le GeoJSON serait plus fiable,
# mais ici on approxime via les positions des arrêts déjà rattachés à chaque ligne.
cur.execute("""
    SELECT a.latitude, a.longitude FROM arrets a
    JOIN arrets_lignes al ON al.arret_id = a.id;
""")
points_lignes = cur.fetchall()

cur.execute("""
    SELECT a.nom, a.latitude, a.longitude FROM arrets a
    LEFT JOIN arrets_lignes al ON al.arret_id = a.id
    WHERE al.id IS NULL;
""")
orphelins = cur.fetchall()

def distance_m(lat1, lon1, lat2, lon2):
    dx = (lon1 - lon2) * MPD_LON
    dy = (lat1 - lat2) * MPD_LAT
    return math.hypot(dx, dy)

resultats = []
for nom, lat, lon in orphelins:
    if lat is None or lon is None:
        continue
    d_min = min(distance_m(lat, lon, plat, plon) for plat, plon in points_lignes)
    resultats.append((nom, d_min))

resultats.sort(key=lambda x: x[1])
proches = [r for r in resultats if r[1] <= 50]
moyens = [r for r in resultats if 50 < r[1] <= 150]
loins = [r for r in resultats if r[1] > 150]

print(f"Total orphelins analysés : {len(resultats)}")
print(f"  A moins de 50m d'un arrêt de ligne (seuil trop strict probable) : {len(proches)}")
print(f"  Entre 50 et 150m : {len(moyens)}")
print(f"  Plus de 150m (vraiment isolés) : {len(loins)}")

print("\nLes 10 plus proches (candidats à un seuil élargi) :")
for nom, d in resultats[:10]:
    print(f"  {nom:35s} : {d:.0f} m")

cur.close(); conn.close()
