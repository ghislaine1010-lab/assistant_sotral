# -*- coding: utf-8 -*-
"""« Eglise des AD Adakpamé » et « Arrêt Campus Sud » partagent la
   ligne L18 — pourquoi le trajet direct échoue-t-il alors ?"""

from app.config import connexion

conn = connexion(); cur = conn.cursor()
cur.execute("""
    SELECT l.nom AS sens, al.ordre, a.nom
    FROM arrets_lignes al
    JOIN lignes l ON l.id = al.ligne_id AND l.ref = 'L18'
    JOIN arrets a ON a.id = al.arret_id
    WHERE a.nom IN ('Eglise des AD Adakpamé', 'Arrêt Campus Sud')
    ORDER BY l.nom, al.ordre;
""")
for sens, ordre, nom in cur.fetchall():
    print(f"  Sens « {sens} » | position {ordre} | {nom}")
cur.close(); conn.close()
