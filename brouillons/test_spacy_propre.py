import spacy
nlp = spacy.load("fr_core_news_sm")

phrases = [
    "Je pars de Zanguéra pour le CHU",
    "Comment aller à Todman depuis Atikoumé ?",
]
for phrase in phrases:
    doc = nlp(phrase)
    print(f"\nPhrase : {phrase}")
    ents = [(e.text, e.label_) for e in doc.ents]
    print("Entités détectées :", ents if ents else "aucune")
