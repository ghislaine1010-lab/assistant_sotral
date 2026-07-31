# -*- coding: utf-8 -*-
"""Avédji et Campus Sud sont-ils bien tous deux sur L16 ? Dans quel
   ordre, et dans quel(s) sens ? Un trajet DIRECT existe-t-il vraiment ?"""

from app.config import connexion
from app.recommandation import trajet_direct

conn = connexion(); cur = conn.cursor()

cur.execute("SELECT id, nom FROM lignes WHERE ref = 'L16' ORDER BY nom;")
sens_l16 = cur.fetchall()
print("Les deux sens de L16 :", sens_l16)

for ligne_id, nom_sens in sens_l16:
    cur.execute("""
        SELECT a.nom, al.ordre FROM arrets_lignes al
        JOIN arrets a ON a.id = al.arret_id
        WHERE al.ligne_id = %s AND (a.nom ILIKE '%%avedji%%' OR a.nom ILIKE '%%campus sud%%')
        ORDER BY al.ordre;
    """, (ligne_id,))
    print(f"\nDans le sens « {nom_sens} » :")
    for nom, ordre in cur.fetchall():
        print(f"   position {ordre:3d} : {nom}")

print("\n--- Test direct via la fonction du moteur ---")
resultat = trajet_direct(cur, "Arrêt Protestant Avédji", "Arrêt Campus Sud")
print("Résultat trajet_direct() :", resultat)

cur.close(); conn.close()
