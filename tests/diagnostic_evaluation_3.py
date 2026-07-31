# -*- coding: utf-8 -*-
"""Le trajet échoue-t-il vraiment entre CES deux arrêts précis ?"""

from app.recommandation import trouver_itineraire

resultat = trouver_itineraire("Arrêt Lycée Moderne Adidogomé", "AD Zanguéra")
print("Résultat :", resultat)
