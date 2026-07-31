# -*- coding: utf-8 -*-
"""Pour les 3 combinaisons sans horaire de départ : y a-t-il des
   enregistrements du tout, ou sont-ils tous incomplets ?"""

from app.config import connexion

conn = connexion(); cur = conn.cursor()

for ref, jour in [("L19", "Samedi"), ("L2", "Lundi-Vendredi"), ("L6", "Lundi-Vendredi")]:
    cur.execute("""
        SELECT COUNT(*), COUNT(heure_depart), COUNT(heure_arrivee)
        FROM horaires WHERE ligne_ref = %s AND jour = %s;
    """, (ref, jour))
    total, avec_depart, avec_arrivee = cur.fetchone()
    print(f"{ref} ({jour}) : {total} enregistrement(s) au total, "
          f"{avec_depart} avec heure de départ, {avec_arrivee} avec heure d'arrivée")

cur.close(); conn.close()
