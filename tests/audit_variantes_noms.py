# -*- coding: utf-8 -*-
"""Combien d'arrêts existent en base sous deux noms légèrement
   différents (avec/sans le préfixe 'Arrêt '), qui pourraient être
   le même point physique mal unifié ?"""

from app.config import connexion

conn = connexion(); cur = conn.cursor()
cur.execute("SELECT id, nom FROM arrets ORDER BY nom;")
tous = cur.fetchall()

noms_sans_prefixe = {}
for id_, nom in tous:
    nom_nu = nom.replace("Arrêt ", "").strip()
    noms_sans_prefixe.setdefault(nom_nu, []).append(nom)

doublons_prefixe = {k: v for k, v in noms_sans_prefixe.items() if len(set(v)) > 1}

print(f"{len(tous)} arrêts au total.")
print(f"Groupes de noms différant seulement par le préfixe 'Arrêt ' : {len(doublons_prefixe)}")
for nom_nu, variantes in list(doublons_prefixe.items())[:20]:
    print(f"  {nom_nu:35s} -> variantes : {variantes}")

cur.close(); conn.close()
