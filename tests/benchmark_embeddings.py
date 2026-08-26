# -*- coding: utf-8 -*-
"""Benchmark du modèle d'embeddings, sur les VRAIES données SOTRAL.
   Correction du 18/08 : la requête SQL utilise désormais une
   sous-requête (comme app/nlp.py::_chercher_par_sens) pour trier par
   distance sur L'ENSEMBLE des arrêts, pas seulement un échantillon
   alphabétique tronqué -- bug détecté dans la première version."""

import time
from pgvector.psycopg2 import register_vector
from app.config import connexion

CAS_TEST = [
    ("Zanguéra", "AD Zanguéra"),
    ("terminus campus", "Terminus Campus Nord"),
    ("BIA", "BIA"),
    ("Adidogomé", "EPP Adidogomé"),
    ("marché", "Marché Bè"),
    ("hôpital", "Arrêt CHU Campus"),
    ("université", "Terminus Campus Sud"),
    ("Bè", "Marché Bè"),
    ("gare", "Gare Ferroviaire Centrale du Togo"),
    ("aéroport", "Tokoin-Aéroport"),
]


def evaluer_qualite(cur, modele):
    reussites_top5, rangs_reciproques = 0, []
    for requete, attendu in CAS_TEST:
        vecteur = modele.encode(requete).tolist()
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
        noms_top5 = [r[0] for r in resultats]

        if attendu in noms_top5:
            reussites_top5 += 1
            rang = noms_top5.index(attendu) + 1
            rangs_reciproques.append(1 / rang)
        else:
            rangs_reciproques.append(0)

        print(f"  {requete!r:20s} -> attendu {attendu!r:32s} | top5={noms_top5}")

    hit_rate_5 = reussites_top5 / len(CAS_TEST) * 100
    mrr = sum(rangs_reciproques) / len(rangs_reciproques)
    return hit_rate_5, mrr


def evaluer_vitesse(modele, n_essais=20):
    debut = time.perf_counter()
    for _ in range(n_essais):
        modele.encode("je suis à Bè et je veux aller à Adidogomé")
    return (time.perf_counter() - debut) / n_essais * 1000


def evaluer_memoire(modele):
    taille_octets = sum(p.numel() * p.element_size() for p in modele._modules['0'].auto_model.parameters())
    return taille_octets / (1024 * 1024)


if __name__ == "__main__":
    from sentence_transformers import SentenceTransformer
    print("Chargement du modèle...")
    modele = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

    conn = connexion(); register_vector(conn); cur = conn.cursor()

    print("\n===== 1. QUALITÉ DE RETRIEVAL (corrigée, sur mes propres arrêts) =====")
    hit_rate_5, mrr = evaluer_qualite(cur, modele)
    print(f"\n  Hit Rate@5 : {hit_rate_5:.0f}%")
    print(f"  MRR : {mrr:.3f}")

    print("\n===== 2. VITESSE D'INFÉRENCE =====")
    latence_ms = evaluer_vitesse(modele)
    print(f"  Latence moyenne : {latence_ms:.1f} ms/requête")

    print("\n===== 3. EMPREINTE MÉMOIRE =====")
    memoire_mo = evaluer_memoire(modele)
    print(f"  Taille du modèle : {memoire_mo:.0f} Mo")

    cur.close(); conn.close()

    print("\n" + "=" * 55)
    print("RÉSUMÉ (comparable au benchmark externe MiniLM-L12-Multi)")
    print("=" * 55)
    print(f"  Hit Rate@5 : {hit_rate_5:.0f}%  (benchmark externe du même modèle : 90%)")
    print(f"  MRR        : {mrr:.3f}  (benchmark externe : 0.733)")
    print(f"  Latence    : {latence_ms:.1f} ms/requête")
    print(f"  Mémoire    : {memoire_mo:.0f} Mo")
