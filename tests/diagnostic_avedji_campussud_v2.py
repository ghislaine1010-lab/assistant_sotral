# -*- coding: utf-8 -*-
"""Reprise du diagnostic précédent, corrigé : la recherche par ILIKE
   doit inclure l'accent réel (Avédji), sinon elle rate silencieusement
   l'arrêt (erreur du script de diagnostic précédent, pas du système)."""

from app.config import connexion
from app.recommandation import trajet_direct
from app.nlp import normaliser

conn = connexion(); cur = conn.cursor()

cur.execute("SELECT id, nom FROM lignes WHERE ref = 'L16' ORDER BY nom;")
sens_l16 = cur.fetchall()

for ligne_id, nom_sens in sens_l16:
    cur.execute("""
        SELECT a.nom, al.ordre FROM arrets_lignes al
        JOIN arrets a ON a.id = al.arret_id
        WHERE al.ligne_id = %s
        ORDER BY al.ordre;
    """, (ligne_id,))
    tous = cur.fetchall()
    # Filtrage en Python avec normalisation (insensible aux accents), pas en SQL
    filtres = [(nom, ordre) for nom, ordre in tous
               if "avedji" in normaliser(nom) or "campus sud" in normaliser(nom)]
    print(f"\nDans le sens « {nom_sens} » ({len(tous)} arrêts au total) :")
    for nom, ordre in filtres:
        print(f"   position {ordre:3d} : {nom}")

print("\n--- Test direct via la fonction du moteur ---")
resultat = trajet_direct(cur, "Arrêt Protestant Avédji", "Arrêt Campus Sud")
print("Résultat trajet_direct() :", resultat)

cur.close(); conn.close()
