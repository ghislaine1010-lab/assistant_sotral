# -*- coding: utf-8 -*-
"""« Eglise des AD Adakpamé » et « Arrêt Campus Sud » sont-ils
   vraiment déconnectés, ou est-ce un bug ?"""

from app.faits import lignes_desservant, correspondances_a

for arret in ["Eglise des AD Adakpamé", "Arrêt Campus Sud"]:
    print(f"Lignes desservant « {arret} » :", lignes_desservant(arret))

print("\nCorrespondances possibles à « Eglise des AD Adakpamé » :", correspondances_a("Eglise des AD Adakpamé"))
print("Correspondances possibles à « Arrêt Campus Sud » :", correspondances_a("Arrêt Campus Sud"))
