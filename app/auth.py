# -*- coding: utf-8 -*-
"""Module d'authentification : inscription, validation d'email par
   format, hachage sécurisé du mot de passe (bcrypt, utilisé
   directement -- passlib abandonné le 11/08 suite à un conflit de
   compatibilité avec les versions récentes de bcrypt), génération et
   envoi d'un code de confirmation par email réel (Gmail SMTP)."""

import os
import re
import random
import smtplib
import bcrypt
from email.mime.text import MIMEText
from datetime import datetime, timedelta

from dotenv import load_dotenv

from app.config import connexion

load_dotenv()

GMAIL_ADRESSE = os.getenv("GMAIL_ADRESSE")
GMAIL_MOT_DE_PASSE_APP = os.getenv("GMAIL_MOT_DE_PASSE_APP")

REGEX_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def email_valide(email):
    """Vérifie que le format de l'adresse email est correct
    (présence d'un @ et d'un domaine avec extension)."""
    return bool(REGEX_EMAIL.match(email or ""))


def _hacher_mot_de_passe(mot_de_passe):
    """Hache le mot de passe avec bcrypt directement (sans passlib)."""
    return bcrypt.hashpw(mot_de_passe.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verifier_mot_de_passe(mot_de_passe, hache):
    """Vérifie un mot de passe contre son hachage bcrypt."""
    return bcrypt.checkpw(mot_de_passe.encode("utf-8"), hache.encode("utf-8"))


def _generer_code():
    return f"{random.randint(0, 999999):06d}"


def _envoyer_email_confirmation(destinataire, code):
    """Envoie un vrai email via le compte Gmail configuré dans .env."""
    message = MIMEText(
        f"Bonjour,\n\n"
        f"Voici votre code de confirmation pour l'Assistant SOTRAL : {code}\n\n"
        f"Ce code est valable 15 minutes.\n\n"
        f"Si vous n'êtes pas à l'origine de cette demande, ignorez ce message."
    )
    message["Subject"] = "Confirmez votre compte — Assistant SOTRAL"
    message["From"] = GMAIL_ADRESSE
    message["To"] = destinataire

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as serveur:
        serveur.login(GMAIL_ADRESSE, GMAIL_MOT_DE_PASSE_APP)
        serveur.send_message(message)


def inscrire(email, mot_de_passe):
    """Crée un nouvel utilisateur (non confirmé) et lui envoie un
    code de confirmation par email. Renvoie (succes: bool, message: str)."""
    if not email_valide(email):
        return False, "Adresse email invalide : le format doit être du type nom@domaine.extension."

    if len(mot_de_passe or "") < 6:
        return False, "Le mot de passe doit contenir au moins 6 caractères."

    conn = connexion(); cur = conn.cursor()
    cur.execute("SELECT id, email_confirme FROM utilisateurs WHERE email = %s;", (email,))
    existant = cur.fetchone()
    if existant and existant[1]:
        cur.close(); conn.close()
        return False, "Un compte confirmé existe déjà avec cette adresse email."

    hache = _hacher_mot_de_passe(mot_de_passe)
    code = _generer_code()
    expiration = datetime.now() + timedelta(minutes=15)

    if existant:
        cur.execute("""
            UPDATE utilisateurs SET mot_de_passe_hache = %s, code_confirmation = %s, code_expire_le = %s
            WHERE email = %s;
        """, (hache, code, expiration, email))
    else:
        cur.execute("""
            INSERT INTO utilisateurs (email, mot_de_passe_hache, code_confirmation, code_expire_le)
            VALUES (%s, %s, %s, %s);
        """, (email, hache, code, expiration))
    conn.commit()
    cur.close(); conn.close()

    try:
        _envoyer_email_confirmation(email, code)
    except Exception as e:
        return False, f"Compte créé, mais l'envoi de l'email a échoué ({e}). Réessayez plus tard."

    return True, "Un code de confirmation a été envoyé à votre adresse email."


def confirmer(email, code_saisi):
    """Vérifie le code de confirmation saisi par l'utilisateur."""
    conn = connexion(); cur = conn.cursor()
    cur.execute("""
        SELECT code_confirmation, code_expire_le FROM utilisateurs WHERE email = %s;
    """, (email,))
    row = cur.fetchone()
    if not row:
        cur.close(); conn.close()
        return False, "Aucun compte trouvé avec cette adresse email."

    code_attendu, expiration = row
    if datetime.now() > expiration:
        cur.close(); conn.close()
        return False, "Ce code a expiré. Veuillez recommencer l'inscription."
    if code_saisi != code_attendu:
        cur.close(); conn.close()
        return False, "Code incorrect."

    cur.execute("UPDATE utilisateurs SET email_confirme = TRUE WHERE email = %s;", (email,))
    conn.commit()
    cur.close(); conn.close()
    return True, "Email confirmé avec succès. Vous pouvez maintenant vous connecter."


def connecter(email, mot_de_passe):
    """Vérifie les identifiants de connexion. Renvoie (succes, message)."""
    conn = connexion(); cur = conn.cursor()
    cur.execute("""
        SELECT mot_de_passe_hache, email_confirme FROM utilisateurs WHERE email = %s;
    """, (email,))
    row = cur.fetchone()
    cur.close(); conn.close()

    if not row:
        return False, "Email ou mot de passe incorrect."
    hache, confirme = row
    if not _verifier_mot_de_passe(mot_de_passe, hache):
        return False, "Email ou mot de passe incorrect."
    if not confirme:
        return False, "Veuillez d'abord confirmer votre adresse email (code reçu par email)."
    return True, "Connexion réussie."
