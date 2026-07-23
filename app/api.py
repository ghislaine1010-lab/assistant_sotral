# -*- coding: utf-8 -*-
"""API web de l'assistant SOTRAL, construite avec FastAPI.
   Expose le pipeline complet (app.assistant.repondre) sous forme
   d'un service HTTP consultable par n'importe quelle interface."""

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from app.assistant import repondre
from app.nlp import charger_arrets

app = FastAPI(
    title="Assistant SOTRAL",
    description="Assistant intelligent de recommandation d'itinéraires — réseau SOTRAL, Lomé",
    version="0.1.0",
)
from fastapi.staticfiles import StaticFiles
app.mount("/ui", StaticFiles(directory="static", html=True), name="static")

# Autorise les appels depuis une page web (nécessaire pour une future interface front-end)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Les arrêts sont chargés une seule fois au démarrage du serveur, pas à chaque requête
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


@app.get("/")
def racine():
    return {"statut": "en ligne", "service": "Assistant SOTRAL", "arrets_charges": len(_arrets_cache or [])}


@app.get("/favicon.ico")
def favicon():
    return Response(status_code=204)


@app.post("/message", response_model=Reponse)
def envoyer_message(requete: Requete):
    """Point d'entrée principal : reçoit un message utilisateur (et,
       optionnellement, sa position GPS) et renvoie la réponse de l'assistant."""
    position = None
    if requete.latitude is not None and requete.longitude is not None:
        position = (requete.latitude, requete.longitude)

    texte_reponse = repondre(requete.message, _arrets_cache, position=position)
    return Reponse(reponse=texte_reponse)
