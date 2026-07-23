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
