# -*- coding: utf-8 -*-
"""Récupère des faits RÉELS depuis la base de connaissances, pour
   répondre aux questions générales sans jamais laisser le LLM
   inventer un fait qui n'existe pas dans les données SOTRAL."""

from app.config import connexion

def jours_de_service_connus():
    conn = connexion(); cur = conn.cursor()
    cur.execute("SELECT DISTINCT jour FROM horaires ORDER BY jour;")
    jours = [l[0] for l in cur.fetchall()]
    cur.close(); conn.close()
    return jours

def lignes_desservant(nom_arret):
    conn = connexion(); cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT l.ref FROM arrets_lignes al
        JOIN arrets a ON a.id = al.arret_id AND a.nom = %s
        JOIN lignes l ON l.id = al.ligne_id
        ORDER BY l.ref;
    """, (nom_arret,))
    lignes = [l[0] for l in cur.fetchall()]
    cur.close(); conn.close()
    return lignes

def correspondances_a(nom_arret):
    conn = connexion(); cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT ligne_a, ligne_b FROM correspondances WHERE arret_nom = %s;
    """, (nom_arret,))
    paires = cur.fetchall()
    cur.close(); conn.close()
    lignes = sorted({l for paire in paires for l in paire})
    return lignes

def statistiques_reseau():
    conn = connexion(); cur = conn.cursor()
    cur.execute("SELECT (SELECT COUNT(*) FROM lignes), (SELECT COUNT(*) FROM arrets), (SELECT COUNT(*) FROM horaires);")
    nb_lignes, nb_arrets, nb_horaires = cur.fetchone()
    cur.close(); conn.close()
    return {"lignes": nb_lignes, "arrets": nb_arrets, "horaires": nb_horaires}

def prochains_departs(ref_ligne, jour, type_moment, valeur, limite=3):
    """Va chercher les VRAIS prochains départs dans la base, jamais inventés.
       DISTINCT sur (sens, periode, heure) pour éviter les doublons dus
       aux différents bus (B1, B2...) partageant le même horaire."""
    conn = connexion(); cur = conn.cursor()
    if type_moment == "heure":
        cur.execute("""
            SELECT DISTINCT sens_direction, periode, heure_depart FROM horaires
            WHERE ligne_ref = %s AND jour = %s AND heure_depart IS NOT NULL
              AND heure_depart >= %s
            ORDER BY heure_depart ASC LIMIT %s;
        """, (ref_ligne, jour, valeur, limite))
    else:
        cur.execute("""
            SELECT DISTINCT sens_direction, periode, heure_depart FROM horaires
            WHERE ligne_ref = %s AND jour = %s AND periode = %s
              AND heure_depart IS NOT NULL
            ORDER BY heure_depart ASC LIMIT %s;
        """, (ref_ligne, jour, valeur, limite))
    resultats = cur.fetchall()
    cur.close(); conn.close()
    return resultats

def arret_le_plus_proche(latitude, longitude):
    """Trouve l'arrêt le plus proche d'une position GPS donnée
       (formule de distance euclidienne simple, suffisante à l'échelle
       d'une ville ; une vraie distance terrestre utiliserait la formule
       de Haversine pour plus de précision)."""
    conn = connexion(); cur = conn.cursor()
    cur.execute("""
        SELECT nom, latitude, longitude,
               SQRT(POWER(latitude - %s, 2) + POWER(longitude - %s, 2)) AS distance
        FROM arrets
        ORDER BY distance ASC
        LIMIT 1;
    """, (latitude, longitude))
    resultat = cur.fetchone()
    cur.close(); conn.close()
    return resultat

def coordonnees_arrets(noms):
    """Renvoie, pour une liste de noms d'arrêts, leurs coordonnées GPS
       (utilisé pour afficher l'itinéraire sur la carte — SF7)."""
    conn = connexion(); cur = conn.cursor()
    resultats = []
    for nom in noms:
        cur.execute("SELECT latitude, longitude FROM arrets WHERE nom = %s LIMIT 1;", (nom,))
        row = cur.fetchone()
        resultats.append({"nom": nom, "latitude": row[0] if row else None,
                           "longitude": row[1] if row else None})
    cur.close(); conn.close()
    return resultats

def arret_est_isole(nom):
    """Vérifie si un arrêt existe dans la base mais n'est rattaché à
    AUCUNE ligne (limite de connectivité réelle, distincte d'un arrêt
    simplement non reconnu)."""
    conn = connexion(); cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(*) FROM arrets_lignes al
        JOIN arrets a ON a.id = al.arret_id
        WHERE a.nom = %s;
    """, (nom,))
    n = cur.fetchone()[0]
    cur.close(); conn.close()
    return n == 0

def tableau_de_bord():
    """Rassemble les statistiques du réseau (en direct depuis la base)
       et le résumé du dernier audit de qualité des données (fixe,
       daté de la session du 30/07 -- à mettre à jour si un nouvel
       audit est mené) pour l'affichage du tableau de bord."""
    conn = connexion(); cur = conn.cursor()
    cur.execute("""
        SELECT (SELECT COUNT(*) FROM lignes),
               (SELECT COUNT(*) FROM arrets),
               (SELECT COUNT(*) FROM horaires),
               (SELECT COUNT(*) FROM correspondances),
               (SELECT COUNT(DISTINCT ref) FROM lignes);
    """)
    nb_lignes, nb_arrets, nb_horaires, nb_correspondances, nb_refs = cur.fetchone()
    cur.close(); conn.close()

    return {
        "reseau": {
            "lignes": nb_lignes, "references_lignes": nb_refs,
            "arrets": nb_arrets, "horaires": nb_horaires,
            "correspondances": nb_correspondances,
        },
        "audit_qualite": {
            "date": "30/07/2026",
            "dimensions": [
                {"nom": "Géométrie des lignes (aller/retour)", "ampleur": "71 % (12/17 lignes)", "statut": "corrige"},
                {"nom": "Connectivité des arrêts", "ampleur": "23,5 % apparent -> 1,3 % réel", "statut": "corrige"},
                {"nom": "Vocabulaire sens / terminus", "ampleur": "32 % (6/19 lignes)", "statut": "documente"},
                {"nom": "Complétude des horaires", "ampleur": "7,9 % (3/38 combinaisons)", "statut": "documente"},
                {"nom": "Cohérence codes bus / périodes", "ampleur": "0 % d'anomalie (127 groupes)", "statut": "sain"},
                {"nom": "Durées de trajet", "ampleur": "5,5 % ambigu (retour dépôt)", "statut": "documente"},
                {"nom": "Coordonnées géographiques", "ampleur": "0 % aberrante (455 arrêts)", "statut": "sain"},
                {"nom": "Correspondances absurdes", "ampleur": "0 % (514 paires)", "statut": "sain"},
            ],
        },
        "tests": {"total": 13, "reussis": 13},
    }
