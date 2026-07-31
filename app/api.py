# -*- coding: utf-8 -*-
"""API web de l'assistant SOTRAL, construite avec FastAPI."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List

from app.assistant import repondre, dernier_itineraire_carte
from app.nlp import charger_arrets
from app.faits import tableau_de_bord

app = FastAPI(
    title="Assistant SOTRAL",
    description="Assistant intelligent de recommandation d'itinéraires — réseau SOTRAL, Lomé",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/ui", StaticFiles(directory="static", html=True), name="static")

_arrets_cache = None

@app.on_event("startup")
def charger_donnees():
    global _arrets_cache
    _arrets_cache = charger_arrets()
    print(f"API démarrée : {len(_arrets_cache)} arrêts chargés.")


class Requete(BaseModel):
    message: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class Reponse(BaseModel):
    reponse: str


class PointCarte(BaseModel):
    nom: str
    latitude: Optional[float]
    longitude: Optional[float]


@app.get("/")
def racine():
    return {"statut": "en ligne", "service": "Assistant SOTRAL", "arrets_charges": len(_arrets_cache or [])}


@app.post("/message", response_model=Reponse)
def envoyer_message(requete: Requete):
    position = None
    if requete.latitude is not None and requete.longitude is not None:
        position = (requete.latitude, requete.longitude)
    texte_reponse = repondre(requete.message, _arrets_cache, position=position)
    return Reponse(reponse=texte_reponse)


@app.get("/trajet", response_model=List[PointCarte])
def trajet_carte():
    points = dernier_itineraire_carte()
    return [PointCarte(**p) for p in points]


@app.get("/dashboard")
def dashboard_data():
    """Statistiques du réseau et bilan du dernier audit de qualité des données."""
    return tableau_de_bord()
