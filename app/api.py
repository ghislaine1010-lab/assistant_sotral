# -*- coding: utf-8 -*-
"""API web de l'assistant SOTRAL, avec authentification par email et
   conversations multiples (12/08, comme sur ChatGPT/Claude) : chaque
   utilisateur peut avoir plusieurs discussions distinctes, listées
   dans une barre latérale, avec un bouton pour en démarrer une nouvelle."""

import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse, JSONResponse
from starlette.middleware.sessions import SessionMiddleware
from pydantic import BaseModel
from typing import Optional, List
from dotenv import load_dotenv

from app.assistant import repondre, dernier_itineraire_carte
from app.nlp import charger_arrets
from app.faits import (tableau_de_bord, enregistrer_message,
                        creer_conversation, lister_conversations, messages_de_conversation, infos_profil)
from app.auth import inscrire, confirmer, connecter

load_dotenv()

app = FastAPI(title="Assistant SOTRAL", version="0.3.0")

app.add_middleware(SessionMiddleware, secret_key=os.getenv("SESSION_SECRET", "cle-de-secours-a-changer"))
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

app.mount("/statique", StaticFiles(directory="static"), name="statique")

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

class Identifiants(BaseModel):
    email: str
    mot_de_passe: str

class Confirmation(BaseModel):
    email: str
    code: str


@app.get("/login")
def page_login():
    return FileResponse("static/login.html")

@app.get("/inscription")
def page_inscription():
    return FileResponse("static/inscription.html")

@app.get("/deconnexion")
def deconnexion(request: Request):
    request.session.clear()
    return RedirectResponse("/login")


@app.post("/auth/inscrire")
def api_inscrire(identifiants: Identifiants):
    succes, message = inscrire(identifiants.email, identifiants.mot_de_passe)
    return JSONResponse({"succes": succes, "message": message})

@app.post("/auth/confirmer")
def api_confirmer(donnees: Confirmation):
    succes, message = confirmer(donnees.email, donnees.code)
    return JSONResponse({"succes": succes, "message": message})

@app.post("/auth/connexion")
def api_connexion(identifiants: Identifiants, request: Request):
    succes, message = connecter(identifiants.email, identifiants.mot_de_passe)
    if succes:
        request.session["email"] = identifiants.email
    return JSONResponse({"succes": succes, "message": message})


@app.get("/app")
def page_application(request: Request):
    if not request.session.get("email"):
        return RedirectResponse("/login")
    return FileResponse("static/chat_prive.html")

@app.get("/")
def racine_redirection(request: Request):
    if request.session.get("email"):
        return RedirectResponse("/app")
    return RedirectResponse("/login")


# ---------- Conversations multiples (12/08) ----------
@app.get("/conversations")
def api_lister_conversations(request: Request):
    utilisateur = request.session.get("email")
    return lister_conversations(utilisateur)

@app.post("/conversations/nouvelle")
def api_nouvelle_conversation(request: Request):
    utilisateur = request.session.get("email")
    id_conversation = creer_conversation(utilisateur)
    request.session["conversation_id"] = id_conversation
    return {"id": id_conversation}

@app.get("/conversations/{id_conversation}")
def api_ouvrir_conversation(id_conversation: int, request: Request):
    utilisateur = request.session.get("email")
    request.session["conversation_id"] = id_conversation
    return messages_de_conversation(utilisateur, id_conversation)


@app.post("/message", response_model=Reponse)
def envoyer_message(requete: Requete, request: Request):
    position = None
    if requete.latitude is not None and requete.longitude is not None:
        position = (requete.latitude, requete.longitude)
    utilisateur = request.session.get("email")

    conversation_id = request.session.get("conversation_id")
    if not conversation_id:
        conversation_id = creer_conversation(utilisateur)
        request.session["conversation_id"] = conversation_id

    enregistrer_message(utilisateur, conversation_id, "usager", requete.message)
    texte_reponse = repondre(requete.message, _arrets_cache, position=position, utilisateur=utilisateur)
    enregistrer_message(utilisateur, conversation_id, "assistant", texte_reponse)
    return Reponse(reponse=texte_reponse)


@app.get("/trajet", response_model=List[PointCarte])
def trajet_carte(request: Request):
    utilisateur = request.session.get("email")
    points = dernier_itineraire_carte(utilisateur)
    return [PointCarte(**p) for p in points]

@app.get("/profil")
def page_profil(request: Request):
    if not request.session.get("email"):
        return RedirectResponse("/login")
    return FileResponse("static/profil.html")

@app.get("/profil-donnees")
def profil_donnees(request: Request):
    utilisateur = request.session.get("email")
    donnees = infos_profil(utilisateur)
    if not donnees:
        return RedirectResponse("/login")
    return donnees


@app.get("/dashboard")
def dashboard_data():
    return tableau_de_bord()

@app.get("/dashboard-html")
def page_dashboard():
    return FileResponse("static/dashboard.html")
