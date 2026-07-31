# -*- coding: utf-8 -*-
"""Pourquoi 'comment aller a todman depuis atikoume ?' échoue-t-il
   maintenant, alors qu'il réussissait avant ?"""

from app.assistant import repondre
from app.llm import interpreter_message
from app.nlp import charger_arrets

arrets = charger_arrets()

phrase = "comment aller a todman depuis atikoume ?"
print("Ce que le LLM extrait :", interpreter_message(phrase))
print("\nRéponse complète de repondre() :")
print(repondre(phrase, arrets))
