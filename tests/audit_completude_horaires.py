# -*- coding: utf-8 -*-
"""Audit de complétude : pour chaque ligne et chaque jour (Lundi-Vendredi,
   Samedi), dispose-t-on d'au moins un horaire de départ exploitable ?
   Révèle les combinaisons ligne/jour totalement dépourvues de données,
   qui déclencheront systématiquement 'Aucun horaire connu' (SF4)."""

from app.config import connexion

conn = connexion(); cur = conn.cursor()

cur.execute("SELECT DISTINCT ligne_ref FROM horaires ORDER BY ligne_ref;")
refs = [r[0] for r in cur.fetchall()]

manques = []
for ref in refs:
    for jour in ["Lundi-Vendredi", "Samedi"]:
        cur.execute("""
            SELECT COUNT(*) FROM horaires
            WHERE ligne_ref = %s AND jour = %s AND heure_depart IS NOT NULL;
        """, (ref, jour))
        n = cur.fetchone()[0]
        if n == 0:
            manques.append((ref, jour))

print(f"{len(refs)} lignes vérifiées, sur 2 jours chacune ({len(refs)*2} combinaisons testées).\n")
print(f"Combinaisons ligne/jour SANS AUCUN horaire de départ exploitable : {len(manques)}")
for ref, jour in manques:
    print(f"  {ref:5s} | {jour}")

cur.close(); conn.close()
