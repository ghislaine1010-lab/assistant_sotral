# -*- coding: utf-8 -*-
"""Le LLM classe-t-il souvent 'je suis a Bè et je veux aller a BIA'
   comme une salutation au lieu d'un itinéraire ? Test répété."""

from app.llm import interpreter_message

phrases = [
    "je suis a be et je veux aller a bia",
    "je suis a Bè et je veux aller à BIA",
    "je suis be et je veux aller a bia comment faire",
]

for phrase in phrases:
    print(f"\nPhrase : « {phrase} »")
    for i in range(4):
        r = interpreter_message(phrase)
        print(f"  Essai {i+1} : intention={r.get('intention')!r}, depart={r.get('depart')!r}, destination={r.get('destination')!r}")
