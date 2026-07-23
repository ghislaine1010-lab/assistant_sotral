# -*- coding: utf-8 -*-
"""Moteur de recommandation d'itinéraires (SF3) — v2 : la correspondance
   se fait par NOM d'arrêt (et non par identifiant), pour tenir compte
   des arrêts dupliqués aller/retour dans les données OpenStreetMap."""

from app.config import connexion

def trajet_direct(cur, depart, destination):
    cur.execute("""
        SELECT l.ref, l.nom, a1.nom, a2.nom, al1.ordre, al2.ordre
        FROM arrets_lignes al1
        JOIN arrets_lignes al2 ON al1.ligne_id = al2.ligne_id
        JOIN lignes l ON l.id = al1.ligne_id
        JOIN arrets a1 ON a1.id = al1.arret_id
        JOIN arrets a2 ON a2.id = al2.arret_id
        WHERE a1.nom = %s AND a2.nom = %s AND al1.ordre < al2.ordre
        ORDER BY (al2.ordre - al1.ordre) ASC
        LIMIT 1;
    """, (depart, destination))
    return cur.fetchone()

def trajet_avec_correspondance(cur, depart, destination):
    cur.execute("""
        SELECT l1.ref, l1.nom, a_t1.nom, l2.ref, l2.nom
        FROM arrets_lignes al_dep
        JOIN arrets a_dep ON a_dep.id = al_dep.arret_id AND a_dep.nom = %s
        JOIN lignes l1 ON l1.id = al_dep.ligne_id
        JOIN arrets_lignes al_t1 ON al_t1.ligne_id = al_dep.ligne_id
                                 AND al_t1.ordre > al_dep.ordre
        JOIN arrets a_t1 ON a_t1.id = al_t1.arret_id
        JOIN arrets a_t2 ON a_t2.nom = a_t1.nom AND a_t2.id <> a_t1.id
        JOIN arrets_lignes al_t2 ON al_t2.arret_id = a_t2.id
                                 AND al_t2.ligne_id <> al_dep.ligne_id
        JOIN lignes l2 ON l2.id = al_t2.ligne_id
        JOIN arrets_lignes al_arr ON al_arr.ligne_id = al_t2.ligne_id
                                   AND al_arr.ordre > al_t2.ordre
        JOIN arrets a_arr ON a_arr.id = al_arr.arret_id AND a_arr.nom = %s
        LIMIT 1;
    """, (depart, destination))
    return cur.fetchone()

def recommander(depart, destination):
    conn = connexion()
    cur = conn.cursor()

    direct = trajet_direct(cur, depart, destination)
    if direct:
        ref, nom_ligne, a1, a2, o1, o2 = direct
        cur.close(); conn.close()
        return (f"Prenez la ligne {ref} ({nom_ligne}) depuis « {a1} » "
                f"jusqu'à « {a2} » ({o2 - o1} arrêt(s) de trajet direct).")

    corresp = trajet_avec_correspondance(cur, depart, destination)
    cur.close(); conn.close()
    if corresp:
        ref1, nom1, transfert, ref2, nom2 = corresp
        return (f"Prenez la ligne {ref1} ({nom1}) jusqu'à « {transfert} », "
                f"puis changez pour la ligne {ref2} ({nom2}) jusqu'à « {destination} ».")

    return f"Aucun itinéraire trouvé entre « {depart} » et « {destination} » (SF8 : à gérer)."

if __name__ == "__main__":
    essais = [
        ("BIA", "Togocel Zanguéra"),
        ("Adjololo", "AD Zanguéra"),
    ]
    for depart, destination in essais:
        print(f"\nDépart : {depart}  ->  Destination : {destination}")
        print(" ", recommander(depart, destination))

def trouver_itineraire(depart, destination):
    """Version structurée de recommander() : renvoie aussi la ou les
       références de lignes utilisées, pour pouvoir ensuite consulter
       leurs horaires réels."""
    conn = connexion(); cur = conn.cursor()

    direct = trajet_direct(cur, depart, destination)
    if direct:
        ref, nom_ligne, a1, a2, o1, o2 = direct
        cur.close(); conn.close()
        texte = (f"Prenez la ligne {ref} ({nom_ligne}) depuis « {a1} » "
                 f"jusqu'à « {a2} » ({o2 - o1} arrêt(s) de trajet direct).")
        return {"type": "direct", "texte": texte, "lignes": [ref]}

    corresp = trajet_avec_correspondance(cur, depart, destination)
    cur.close(); conn.close()
    if corresp:
        ref1, nom1, transfert, ref2, nom2 = corresp
        texte = (f"Prenez la ligne {ref1} ({nom1}) jusqu'à « {transfert} », "
                 f"puis changez pour la ligne {ref2} ({nom2}) jusqu'à « {destination} ».")
        return {"type": "correspondance", "texte": texte, "lignes": [ref1, ref2]}

    return {"type": "aucun", "texte": f"Aucun itinéraire trouvé entre « {depart} » et « {destination} ».", "lignes": []}
