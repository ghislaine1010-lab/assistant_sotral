# -*- coding: utf-8 -*-
"""Module NLP hybride : RapidFuzz en première intention (rapide),
   puis pgvector (recherche sémantique en base) en filet de sécurité.
   Détecte aussi l'ambiguïté quand plusieurs arrêts DISTINCTS (pas de
   simples doublons aller/retour) obtiennent un score de comparaison
   très proche (ex. « Adidogomé » désigne plusieurs arrêts du quartier)."""

import re
import unicodedata
from rapidfuzz import process, fuzz
from app.config import connexion

def charger_arrets():
    conn = connexion()
    curseur = conn.cursor()
    curseur.execute("SELECT DISTINCT nom FROM arrets ORDER BY nom;")
    arrets = [ligne[0] for ligne in curseur.fetchall()]
    curseur.close(); conn.close()
    return arrets

def normaliser(texte):
    texte = unicodedata.normalize("NFD", texte.lower())
    texte = texte.encode("ascii", "ignore").decode()
    return " ".join(texte.split())

MOTS_VIDES = {"le", "la", "les", "l", "du", "de", "des", "un", "une"}
# Mots qui annoncent une NOUVELLE proposition (jamais présents dans un nom
# d'arrêt réel) : leur présence signale que le reste du fragment est du
# bruit à ignorer plutôt que le nom du lieu (bug observé : "be je veux"
# au lieu de "be", extrait entre deux marqueurs trop éloignés).
MOTS_CESURE = {"je", "tu", "il", "elle", "nous", "vous", "ils", "elles",
               "veux", "voudrais", "souhaite", "aimerais", "et", "puis", "ensuite", "donc"}

def nettoyer_fragment(fragment):
    fragment = fragment.strip(" .!?,")
    fragment = re.sub(r"^(l|d|j|qu)'", "", fragment)
    mots = fragment.split()
    while mots and mots[0] in MOTS_VIDES:
        mots.pop(0)
    for i, mot in enumerate(mots):
        if mot in MOTS_CESURE:
            mots = mots[:i]
            break
    return " ".join(mots)

_modele = None
def _get_modele():
    global _modele
    if _modele is None:
        from sentence_transformers import SentenceTransformer
        print("(chargement du modèle sémantique, un instant...)")
        _modele = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    return _modele

def _chercher_par_sens(texte_avec_contexte, seuil_sens=45):
    modele = _get_modele()
    vecteur = modele.encode(texte_avec_contexte).tolist()
    conn = connexion()
    cur = conn.cursor()
    cur.execute("""
        SELECT nom, distance FROM (
            SELECT DISTINCT ON (nom) nom, embedding <=> %s::vector AS distance
            FROM arrets WHERE embedding IS NOT NULL
            ORDER BY nom, distance ASC
        ) sous_requete
        ORDER BY distance ASC
        LIMIT 5;
    """, (vecteur,))
    resultats = cur.fetchall()
    cur.close(); conn.close()
    if not resultats:
        return None, 0
    meilleur_nom, meilleure_distance = resultats[0]
    similarite = (1 - meilleure_distance) * 100
    if similarite >= seuil_sens:
        return meilleur_nom, round(similarite)
    return None, 0

MARGE_AMBIGUITE = 8  # points d'écart max avec le meilleur score pour être "à égalité"

def trouver_arret(fragment, arrets, seuil_texte=70, seuil_sens=45, contexte=None):
    fragment_propre = nettoyer_fragment(fragment or "")
    if not fragment_propre:
        return None, 0, "aucun"

    fragment_norm = normaliser(fragment_propre)
    normalises = {a: normaliser(a).replace("arret ", "") for a in arrets}

    if len(fragment_norm) <= 3:
        correspondances = [a for a, texte_norm in normalises.items()
                            if fragment_norm in texte_norm.split()]
        if len(correspondances) == 1:
            return correspondances[0], 100, "texte"
        elif len(correspondances) > 1:
            return sorted(correspondances), 75, "texte-ambigu"
    else:
        # process.extract() sur un dict renvoie (valeur, score, CLÉ) :
        # la clé (3e élément) est le nom original de l'arrêt.
        resultats = process.extract(fragment_norm, normalises, scorer=fuzz.WRatio, limit=8)
        candidats_valides = [r for r in resultats if r[1] >= seuil_texte]
        if candidats_valides:
            meilleur_score = candidats_valides[0][1]
            proches = [r for r in candidats_valides if r[1] >= meilleur_score - MARGE_AMBIGUITE]
            # Regroupe par texte NORMALISÉ (r[0]) : deux entrées avec le
            # même texte normalisé = même arrêt physique (doublon
            # aller/retour), pas une vraie ambiguïté.
            textes_distincts = {}
            for texte_norm, score, nom_original in proches:
                if texte_norm not in textes_distincts:
                    textes_distincts[texte_norm] = nom_original
            noms_distincts = sorted(textes_distincts.values())
            if len(noms_distincts) > 1:
                return noms_distincts, meilleur_score, "texte-ambigu"
            return candidats_valides[0][2], round(meilleur_score), "texte"

    # Recherche sémantique VOLONTAIREMENT désactivée : sur ce jeu de
    # données, elle produit parfois des faux positifs confiants pour
    # des lieux absents de la base (ex. « Djagblé » -> « Siège SOTRAL »,
    # confirmé le 24/07 lors du jeu de test chiffré). À retravailler
    # (score relatif, seuil par requête, autre modèle) avant réactivation.
    return None, 0, "aucun"

MARQUEURS = [
    ("depart", r"je suis a"), ("depart", r"je pars du"), ("depart", r"je pars de"),
    ("depart", r"en partant de"), ("depart", r"depuis"), ("depart", r"\bde\b"),
    ("destination", r"je veux aller a"), ("destination", r"je souhaite me rendre a"),
    ("destination", r"aller a"), ("destination", r"me rendre a"),
    ("destination", r"jusqu'a"), ("destination", r"jusqu a"),
    ("destination", r"a destination de"), ("destination", r"\bvers\b"), ("destination", r"\bpour\b"),
]

def analyser(phrase, arrets):
    p = normaliser(phrase)
    occurrences = []
    for kind, motif in MARQUEURS:
        for m in re.finditer(motif, p):
            occurrences.append((m.start(), m.end(), kind))
    occurrences.sort(key=lambda x: x[0])
    retenues = []
    for start, end, kind in occurrences:
        if not any(s <= start and end <= e for s, e, k in retenues):
            retenues.append((start, end, kind))
    retenues.sort(key=lambda x: x[0])
    fragments = {"depart": None, "destination": None}
    contextes = {"depart": None, "destination": None}
    for i, (start, end, kind) in enumerate(retenues):
        fin_segment = retenues[i + 1][0] if i + 1 < len(retenues) else len(p)
        fragments[kind] = p[end:fin_segment]
        contextes[kind] = p[start:fin_segment]
    depart, score_d, methode_d = trouver_arret(fragments["depart"], arrets, contexte=contextes["depart"])
    destination, score_a, methode_a = trouver_arret(fragments["destination"], arrets, contexte=contextes["destination"])
    return {"depart": depart, "score_depart": score_d, "methode_depart": methode_d,
            "destination": destination, "score_destination": score_a, "methode_destination": methode_a}
