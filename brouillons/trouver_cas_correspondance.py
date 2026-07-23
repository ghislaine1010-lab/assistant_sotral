import psycopg2
from moteur_recommandation import recommander

conn = psycopg2.connect(host="localhost", dbname="sotral_db",
                         user="sotral_user", password="merci_p@p@10")
cur = conn.cursor()

cur.execute("""
    SELECT a1.nom, a2.nom
    FROM arrets_lignes al1
    JOIN arrets a1 ON a1.id = al1.arret_id
    JOIN arrets_lignes al2 ON al2.ligne_id <> al1.ligne_id
    JOIN arrets a2 ON a2.id = al2.arret_id
    WHERE a1.nom <> a2.nom
      AND NOT EXISTS (
        SELECT 1 FROM arrets_lignes x
        JOIN arrets_lignes y ON y.ligne_id = x.ligne_id
        WHERE x.arret_id = al1.arret_id AND y.arret_id = al2.arret_id
      )
    LIMIT 1;
""")
depart, destination = cur.fetchone()
cur.close(); conn.close()

print(f"Cas trouvé automatiquement : « {depart} » -> « {destination} »")
print(recommander(depart, destination))
