import psycopg2

# Connexion à la base de connaissances SOTRAL
connexion = psycopg2.connect(
    host="localhost",
    dbname="sotral_db",
    user="sotral_user",
    password="merci_p@p@10"
)
curseur = connexion.cursor()

curseur.execute("SELECT COUNT(*) FROM arrets;")
nb_arrets = curseur.fetchone()[0]
print(f"Connexion réussie ! La base contient {nb_arrets} arrêts.")

curseur.close()
connexion.close()
