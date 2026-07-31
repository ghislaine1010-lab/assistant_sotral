# -*- coding: utf-8 -*-
"""Combien de lignes ont un 'sens_direction' (horaires transcrits) qui
   ne correspond à AUCUN mot des vrais terminus géographiques (OSM) ?"""

from app.config import connexion
import unicodedata

def normaliser(t):
    return unicodedata.normalize("NFD", t.lower()).encode("ascii", "ignore").decode()

conn = connexion(); cur = conn.cursor()
cur.execute("SELECT DISTINCT ligne_ref FROM horaires ORDER BY ligne_ref;")
refs = [r[0] for r in cur.fetchall()]

suspectes, coherentes = [], []
for ref in refs:
    cur.execute("SELECT DISTINCT sens_direction FROM horaires WHERE ligne_ref = %s;", (ref,))
    sens_horaires = [r[0] for r in cur.fetchall()]

    cur.execute("SELECT terminus_depart, terminus_arrivee FROM lignes WHERE ref = %s;", (ref,))
    terminus_osm = cur.fetchall()
    mots_osm = set()
    for td, ta in terminus_osm:
        if td: mots_osm.update(normaliser(td).split())
        if ta: mots_osm.update(normaliser(ta).split())

    ok = True
    for s in sens_horaires:
        mots_sens = set(normaliser(s.replace("Départ ", "")).split())
        if mots_osm and not (mots_sens & mots_osm):
            ok = False
    (coherentes if ok else suspectes).append(ref)

print(f"{len(refs)} lignes vérifiées.")
print(f"Cohérentes (vocabulaire compatible) : {len(coherentes)} -> {coherentes}")
print(f"Incohérentes (vocabulaire différent) : {len(suspectes)} -> {suspectes}")
