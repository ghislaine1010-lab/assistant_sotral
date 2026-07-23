# -*- coding: utf-8 -*-
"""Module NLP hybride : RapidFuzz en première intention (rapide),
   puis pgvector (recherche sémantique en base) en filet de sécurité."""

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
def nettoyer_fragment(fragment):
    fragment = fragment.strip(" .!?,")
    fragment = re.sub(r"^(l|d|j|qu)'", "", fragment)
    mots = fragment.split()
    while mots and mots[0] in MOTS_VIDES:
        mots.pop(0)
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

def trouver_arret(fragment, arrets, seuil_texte=70, seuil_sens=45, contexte=None):
    """fragment : texte après le marqueur (peut être BRUT, non normalisé,
       par exemple fourni directement par le LLM).
       contexte : texte incluant le marqueur, pour la recherche sémantique."""
    fragment_propre = nettoyer_fragment(fragment or "")
    if not fragment_propre:
        return None, 0, "aucun"

    # Normalisation systématique, quelle que soit la provenance du fragment
    # (corrige le cas où un fragment brut, ex. venant du LLM, garde ses
    # accents/majuscules et échoue silencieusement la comparaison exacte).
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
        resultat = process.extractOne(fragment_norm, normalises, scorer=fuzz.ratio)
        if resultat and resultat[1] >= seuil_texte:
            return resultat[2], round(resultat[1]), "texte"

    # Fallback sémantique désactivé (voir _chercher_par_sens) : sur ce jeu
    # de données, l'effet de "hubness" fait qu'un texte hors-sujet (voire
    # du charabia) score souvent plus haut qu'une vraie requête légitime
    # (ex. "aller à l'université" -> 28% contre 45% pour "xyzabc123").
    # Un seuil ne suffit pas à corriger ça ; à retravailler (score relatif,
    # autre modèle...) avant de le réactiver.
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

if __name__ == "__main__":
    arrets = charger_arrets()
    print(f"{len(arrets)} arrêts chargés depuis la base.\n")
    for phrase in ["Je suis à Adidogomé et je veux aller à BIA", "je pars de zangera pour le CHU"]:
        r = analyser(phrase, arrets)
        print(phrase, "->", r)
