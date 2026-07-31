# -*- coding: utf-8 -*-
"""Tentative de reconnexion ciblée des arrêts réellement isolés,
   avec un seuil élargi (200m au lieu de 30m), UNIQUEMENT pour ces
   arrêts précis -- sans toucher au reste du réseau déjà fonctionnel.
   Approximation assumée : l'arrêt reconnecté est ajouté en FIN de
   séquence de la ligne trouvée, pas à sa position exacte interpolée."""

import json
import math
from app.config import connexion

SEUIL_ELARGI = 200  # mètres
LAT0 = 6.2
MPD_LAT = 111320.0
MPD_LON = 111320.0 * math.cos(math.radians(LAT0))

def to_xy(lon, lat):
    return (lon * MPD_LON, lat * MPD_LAT)

def dist_point_segment(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    L2 = dx*dx + dy*dy
    if L2 == 0:
        return math.hypot(px-ax, py-ay)
    t = max(0.0, min(1.0, ((px-ax)*dx + (py-ay)*dy) / L2))
    qx, qy = ax + t*dx, ay + t*dy
    return math.hypot(px-qx, py-qy)

# ---------- 1. Charger le GeoJSON ----------
with open('/home/salim/Téléchargements/r_seau_de_ligne_de_bus_sotral.geojson') as f:
    feats = json.load(f)["features"]

tracés = {}  # osm_id -> liste de points (x, y)
for f in feats:
    g, p = f.get("geometry"), f.get("properties", {})
    if g and g["type"] in ("LineString", "MultiLineString") and p.get("route") == "bus":
        coords = g["coordinates"] if g["type"] == "LineString" else max(g["coordinates"], key=len)
        tracés[p.get("@id", "")] = [to_xy(c[0], c[1]) for c in coords]

# ---------- 2. Récupérer les 6 arrêts vraiment isolés ----------
conn = connexion(); cur = conn.cursor()
cur.execute("""
    SELECT a.id, a.nom, a.latitude, a.longitude FROM arrets a
    WHERE NOT EXISTS (
        SELECT 1 FROM arrets_lignes al
        JOIN arrets a2 ON a2.id = al.arret_id
        WHERE a2.nom = a.nom
    );
""")
isoles = cur.fetchall()
print(f"{len(isoles)} arrêt(s) vraiment isolé(s) à traiter.\n")

# ---------- 3. Pour chacun, chercher la ligne la plus proche (seuil élargi) ----------
reconnexions = 0
for arret_id, nom, lat, lon in isoles:
    px, py = to_xy(lon, lat)
    meilleure_ligne_osm_id, meilleure_distance = None, float("inf")
    for osm_id, points in tracés.items():
        for i in range(1, len(points)):
            d = dist_point_segment(px, py, *points[i-1], *points[i])
            if d < meilleure_distance:
                meilleure_distance = d
                meilleure_ligne_osm_id = osm_id

    if meilleure_distance <= SEUIL_ELARGI:
        cur.execute("SELECT id, ref FROM lignes WHERE osm_id = %s;", (meilleure_ligne_osm_id,))
        row = cur.fetchone()
        if row:
            ligne_id, ref = row
            cur.execute("SELECT MAX(ordre) FROM arrets_lignes WHERE ligne_id = %s;", (ligne_id,))
            ordre_max = cur.fetchone()[0] or 0
            cur.execute("""
                INSERT INTO arrets_lignes (ligne_id, arret_id, ordre)
                VALUES (%s, %s, %s);
            """, (ligne_id, arret_id, ordre_max + 1))
            print(f"  RECONNECTÉ : « {nom} » -> ligne {ref} (distance {meilleure_distance:.0f} m, ajouté en position {ordre_max+1})")
            reconnexions += 1
    else:
        print(f"  Non reconnecté : « {nom} » (ligne la plus proche à {meilleure_distance:.0f} m, > {SEUIL_ELARGI} m)")

conn.commit()
cur.close(); conn.close()
print(f"\nTotal reconnecté : {reconnexions} / {len(isoles)}")
