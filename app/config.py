# -*- coding: utf-8 -*-
"""Configuration centralisée : connexion à la base de données.
   Toutes les infos sensibles viennent du fichier .env (jamais du code)."""

import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def connexion():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )
