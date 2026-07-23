# -*- coding: utf-8 -*-
"""Compare les 'sens_direction' transcrits dans horaires avec les vrais
   terminus des lignes (issus d'OpenStreetMap), pour détecter les cas
   où la transcription manuelle a copié le mauvais modèle de ligne."""

from app.config import connexion
import unicodedata

def normaliser(t):
    t = unicodedata.normalize("NFD", t.lower()).encode("ascii", "ignore").decode()
    return t

conn = connexion(); cur = conn.cursor()
cur.execute("SELECT DISTINCT ligne_ref FROM horaires ORDER BY ligne_ref;")
refs = [r[0] for r in cur.fetchall()]

suspects = []
for ref in refs:
    cur.execute("SELECT DISTINCT sens_direction FROM horaires WHERE ligne_ref = %s;", (ref,))
    sens_horaires = [r[0] for r in cur.fetchall()]

    cur.execute("SELECT terminus_depart, terminus_arrivee FROM lignes WHERE ref = %s;", (ref,))
    terminus_osm = cur.fetchall()
    mots_osm = set()
    for td, ta in terminus_osm:
        if td: mots_osm.update(normaliser(td).split())
        if ta: mots_osm.update(normaliser(ta).split())

    for s in sens_horaires:
        mots_sens = set(normaliser(s.replace("Départ ", "")).split())
        if not (mots_sens & mots_osm):
            suspects.append((ref, s, sorted(mots_osm)))

cur.close(); conn.close()

print(f"{len(suspects)} cas suspects sur {len(refs)} lignes vérifiées :\n")
for ref, sens, mots_osm in suspects:
    print(f"  {ref:5s} | horaires dit « {sens} »  |  terminus OSM contiennent : {mots_osm}")
