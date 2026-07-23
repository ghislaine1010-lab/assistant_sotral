# -*- coding: utf-8 -*-
"""Teste Ollama sur trois rôles à la fois :
   1) classer l'intention (salutation / itineraire / autre)
   2) extraire départ et destination si c'est une demande d'itinéraire
   3) rédiger une réponse naturelle si ce n'est PAS une demande d'itinéraire
      (le calcul du VRAI trajet reste toujours fait par notre moteur,
       jamais inventé par le LLM, pour rester fiable)."""

import ollama
import json

PROMPT_SYSTEME = """Tu es l'assistant conversationnel du réseau de bus SOTRAL à Lomé, au Togo.
Pour chaque message de l'utilisateur, réponds UNIQUEMENT avec un objet JSON, sans aucun texte autour, de cette forme exacte :
{"intention": "...", "depart": "...", "destination": "...", "reponse": "..."}

Règles :
- "intention" vaut "itineraire" si l'utilisateur demande un trajet, une ligne de bus, ou un moyen d'aller d'un lieu à un autre.
- "intention" vaut "salutation" pour les politesses (bonjour, merci, au revoir...).
- "intention" vaut "autre" pour toute autre question ou remarque (horaires généraux, tarifs, questions sur toi, etc.).
- Si intention = "itineraire" : remplis "depart" et "destination" avec les lieux mentionnés (null si absent), et mets "reponse" à null (le trajet sera calculé séparément).
- Si intention = "salutation" ou "autre" : mets "depart" et "destination" à null, et écris dans "reponse" une réponse chaleureuse, brève, en français, cohérente avec ton rôle d'assistant SOTRAL.
"""

def analyser_avec_llm(phrase):
    reponse = ollama.chat(model="llama3.2:3b", messages=[
        {"role": "system", "content": PROMPT_SYSTEME},
        {"role": "user", "content": phrase},
    ])
    texte = reponse["message"]["content"]
    try:
        return json.loads(texte)
    except json.JSONDecodeError:
        return {"erreur": "réponse non conforme", "brut": texte}

if __name__ == "__main__":
    phrases_test = [
        "Bonjour, comment vas-tu ?",
        "Je suis à Adidogomé et je veux aller à BIA",
        "comment aller a todman depuis atikoume ?",
        "merci beaucoup, au revoir",
        "est-ce que les bus roulent le dimanche ?",
        "c'est toi qui as créé ce projet ?",
    ]
    for phrase in phrases_test:
        print(f"\nPhrase : {phrase}")
        print("Résultat :", analyser_avec_llm(phrase))
