# -*- coding: utf-8 -*-
"""Graphique des résultats RÉELS de ton jeu de test chiffré."""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))

# Graphique 1 : taux de réussite
categories = ["Compréhension\ndes requêtes", "Pertinence des\nitinéraires"]
valeurs = [100, 100]
cibles = [90, 95]
x = range(len(categories))
axes[0].bar(x, valeurs, color="#2F7D5E", width=0.5, label="Résultat obtenu", zorder=3)
axes[0].plot(x, cibles, "o--", color="#ED7D31", label="Cible (cahier des charges)", zorder=4)
axes[0].set_xticks(x); axes[0].set_xticklabels(categories, fontsize=9.5)
axes[0].set_ylim(0, 110); axes[0].set_ylabel("%")
axes[0].legend(fontsize=8.5); axes[0].set_title("Taux de réussite mesurés", fontsize=10.5)

# Graphique 2 : temps de réponse
categories2 = ["Requêtes\ndéterministes", "Requêtes\nvia LLM"]
temps = [0.03, 7.8]
axes[1].bar(categories2, temps, color=["#2E74B5", "#ED7D31"], width=0.5, zorder=3)
axes[1].axhline(3, color="red", linestyle="--", label="Cible (< 3 s)", zorder=4)
axes[1].set_ylabel("secondes"); axes[1].legend(fontsize=8.5)
axes[1].set_title("Temps de réponse mesurés", fontsize=10.5)

plt.tight_layout()
plt.savefig("resultats_evaluation.png", dpi=150)
print("Graphique enregistré : resultats_evaluation.png (dans le dossier courant)")
