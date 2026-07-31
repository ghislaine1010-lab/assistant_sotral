# -*- coding: utf-8 -*-
"""Jeu de test chiffré (v3, 24/07). Le pipeline intégrant un LLM non
   déterministe, chaque cas d'itinéraire est répété plusieurs fois
   pour mesurer un taux de réussite statistique plutôt qu'un simple
   succès/échec ponctuel."""

import time
from app.nlp import charger_arrets, analyser
from app.assistant import repondre

arrets = charger_arrets()
NB_ESSAIS = 3  # répétitions par phrase, pour lisser la variabilité du LLM

CAS_COMPREHENSION = [
    ("Je suis à Adidogomé et je veux aller à BIA", "AMBIGU", "BIA"),
    ("je pars de zangera pour le CHU", "AMBIGU", "AMBIGU"),
    ("comment aller a todman depuis atikoume ?", "Atikoumé", "Todman"),
    ("Je souhaite me rendre à la douane adidogome", None, "Adidogomé"),
    ("je suis a avedji et je veux aller a adidogome", "Avédji", "AMBIGU"),
    ("je pars de Bè pour BIA", "AMBIGU", "BIA"),
    ("depuis Zanguéra jusqu'à BIA", "AMBIGU", "BIA"),
    ("je veux aller à Adjololo en partant de Djagble", "AUCUN", "Adjololo"),
]

# Cas non ambigus uniquement (l'ambiguïté Adidogomé/Zanguéra est
# retirée : elle constitue un succès SF8, pas un test d'itinéraire).
CAS_ITINERAIRE = [
    "comment aller a todman depuis atikoume ?",
    "je suis à Atikoumé et je veux aller à Todman",
    "je suis à avedji et je veux aller à BIA",
]

CAS_DIVERS = [
    "Bonjour", "merci, au revoir", "quelles lignes desservent BIA ?",
    "quelles correspondances à BIA ?", "combien de lignes avez-vous au total ?",
    "quel est le prix du ticket ?", "est-ce que les bus roulent le dimanche ?",
]


def _verifier_champ(obtenu, methode, attendu):
    if attendu is None:
        return True
    if attendu == "AMBIGU":
        return methode == "texte-ambigu"
    if attendu == "AUCUN":
        return obtenu is None and methode == "aucun"
    return bool(obtenu) and not isinstance(obtenu, list) and attendu in obtenu


def evaluer_comprehension():
    print("\n===== 1. TAUX DE COMPRÉHENSION (SF1, SF2, SF8) — déterministe, 1 essai =====")
    reussites = 0
    for phrase, dep_attendu, dest_attendu in CAS_COMPREHENSION:
        r = analyser(phrase, arrets)
        succes = (_verifier_champ(r["depart"], r["methode_depart"], dep_attendu) and
                   _verifier_champ(r["destination"], r["methode_destination"], dest_attendu))
        reussites += int(succes)
        print(f"  [{'OK' if succes else 'ÉCHEC'}] {phrase}")
    taux = reussites / len(CAS_COMPREHENSION) * 100
    print(f"\n  Taux de compréhension : {reussites}/{len(CAS_COMPREHENSION)} = {taux:.1f}%")
    return taux


def evaluer_itineraires():
    print(f"\n===== 2. PERTINENCE DES ITINÉRAIRES (SF3) — {NB_ESSAIS} essais/phrase (LLM non déterministe) =====")
    reussites_totales, essais_totaux, temps = 0, 0, []
    for phrase in CAS_ITINERAIRE:
        reussites_phrase = 0
        for essai in range(NB_ESSAIS):
            debut = time.perf_counter()
            reponse = repondre(phrase, arrets)
            duree = time.perf_counter() - debut
            temps.append(duree)
            succes = "ligne" in reponse.lower() and "aucun itinéraire" not in reponse.lower()
            reussites_phrase += int(succes)
            essais_totaux += 1
            if not succes:
                print(f"    -> essai {essai+1} en échec : {reponse[:100]}")
        reussites_totales += reussites_phrase
        print(f"  {phrase} : {reussites_phrase}/{NB_ESSAIS} essais réussis")
    taux = reussites_totales / essais_totaux * 100
    temps_hors_premier = temps[1:]  # exclut le tout 1er appel (démarrage à froid)
    temps_moyen = sum(temps_hors_premier) / len(temps_hors_premier)
    print(f"\n  Taux de réussite global : {reussites_totales}/{essais_totaux} = {taux:.1f}%")
    print(f"  Temps de réponse moyen (hors 1er appel à froid) : {temps_moyen:.2f} s")
    return taux, temps_moyen


def evaluer_divers():
    print("\n===== 3. QUESTIONS DIVERSES =====")
    temps = []
    for phrase in CAS_DIVERS:
        debut = time.perf_counter()
        reponse = repondre(phrase, arrets)
        temps.append(time.perf_counter() - debut)
        print(f"  ({temps[-1]:.2f}s) {phrase} -> {reponse[:80]}...")
    temps_moyen = sum(temps[1:]) / len(temps[1:])
    print(f"\n  Temps de réponse moyen (hors 1er appel) : {temps_moyen:.2f} s")
    return temps_moyen


if __name__ == "__main__":
    tc = evaluer_comprehension()
    ti, tpsi = evaluer_itineraires()
    tpsd = evaluer_divers()
    print("\n" + "=" * 55)
    print("BILAN GLOBAL (à reporter dans le chapitre Résultats)")
    print("=" * 55)
    print(f"  Compréhension (dont ambiguïtés bien signalées) : {tc:.1f}%  (cible ≥ 90 %)")
    print(f"  Itinéraires corrects (moyenne sur {NB_ESSAIS} essais/phrase) : {ti:.1f}%  (cible ≥ 95 %)")
    print(f"  Temps de réponse moyen : {tpsi:.2f} s (itinéraires) / {tpsd:.2f} s (divers)  (cible < 3 s)")
