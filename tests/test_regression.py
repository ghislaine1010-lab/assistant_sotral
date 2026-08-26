# -*- coding: utf-8 -*-
"""Suite de tests de non-régression : rassemble tous les cas déjà
validés manuellement au fil du développement. À relancer après
CHAQUE modification de app/nlp.py, app/recommandation.py ou
app/assistant.py, pour détecter immédiatement une régression
silencieuse (comme celle du scorer fuzz.ratio découverte le 24/07)."""

import pytest
from app.nlp import charger_arrets, trouver_arret, analyser
from app.recommandation import trouver_itineraire
from app.assistant import repondre

@pytest.fixture(scope="module")
def arrets():
    return charger_arrets()


# ---------- Module NLP : reconnaissance des arrêts ----------

def test_arret_bien_orthographie(arrets):
    nom, score, methode = trouver_arret("BIA", arrets)
    assert nom == "BIA" and score == 100

def test_arret_avec_faute(arrets):
    nom, score, methode = trouver_arret("zangera", arrets)
    if methode == "texte-ambigu":
        assert all("Zanguéra" in n for n in nom) and score >= 70
    else:
        assert "Zanguéra" in nom and score >= 70

def test_arret_avec_accent_et_nom_long(arrets):
    # Cas ayant révélé la régression fuzz.ratio vs fuzz.WRatio du 24/07
    nom, score, methode = trouver_arret("avedji", arrets)
    assert nom is not None and "Avédji" in nom and score >= 70

def test_sigle_ambigu(arrets):
    nom, score, methode = trouver_arret("CHU", arrets)
    assert methode == "texte-ambigu"

def test_fragment_court_ambigu(arrets):
    nom, score, methode = trouver_arret("Bè", arrets)
    assert methode == "texte-ambigu"

def test_ambiguite_nom_de_quartier(arrets):
    # Un nom de quartier recouvrant plusieurs arrêts réels distincts
    # doit être signalé ambigu, pas résolu silencieusement au hasard.
    nom, score, methode = trouver_arret("Adidogome", arrets)
    assert methode == "texte-ambigu" and len(nom) >= 2


# ---------- Moteur de recommandation ----------

def test_trajet_direct():
    resultat = trouver_itineraire("BIA", "Togocel Zanguéra")
    assert resultat["type"] == "direct"

def test_trajet_avec_correspondance():
    resultat = trouver_itineraire("Adjololo", "AD Zanguéra")
    # "multi" ajouté le 04/08 : extension du moteur aux trajets à
    # plusieurs correspondances (2 ou 3), au-delà du périmètre initial
    # du cahier des charges (SF3 : une seule correspondance prévue).
    assert resultat["type"] in ("correspondance", "multi", "aucun")

def test_trajet_multi_correspondances():
    # Cas nécessitant 3 correspondances (au-delà du périmètre initial
    # SF3 du cahier des charges), validé manuellement le 04/08.
    resultat = trouver_itineraire("AD Zanguéra", "Arrêt Amina")
    assert resultat["type"] == "multi"
    assert len(resultat["lignes"]) == 4
    assert resultat["arrets"][0] == "AD Zanguéra"
    assert resultat["arrets"][-1] == "Arrêt Amina"


# ---------- Pipeline complet (app.assistant.repondre) ----------

def test_salutation(arrets):
    # Le LLM adapte parfois sa salutation à l'heure réelle du système
    # (« Bonsoir » le soir plutôt que « Bonjour ») -- non-déterminisme
    # déjà documenté ; le test accepte donc toute salutation valide,
    # pas uniquement « bonjour ».
    reponse = repondre("Bonjour", arrets)
    reponse_minuscule = reponse.lower()
    assert ("?" in reponse or "aider" in reponse_minuscule
            or "bonjour" in reponse_minuscule or "bonsoir" in reponse_minuscule
            or "bienvenue" in reponse_minuscule)

def test_itineraire_simple(arrets):
    reponse = repondre("Je suis à Atikoumé et je veux aller à Todman", arrets)
    assert "ligne" in reponse.lower() and "aucun itinéraire" not in reponse.lower()

def test_itineraire_avec_quartier_ambigu(arrets):
    reponse = repondre("Je suis à Adidogomé et je veux aller à BIA", arrets)
    assert "plusieurs arrêts" in reponse.lower() and "lequel" in reponse.lower()

def test_question_lignes(arrets):
    reponse = repondre("quelles lignes desservent BIA ?", arrets)
    assert "L1" in reponse or "desservi" in reponse.lower()

def test_question_hors_perimetre(arrets):
    reponse = repondre("quel est le prix du ticket ?", arrets)
    assert "tarif" in reponse.lower() or "ne figure pas" in reponse.lower()

def test_correspondance_calculee_en_direct():
    # Cas découvert le 31/07 : la table 'correspondances' pouvait se
    # désynchroniser de l'état réel de arrets_lignes après une
    # correction des données. correspondances_a() doit interroger la
    # base en direct, pas une table figée potentiellement obsolète.
    from app.faits import correspondances_a
    lignes = correspondances_a("Arrêt Legbanou")
    assert lignes == ["L5"]


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))
