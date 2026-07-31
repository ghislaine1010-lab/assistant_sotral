# -*- coding: utf-8 -*-
"""Les deux sens de L18 ont-ils un ordre systématiquement identique
   au lieu d'être inversés l'un par rapport à l'autre ?"""

from app.config import connexion

conn = connexion(); cur = conn.cursor()
cur.execute("""
    SELECT a.nom,
           MAX(CASE WHEN l.nom = 'Adakpamé - TERMINUS CAMPUS NORD' THEN al.ordre END) AS ordre_aller,
           MAX(CASE WHEN l.nom = 'TERMINUS CAMPUS NORD - Adakpamé' THEN al.ordre END) AS ordre_retour
    FROM arrets_lignes al
    JOIN lignes l ON l.id = al.ligne_id AND l.ref = 'L18'
    JOIN arrets a ON a.id = al.arret_id
    GROUP BY a.nom
    HAVING MAX(CASE WHEN l.nom = 'Adakpamé - TERMINUS CAMPUS NORD' THEN al.ordre END) IS NOT NULL
       AND MAX(CASE WHEN l.nom = 'TERMINUS CAMPUS NORD - Adakpamé' THEN al.ordre END) IS NOT NULL
    ORDER BY ordre_aller
    LIMIT 15;
""")
for nom, aller, retour in cur.fetchall():
    print(f"  {nom:35s} | aller: {aller:3d} | retour: {retour:3d}")
cur.close(); conn.close()
