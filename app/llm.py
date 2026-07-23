# -*- coding: utf-8 -*-
"""Interface avec le LLM local (Ollama) : classification de l'intention,
   extraction brute du départ/destination, et réponses conversationnelles
   pour tout ce qui n'est pas une demande d'itinéraire.
   IMPORTANT : les lieux extraits ici sont BRUTS (non vérifiés) ; ils
   doivent toujours être confrontés à la vraie base de connaissances
   avant d'être utilisés (architecture RAG — voir app/assistant.py)."""

import ollama
import json

PROMPT_SYSTEME = """Tu es l'assistant conversationnel du réseau de bus SOTRAL à Lomé, au Togo.
Pour chaque message de l'utilisateur, réponds UNIQUEMENT avec un objet JSON, sans aucun texte autour, de cette forme exacte :
{"intention": "...", "depart": "...", "destination": "...", "reponse": "..."}

Règles :
- "intention" vaut "itineraire" si l'utilisateur demande un trajet, une ligne de bus, ou un moyen d'aller d'un lieu à un autre.
- "intention" vaut "salutation" pour les politesses (bonjour, merci, au revoir...).
- "intention" vaut "autre" pour toute autre question (horaires généraux, tarifs, questions sur toi...).
- Si intention = "itineraire" : remplis "depart" et "destination" avec les lieux mentionnés tels quels (null si absent), et mets "reponse" à null.
- Si intention = "salutation" : mets "depart" et "destination" à null, "reponse" = message chaleureux et bref.
- Si intention = "autre" : mets "depart" et "destination" à null, "reponse" = "Je ne dispose pas de cette information pour le moment, je vous invite à contacter directement la SOTRAL."
  (NE JAMAIS inventer une réponse factuelle sur les horaires, tarifs ou jours de service que tu ne connais pas avec certitude.)
"""

def interpreter_message(phrase):
    reponse = ollama.chat(model="llama3.2:3b", messages=[
        {"role": "system", "content": PROMPT_SYSTEME},
        {"role": "user", "content": phrase},
    ])
    texte = reponse["message"]["content"]
    try:
        return json.loads(texte)
    except json.JSONDecodeError:
        return {"intention": "autre", "depart": None, "destination": None,
                "reponse": "Je n'ai pas bien compris votre demande, pouvez-vous reformuler ?"}
