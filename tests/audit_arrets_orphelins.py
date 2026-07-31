# -*- coding: utf-8 -*-
"""1) Combien d'arrêts géolocalisés ne sont rattachés à AUCUNE ligne ?
   2) Combien de lignes n'ont qu'un seul sens de circulation au lieu de deux ?"""

from app.config import connexion

conn = connexion(); cur = conn.cursor()

# ---------- 1. Arrêts orphelins ----------
cur.execute("""
    SELECT a.nom FROM arrets a
    LEFT JOIN arrets_lignes al ON al.arret_id = a.id
    WHERE al.id IS NULL
    ORDER BY a.nom;
""")
orphelins = [r[0] for r in cur.fetchall()]
cur.execute("SELECT COUNT(*) FROM arrets;")
total_arrets = cur.fetchone()[0]

print(f"Arrêts orphelins (aucune ligne associée) : {len(orphelins)} sur {total_arrets} "
      f"({len(orphelins)/total_arrets*100:.1f}%)")
for nom in orphelins[:15]:
    print(f"  - {nom}")
if len(orphelins) > 15:
    print(f"  ... et {len(orphelins)-15} autres")

# ---------- 2. Lignes à sens unique ----------
cur.execute("""
    SELECT ref, COUNT(DISTINCT nom) FROM lignes
    GROUP BY ref
    ORDER BY ref;
""")
print("\nNombre de sens (tracés) par ligne :")
sens_unique = []
for ref, n in cur.fetchall():
    if n == 1:
        sens_unique.append(ref)
    print(f"  {ref:5s} : {n} sens" + ("  <-- sens unique" if n == 1 else ""))

print(f"\nLignes à sens unique : {len(sens_unique)} -> {sens_unique}")

cur.close(); conn.close()
