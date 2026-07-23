from app.faits import arret_le_plus_proche

nom, lat, lon, distance_degres = arret_le_plus_proche(6.1319, 1.2228)
distance_metres = distance_degres * 111320  # conversion approximative degrés -> mètres
print(f"Arrêt le plus proche : « {nom} »")
print(f"Distance approximative : {distance_metres:.0f} mètres")
