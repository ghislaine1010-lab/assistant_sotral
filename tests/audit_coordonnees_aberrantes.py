# -*- coding: utf-8 -*-
"""Audit géographique : tous les arrêts sont-ils bien situés dans une
   zone réaliste autour de Lomé (env. 6.0-6.35 lat, 1.05-1.35 lon) ?
   Détecte les coordonnées aberrantes (saisie erronée, lat/lon inversées,
   ou arrêt géographiquement isolé du reste du réseau)."""

from app.config import connexion

# Zone large mais raisonnable autour de Lomé (marge de sécurité incluse)
LAT_MIN, LAT_MAX = 6.00, 6.40
LON_MIN, LON_MAX = 1.00, 1.40

conn = connexion(); cur = conn.cursor()
cur.execute("SELECT nom, latitude, longitude FROM arrets ORDER BY nom;")
arrets = cur.fetchall()

hors_zone = []
for nom, lat, lon in arrets:
    if lat is None or lon is None:
        hors_zone.append((nom, lat, lon, "coordonnée manquante"))
    elif not (LAT_MIN <= lat <= LAT_MAX and LON_MIN <= lon <= LON_MAX):
        hors_zone.append((nom, lat, lon, "hors zone attendue"))

print(f"{len(arrets)} arrêts vérifiés.")
print(f"Coordonnées hors zone ou manquantes : {len(hors_zone)}")
for nom, lat, lon, raison in hors_zone:
    print(f"  {nom:35s} | lat={lat} lon={lon} | {raison}")

# Vérifie aussi la dispersion générale (min/max réels observés)
lats = [lat for _, lat, lon in arrets if lat is not None]
lons = [lon for _, lat, lon in arrets if lon is not None]
print(f"\nÉtendue réelle observée : latitude [{min(lats):.4f}, {max(lats):.4f}], "
      f"longitude [{min(lons):.4f}, {max(lons):.4f}]")

cur.close(); conn.close()
