# Assistant intelligent de recommandation d'itinéraires — Réseau SOTRAL

Assistant conversationnel (NLP + RAG) permettant d'obtenir un itinéraire
en langage naturel sur le réseau de bus SOTRAL à Lomé, Togo.

## Prérequis

- [Docker](https://docs.docker.com/get-docker/) et Docker Compose (inclus dans Docker Desktop)
- [Ollama](https://ollama.com/download) installé **sur la machine hôte** (pas dans un conteneur), avec le modèle `llama3.2:3b` :
```bash
  ollama pull llama3.2:3b
```

## ⚠️ Point important (Linux uniquement)

Sur Linux, Ollama n'écoute par défaut que sur `127.0.0.1`, ce qui le rend
inaccessible depuis un conteneur Docker. Avant de lancer l'application,
démarrez Ollama ainsi :
```bash
OLLAMA_HOST=0.0.0.0:11434 ollama serve
```
(Sur Windows/Mac avec Docker Desktop, ce n'est généralement pas nécessaire.)

## Installation

1. **Clonez le dépôt :**
```bash
   git clone https://github.com/ghislaine1010-lab/assistant_sotral.git
   cd assistant_sotral
```

2. **Créez le fichier `.env`** à la racine du projet (non fourni sur Git pour des raisons de sécurité) :
```env
   DB_HOST=base_de_donnees
   DB_NAME=sotral_db
   DB_USER=sotral_user
   DB_PASSWORD=merci_p@p@10
   GMAIL_ADRESSE=votre_adresse@gmail.com
   GMAIL_MOT_DE_PASSE_APP=votre_mot_de_passe_application
   SESSION_SECRET=une_chaine_aleatoire_longue
```

3. **Lancez Ollama** (voir point important ci-dessus), puis dans un terminal séparé :
```bash
   docker compose up -d
```

4. **Patientez 20-30 secondes** (import automatique des données), puis vérifiez :
```bash
   docker compose ps
```
   Les deux services doivent afficher le statut "Up" (la base de données en "healthy").

5. **Accédez à l'application :** [http://127.0.0.1:8000/app](http://127.0.0.1:8000/app)

## Arrêter l'application

```bash
docker compose down
```
(ajoutez `-v` pour aussi supprimer les données importées et repartir de zéro)

## Structure du projet

## Lancer les tests

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m pytest tests/test_regression.py -v
```

## Auteure

EKLOU Abla Ghislaine — Licence Professionnelle IABD, ESGIS — Stage ROOK-IT
