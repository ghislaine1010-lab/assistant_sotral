# -*- coding: utf-8 -*-
"""Suite de tests de non-régression, mise à jour le 24/07 pour refléter
la détection d'ambiguïté au niveau des noms de quartier (ex. Adidogomé,
Zanguéra désignent plusieurs arrêts réels distincts)."""

import pytest
from app.nlp import charger_arrets, trouver_arret, analyser
from app.recommandation import trouver_itineraire
from app.assistant import repondre

@pytest.fixture(scope="module")
def arrets():
    return charger_arrets()


def test_arret_bien_orthographie(arrets):
    nom, score, methode = trouver_arret("BIA", arrets)
    assert nom == "BIA" and score == 100

def test_arret_avec_faute(arrets):
    # "Zanguéra" désigne 2 arrêts réels distincts (AD Zanguéra, Togocel
    # Zanguéra) : le résultat attendu est une ambiguïté, pas un choix
    # arbitraire.
    nom, score, methode = trouver_arret("zangera", arrets)
    if methode == "texte-ambigu":
        assert all("Zanguéra" in n for n in nom) and score >= 70
    else:
        assert "Zanguéra" in nom and score >= 70

def test_arret_avec_accent_et_nom_long(arrets):
    nom, score, methode = trouver_arret("avedji", arrets)
    assert nom is not None and "Avédji" in nom and score >= 70

def test_sigle_ambigu(arrets):
    nom, score, methode = trouver_arret("CHU", arrets)
    assert methode == "texte-ambigu"

def test_fragment_court_ambigu(arrets):
    nom, score, methode = trouver_arret("Bè", arrets)
    assert methode == "texte-ambigu"

def test_ambiguite_nom_de_quartier(arrets):
    # Nouveau test (24/07) : un nom de quartier recouvrant plusieurs
    # arrêts réels distincts doit être signalé ambigu, pas résolu
    # silencieusement au hasard (cause racine de l'échec Adidogomé/
    # Zanguéra découvert lors du jeu de test chiffré).
    nom, score, methode = trouver_arret("Adidogome", arrets)
    assert methode == "texte-ambigu" and len(nom) >= 2


def test_trajet_direct():
    resultat = trouver_itineraire("BIA", "Togocel Zanguéra")
    assert resultat["type"] == "direct"

def test_trajet_avec_correspondance():
    resultat = trouver_itineraire("Adjololo", "AD Zanguéra")
    assert resultat["type"] in ("correspondance", "aucun")


def test_salutation(arrets):
    reponse = repondre("Bonjour", arrets)
    assert "?" in reponse or "bonjour" in reponse.lower() or "aider" in reponse.lower()

def test_itineraire_simple(arrets):
    # Remplacé Adidogomé/BIA (désormais ambigu, à raison) par un couple
    # d'arrêts non ambigus déjà validé (ligne directe L1).
    reponse = repondre("Je suis à Atikoumé et je veux aller à Todman", arrets)
    assert "ligne" in reponse.lower() and "aucun itinéraire" not in reponse.lower()

def test_itineraire_avec_quartier_ambigu(arrets):
    # Le cas Adidogomé doit désormais demander une clarification,
    # jamais deviner silencieusement un arrêt mal connecté.
    reponse = repondre("Je suis à Adidogomé et je veux aller à BIA", arrets)
    assert "plusieurs arrêts" in reponse.lower() and "lequel" in reponse.lower()

def test_question_lignes(arrets):
    reponse = repondre("quelles lignes desservent BIA ?", arrets)
    assert "L1" in reponse or "desservi" in reponse.lower()

def test_question_hors_perimetre(arrets):
    reponse = repondre("quel est le prix du ticket ?", arrets)
    assert "tarif" in reponse.lower() or "ne figure pas" in reponse.lower()


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))
