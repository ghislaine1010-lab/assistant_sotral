# -*- coding: utf-8 -*-
"""Le quartier Adakpamé est-il structurellement coupé du quartier
   Campus, ou seulement certaines paires d'arrêts précises ?"""

from app.config import connexion
from app.nlp import normaliser

conn = connexion(); cur = conn.cursor()

def arrets_et_lignes(mot_cle):
    cur.execute("""
        SELECT DISTINCT a.nom, l.ref FROM arrets_lignes al
        JOIN arrets a ON a.id = al.arret_id
        JOIN lignes l ON l.id = al.ligne_id
        WHERE a.nom ILIKE %s
        ORDER BY a.nom;
    """, (f"%{mot_cle}%",))
    return cur.fetchall()

adakpame = arrets_et_lignes("adakpam")
campus = arrets_et_lignes("campus")

lignes_adakpame = {ref for _, ref in adakpame}
lignes_campus = {ref for _, ref in campus}
lignes_communes = lignes_adakpame & lignes_campus

print(f"Arrêts « Adakpamé » ({len(set(n for n,_ in adakpame))} uniques), lignes desservantes : {sorted(lignes_adakpame)}")
print(f"Arrêts « Campus » ({len(set(n for n,_ in campus))} uniques), lignes desservantes : {sorted(lignes_campus)}")
print(f"\nLignes en commun entre les deux quartiers : {sorted(lignes_communes)}")

# Pour chaque ligne commune, teste s'il existe AU MOINS UNE paire
# (arrêt Adakpamé, arrêt Campus) dans le bon ordre (direct possible)
for ref in sorted(lignes_communes):
    cur.execute("""
        SELECT a1.nom, al1.ordre, a2.nom, al2.ordre, l.nom
        FROM arrets_lignes al1
        JOIN arrets_lignes al2 ON al1.ligne_id = al2.ligne_id
        JOIN lignes l ON l.id = al1.ligne_id AND l.ref = %s
        JOIN arrets a1 ON a1.id = al1.arret_id AND a1.nom ILIKE %s
        JOIN arrets a2 ON a2.id = al2.arret_id AND a2.nom ILIKE %s
        WHERE al1.ordre < al2.ordre
        LIMIT 3;
    """, (ref, "%adakpam%", "%campus%"))
    resultats = cur.fetchall()
    print(f"\n  Ligne {ref} -- paires valides (ordre croissant) Adakpamé -> Campus : {len(resultats)}")
    for r in resultats:
        print("   ", r)

cur.close(); conn.close()
