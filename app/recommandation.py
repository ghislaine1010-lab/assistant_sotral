# -*- coding: utf-8 -*-
"""Moteur de recommandation d'itinéraires (SF3). La correspondance se
   fait par NOM d'arrêt, en tenant compte des VARIANTES de noms
   (ex. « Arrêt Protestant Avédji » / « Protestant Avédji ») qui
   désignent le même lieu physique sous deux formes légèrement
   différentes dans les données OpenStreetMap (11 cas identifiés par
   audit le 31/07)."""

from app.config import connexion

def _variantes(nom):
    """Renvoie le nom original ET sa variante avec/sans le préfixe
       'Arrêt ', pour couvrir les doublons de nommage OSM."""
    variantes = {nom}
    if nom.startswith("Arrêt "):
        variantes.add(nom[len("Arrêt "):])
    else:
        variantes.add("Arrêt " + nom)
    return list(variantes)


def trajet_direct(cur, depart, destination):
    variantes_dep = _variantes(depart)
    variantes_dest = _variantes(destination)
    cur.execute("""
        SELECT l.ref, l.nom, a1.nom, a2.nom, al1.ordre, al2.ordre
        FROM arrets_lignes al1
        JOIN arrets_lignes al2 ON al1.ligne_id = al2.ligne_id
        JOIN lignes l ON l.id = al1.ligne_id
        JOIN arrets a1 ON a1.id = al1.arret_id
        JOIN arrets a2 ON a2.id = al2.arret_id
        WHERE a1.nom = ANY(%s) AND a2.nom = ANY(%s) AND al1.ordre < al2.ordre
        ORDER BY (al2.ordre - al1.ordre) ASC
        LIMIT 1;
    """, (variantes_dep, variantes_dest))
    resultat = cur.fetchone()
    if resultat:
        ref, nom_ligne, _, _, o1, o2 = resultat
        # On réaffiche les noms d'origine demandés par l'usager (plus lisibles)
        return (ref, nom_ligne, depart, destination, o1, o2)
    return None


def trajet_avec_correspondance(cur, depart, destination):
    variantes_dep = _variantes(depart)
    variantes_dest = _variantes(destination)
    cur.execute("""
        SELECT l1.ref, l1.nom, a_t1.nom, l2.ref, l2.nom
        FROM arrets_lignes al_dep
        JOIN arrets a_dep ON a_dep.id = al_dep.arret_id AND a_dep.nom = ANY(%s)
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
        JOIN arrets a_arr ON a_arr.id = al_arr.arret_id AND a_arr.nom = ANY(%s)
        LIMIT 1;
    """, (variantes_dep, variantes_dest))
    return cur.fetchone()


def trouver_itineraire(depart, destination):
    conn = connexion(); cur = conn.cursor()

    direct = trajet_direct(cur, depart, destination)
    if direct:
        ref, nom_ligne, a1, a2, o1, o2 = direct
        cur.close(); conn.close()
        texte = (f"Prenez la ligne {ref} ({nom_ligne}) depuis « {a1} » "
                 f"jusqu'à « {a2} » ({o2 - o1} arrêt(s) de trajet direct).")
        return {"type": "direct", "texte": texte, "lignes": [ref], "arrets": [a1, a2]}

    from app.faits import arret_est_isole
    if arret_est_isole(depart):
        cur.close(); conn.close()
        return {"type": "aucun", "lignes": [], "arrets": [],
                "texte": (f"L'arrêt « {depart} » figure dans nos données mais n'est "
                          f"actuellement rattaché à aucune ligne connue (limite des "
                          f"données cartographiques disponibles).")}
    if arret_est_isole(destination):
        cur.close(); conn.close()
        return {"type": "aucun", "lignes": [], "arrets": [],
                "texte": (f"L'arrêt « {destination} » figure dans nos données mais n'est "
                          f"actuellement rattaché à aucune ligne connue (limite des "
                          f"données cartographiques disponibles).")}

    corresp = trajet_avec_correspondance(cur, depart, destination)
    cur.close(); conn.close()
    if corresp:
        ref1, nom1, transfert, ref2, nom2 = corresp
        texte = (f"Prenez la ligne {ref1} ({nom1}) jusqu'à « {transfert} », "
                 f"puis changez pour la ligne {ref2} ({nom2}) jusqu'à « {destination} ».")
        return {"type": "correspondance", "texte": texte, "lignes": [ref1, ref2],
                "arrets": [depart, transfert, destination]}

    return {"type": "aucun", "texte": f"Aucun itinéraire trouvé entre « {depart} » et « {destination} ».",
            "lignes": [], "arrets": []}
