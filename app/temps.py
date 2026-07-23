# -*- coding: utf-8 -*-
"""Extraction du moment souhaité (heure précise, ou période de la
   journée) à partir d'une phrase, et détermination du jour réel
   (pour savoir si on dispose de données : Lundi-Vendredi ou Samedi)."""

import re
from datetime import date, datetime

def jour_actuel():
    """Renvoie 'Lundi-Vendredi', 'Samedi', ou None si on est dimanche
       (jour non couvert par les données collectées)."""
    wd = date.today().weekday()  # 0 = lundi ... 6 = dimanche
    if wd == 5:
        return "Samedi"
    if wd == 6:
        return None
    return "Lundi-Vendredi"

def extraire_moment(phrase):
    """Renvoie (type, valeur) : ('heure', '14:30'), ('periode', 'MATIN'),
       ou (None, None) si rien n'est précisé."""
    p = phrase.lower()
    m = re.search(r"(\d{1,2})\s*h\s*(\d{2})?", p)
    if m:
        h = int(m.group(1)); mn = int(m.group(2) or 0)
        return "heure", f"{h:02d}:{mn:02d}"
    if "maintenant" in p or "tout de suite" in p:
        return "heure", datetime.now().strftime("%H:%M")
    if "matin" in p:
        return "periode", "MATIN"
    if "midi" in p:
        return "periode", "MIDI"
    if "soir" in p:
        return "periode", "SOIR"
    return None, None
