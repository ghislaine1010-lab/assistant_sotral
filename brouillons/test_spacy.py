# -*- coding: utf-8 -*-
"""Test exploratoire : que fait spaCy sur nos phrases, comparé à notre approche ?"""

import spacy

nlp = spacy.load("fr_core_news_sm")

phrases_test = [
    "Je suis à Adidogomé et je veux aller à BIA",
    "je pars de zangera pour le CHU",
    "comment aller a todman depuis atikoume ?",
    "Je souhaite me rendre à la douane adidogome",
]

for phrase in phrases_test:
    print(f"\n{'='*60}")
    print(f"Phrase : {phrase}")
    doc = nlp(phrase)

    print("\n-- Étiquetage grammatical (POS tagging) --")
    for token in doc:
        print(f"  {token.text:15s} -> {token.pos_:10s} (dépend de : {token.head.text})")

    print("\n-- Entités nommées détectées (NER) --")
    if doc.ents:
        for ent in doc.ents:
            print(f"  « {ent.text} »  ->  type : {ent.label_}")
    else:
        print("  (aucune entité détectée)")
