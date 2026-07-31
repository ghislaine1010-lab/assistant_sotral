# -*- coding: utf-8 -*-
"""'Akato' est-il un arrêt réel sur le trajet de la ligne 16 ?"""

from app.config import connexion

conn = connexion(); cur = conn.cursor()
cur.execute("""
    SELECT l.nom AS sens, al.ordre, a.nom
    FROM arrets_lignes al
    JOIN lignes l ON l.id = al.ligne_id AND l.ref = 'L16'
    JOIN arrets a ON a.id = al.arret_id
    WHERE a.nom ILIKE '%akato%'
    ORDER BY al.ordre;
""")
resultats = cur.fetchall()
cur.close(); conn.close()

if resultats:
    for sens, ordre, nom in resultats:
        print(f"  Trouvé : « {nom} » à la position {ordre} du sens « {sens} »")
else:
    print("  Aucun arrêt contenant « Akato » trouvé sur la ligne 16.")
