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
    """Calcul EN DIRECT (pas via la table 'correspondances', qui peut se
    désynchroniser de arrets_lignes après une correction des données --
    cas découvert le 31/07 : 8 paires sur 79 étaient devenues obsolètes).
    Toutes les lignes desservant cet arrêt, ou tout arrêt du même nom
    (doublons OSM), sont considérées comme des correspondances possibles."""
    conn = connexion(); cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT l.ref
        FROM arrets_lignes al
        JOIN arrets a ON a.id = al.arret_id
        JOIN lignes l ON l.id = al.ligne_id
        WHERE a.nom = %s
        ORDER BY l.ref;
    """, (nom_arret,))
    lignes = [r[0] for r in cur.fetchall()]
    cur.close(); conn.close()
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
       et le résumé du dernier audit de qualité des données pour
       l'affichage du tableau de bord (graphiques inclus)."""
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

    dimensions = [
        {"nom": "Géométrie des lignes (aller/retour)", "ampleur": "71 % (12/17 lignes)", "valeur": 71, "statut": "corrige"},
        {"nom": "Connectivité des arrêts", "ampleur": "23,5 % apparent -> 1,3 % réel", "valeur": 23.5, "statut": "corrige"},
        {"nom": "Vocabulaire sens / terminus", "ampleur": "32 % (6/19 lignes)", "valeur": 32, "statut": "documente"},
        {"nom": "Complétude des horaires", "ampleur": "7,9 % (3/38 combinaisons)", "valeur": 7.9, "statut": "documente"},
        {"nom": "Cohérence codes bus / périodes", "ampleur": "0 % d'anomalie (127 groupes)", "valeur": 0, "statut": "sain"},
        {"nom": "Durées de trajet", "ampleur": "5,5 % ambigu (retour dépôt)", "valeur": 5.5, "statut": "documente"},
        {"nom": "Coordonnées géographiques", "ampleur": "0 % aberrante (455 arrêts)", "valeur": 0, "statut": "sain"},
        {"nom": "Correspondances absurdes", "ampleur": "0 % (514 paires)", "valeur": 0, "statut": "sain"},
        {"nom": "Correspondances désynchronisées (table figée)", "ampleur": "8 paires sur 79 (10 %)", "valeur": 10.1, "statut": "corrige"},
    ]

    return {
        "reseau": {
            "lignes": nb_lignes, "references_lignes": nb_refs,
            "arrets": nb_arrets, "horaires": nb_horaires,
            "correspondances": nb_correspondances,
        },
        "audit_qualite": {"date": "31/07/2026", "dimensions": dimensions},
        "tests": {"total": 14, "reussis": 14},
    }

def arrets_proches(latitude, longitude, limite=5):
    """Renvoie les N arrêts les plus proches d'une position GPS, avec
       leur distance approximative en mètres. Même principe que
       arret_le_plus_proche(), mais renvoie plusieurs résultats.
       Sous-requête pour dédoublonner par nom AVANT de trier par
       distance (évite le bug DISTINCT ON + LIMIT découvert le 24/07)."""
    conn = connexion(); cur = conn.cursor()
    cur.execute("""
        SELECT nom, distance_m FROM (
            SELECT DISTINCT ON (nom) nom,
                   SQRT(POWER(latitude - %s, 2) + POWER(longitude - %s, 2)) * 111320 AS distance_m
            FROM arrets
            WHERE latitude IS NOT NULL AND longitude IS NOT NULL
            ORDER BY nom, distance_m ASC
        ) sous_requete
        ORDER BY distance_m ASC
        LIMIT %s;
    """, (latitude, longitude, limite))
    resultats = [(nom, round(dist)) for nom, dist in cur.fetchall()]
    cur.close(); conn.close()
    return resultats

def arrets_proches(latitude, longitude, limite=5):
    """Renvoie les N arrêts les plus proches d'une position GPS, avec
       leur distance approximative en mètres. Même principe que
       arret_le_plus_proche(), mais renvoie plusieurs résultats.
       Sous-requête pour dédoublonner par nom AVANT de trier par
       distance (évite le bug DISTINCT ON + LIMIT découvert le 24/07)."""
    conn = connexion(); cur = conn.cursor()
    cur.execute("""
        SELECT nom, distance_m FROM (
            SELECT DISTINCT ON (nom) nom,
                   SQRT(POWER(latitude - %s, 2) + POWER(longitude - %s, 2)) * 111320 AS distance_m
            FROM arrets
            WHERE latitude IS NOT NULL AND longitude IS NOT NULL
            ORDER BY nom, distance_m ASC
        ) sous_requete
        ORDER BY distance_m ASC
        LIMIT %s;
    """, (latitude, longitude, limite))
    resultats = [(nom, round(dist)) for nom, dist in cur.fetchall()]
    cur.close(); conn.close()
    return resultats

def creer_conversation(email):
    """Crée une nouvelle conversation vide pour un utilisateur et
    renvoie son identifiant."""
    conn = connexion(); cur = conn.cursor()
    cur.execute("""
        INSERT INTO conversations (utilisateur_email, titre)
        VALUES (%s, 'Nouvelle conversation') RETURNING id;
    """, (email,))
    id_conversation = cur.fetchone()[0]
    conn.commit()
    cur.close(); conn.close()
    return id_conversation


def lister_conversations(email, limite=50):
    """Renvoie les conversations d'un utilisateur, les plus récentes
    en premier (comme une liste de discussions type ChatGPT/Claude)."""
    if not email:
        return []
    conn = connexion(); cur = conn.cursor()
    cur.execute("""
        SELECT id, titre, cree_le FROM conversations
        WHERE utilisateur_email = %s
        ORDER BY cree_le DESC
        LIMIT %s;
    """, (email, limite))
    resultats = [{"id": i, "titre": t, "cree_le": str(d)} for i, t, d in cur.fetchall()]
    cur.close(); conn.close()
    return resultats


def enregistrer_message(email, conversation_id, role, contenu):
    """Enregistre un message dans une conversation précise, et donne
    automatiquement un titre à la conversation lors du tout premier
    message de l'usager (comme sur ChatGPT/Claude)."""
    if not email or not conversation_id:
        return
    conn = connexion(); cur = conn.cursor()
    cur.execute("""
        INSERT INTO messages (utilisateur_email, conversation_id, role, contenu)
        VALUES (%s, %s, %s, %s);
    """, (email, conversation_id, role, contenu))

    if role == "usager":
        cur.execute("SELECT titre FROM conversations WHERE id = %s;", (conversation_id,))
        titre_actuel = cur.fetchone()
        if titre_actuel and titre_actuel[0] == "Nouvelle conversation":
            nouveau_titre = contenu[:45] + ("…" if len(contenu) > 45 else "")
            cur.execute("UPDATE conversations SET titre = %s WHERE id = %s;", (nouveau_titre, conversation_id))
    conn.commit()
    cur.close(); conn.close()


def messages_de_conversation(email, conversation_id, limite=200):
    """Renvoie les messages d'UNE conversation précise, en vérifiant
    qu'elle appartient bien à l'utilisateur demandeur."""
    if not email or not conversation_id:
        return []
    conn = connexion(); cur = conn.cursor()
    cur.execute("""
        SELECT m.role, m.contenu FROM messages m
        JOIN conversations c ON c.id = m.conversation_id
        WHERE m.conversation_id = %s AND c.utilisateur_email = %s
        ORDER BY m.cree_le ASC
        LIMIT %s;
    """, (conversation_id, email, limite))
    resultats = [{"role": r, "contenu": c} for r, c in cur.fetchall()]
    cur.close(); conn.close()
    return resultats

import requests
import time

_dernier_appel_geocodage = 0

def geocoder_lieu(nom_lieu):
    """Cherche la position géographique (latitude, longitude) d'un
    lieu qui n'est PAS un arrêt connu de notre base, via OpenStreetMap
    Nominatim (service externe gratuit, limité à Lomé/Togo). Respecte
    la règle d'usage Nominatim (max 1 requête/seconde). Renvoie None
    si rien n'est trouvé."""
    global _dernier_appel_geocodage
    attente = 1.0 - (time.time() - _dernier_appel_geocodage)
    if attente > 0:
        time.sleep(attente)
    _dernier_appel_geocodage = time.time()

    try:
        reponse = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={
                "q": f"{nom_lieu}, Lomé, Togo",
                "format": "json",
                "limit": 1,
                "viewbox": "1.05,6.35,1.40,6.05",  # zone Lomé élargie
                "bounded": 1,
            },
            headers={"User-Agent": "AssistantSOTRAL-MemoireIABD/1.0"},
            timeout=5,
        )
        resultats = reponse.json()
        if resultats:
            return float(resultats[0]["lat"]), float(resultats[0]["lon"])
    except Exception as e:
        print(f"(géocodage indisponible : {e})")
    return None

def infos_profil(email):
    """Rassemble les informations du compte pour la page « Mon
    profil » : date de création, nombre de conversations, nombre
    total de messages échangés, nombre de trajets récents en mémoire."""
    if not email:
        return None
    conn = connexion(); cur = conn.cursor()

    cur.execute("SELECT cree_le FROM utilisateurs WHERE email = %s;", (email,))
    ligne = cur.fetchone()
    if not ligne:
        cur.close(); conn.close()
        return None
    cree_le = ligne[0]

    cur.execute("SELECT COUNT(*) FROM conversations WHERE utilisateur_email = %s;", (email,))
    nb_conversations = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM messages WHERE utilisateur_email = %s;", (email,))
    nb_messages = cur.fetchone()[0]

    cur.close(); conn.close()
    return {
        "email": email,
        "cree_le": str(cree_le),
        "nb_conversations": nb_conversations,
        "nb_messages": nb_messages,
    }

def ajouter_trajet_recent_bdd(email, depart, destination, limite=4):
    """Enregistre un trajet réussi en base (persistant, contrairement
    à l'ancienne version en mémoire du serveur), sans doublon, et ne
    conserve que les 'limite' plus récents par utilisateur."""
    if not email:
        return
    conn = connexion(); cur = conn.cursor()
    cur.execute("""
        DELETE FROM trajets_recents
        WHERE utilisateur_email = %s AND depart = %s AND destination = %s;
    """, (email, depart, destination))
    cur.execute("""
        INSERT INTO trajets_recents (utilisateur_email, depart, destination)
        VALUES (%s, %s, %s);
    """, (email, depart, destination))
    cur.execute("""
        DELETE FROM trajets_recents WHERE id IN (
            SELECT id FROM trajets_recents
            WHERE utilisateur_email = %s
            ORDER BY cree_le DESC
            OFFSET %s
        );
    """, (email, limite))
    conn.commit()
    cur.close(); conn.close()


def trajets_recents_bdd(email, limite=4):
    """Renvoie les derniers trajets réussis d'un utilisateur, du plus
    récent au plus ancien (persistant en base)."""
    if not email:
        return []
    conn = connexion(); cur = conn.cursor()
    cur.execute("""
        SELECT depart, destination FROM trajets_recents
        WHERE utilisateur_email = %s
        ORDER BY cree_le DESC
        LIMIT %s;
    """, (email, limite))
    resultats = [{"depart": d, "destination": a} for d, a in cur.fetchall()]
    cur.close(); conn.close()
    return resultats

def toutes_les_lignes_avec_trajet():
    """Renvoie chaque ligne du réseau avec son trajet résumé (les
    directions connues, ex. 'BIA <-> Togocel Zanguéra'), pour répondre
    à une demande globale du type 'quelles sont toutes les lignes'."""
    conn = connexion(); cur = conn.cursor()
    cur.execute("SELECT DISTINCT ref, nom FROM lignes ORDER BY ref, nom;")
    lignes_brutes = cur.fetchall()
    cur.close(); conn.close()

    par_ref = {}
    for ref, nom in lignes_brutes:
        par_ref.setdefault(ref, []).append(nom)

    resultats = []
    for ref in sorted(par_ref.keys(), key=lambda r: (len(r), r)):
        directions = par_ref[ref]
        trajet = " <-> ".join(directions[:2]) if len(directions) >= 2 else directions[0]
        resultats.append((ref, trajet))
    return resultats


def informations_ligne(ref_demande):
    """Renvoie le trajet résumé d'UNE ligne précise (ex. 'L1'), ou
    None si cette référence de ligne n'existe pas."""
    conn = connexion(); cur = conn.cursor()
    cur.execute("SELECT DISTINCT nom FROM lignes WHERE ref = %s ORDER BY nom;", (ref_demande,))
    directions = [r[0] for r in cur.fetchall()]
    cur.close(); conn.close()

    if not directions:
        return None
    return " <-> ".join(directions[:2]) if len(directions) >= 2 else directions[0]

def chercher_synonyme(terme):
    """Vérifie si le terme employé par l'usager est un surnom/synonyme
    local connu (ex. « Grand Marché » pour « BIA »), enregistré dans
    la table synonymes_arrets. Recherche insensible à la casse et aux
    accents. Renvoie le vrai nom d'arrêt si trouvé, sinon None."""
    if not terme:
        return None
    conn = connexion(); cur = conn.cursor()
    cur.execute("""
        SELECT arret_reel FROM synonymes_arrets
        WHERE unaccent(lower(synonyme)) = unaccent(lower(%s))
        LIMIT 1;
    """, (terme,))
    resultat = cur.fetchone()
    cur.close(); conn.close()
    return resultat[0] if resultat else None
