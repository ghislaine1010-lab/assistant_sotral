# -*- coding: utf-8 -*-
"""Moteur de recommandation d'itinéraires (SF3). La correspondance se
   fait par NOM d'arrêt, en tenant compte des VARIANTES de noms.
   Étendu le 04/08 aux trajets à 2-3 correspondances.
   Estimation de durée ajoutée le 06/08 : calibrée sur 285 courses
   réelles de la base (temps moyen mesuré = 1,83 min/arrêt), plutôt
   qu'un chiffre arbitraire (cf. tests/calibrer_duree_par_arret.py)."""

from app.config import connexion

TEMPS_PAR_ARRET_MIN = 1.83  # calibré le 06/08 sur 285 courses réelles


def _formater_duree(nb_arrets):
    minutes = round(nb_arrets * TEMPS_PAR_ARRET_MIN)
    return f"environ {minutes} min" if minutes > 0 else "moins d'une minute"


def _variantes(nom):
    variantes = {nom}
    if nom.startswith("Arrêt "):
        variantes.add(nom[len("Arrêt "):])
    else:
        variantes.add("Arrêt " + nom)
    return list(variantes)


def trajet_direct(cur, depart, destination):
    variantes_dep = _variantes(depart)
    variantes_dest = _variantes(destination)
    cur.execute("""
        SELECT l.ref, l.nom, a1.nom, a2.nom, al1.ordre, al2.ordre
        FROM arrets_lignes al1
        JOIN arrets_lignes al2 ON al1.ligne_id = al2.ligne_id
        JOIN lignes l ON l.id = al1.ligne_id
        JOIN arrets a1 ON a1.id = al1.arret_id
        JOIN arrets a2 ON a2.id = al2.arret_id
        WHERE a1.nom = ANY(%s) AND a2.nom = ANY(%s) AND al1.ordre < al2.ordre
        ORDER BY (al2.ordre - al1.ordre) ASC
        LIMIT 1;
    """, (variantes_dep, variantes_dest))
    resultat = cur.fetchone()
    if resultat:
        ref, nom_ligne, _, _, o1, o2 = resultat
        return (ref, nom_ligne, depart, destination, o1, o2)
    return None


def trajet_avec_correspondance(cur, depart, destination):
    variantes_dep = _variantes(depart)
    variantes_dest = _variantes(destination)
    cur.execute("""
        SELECT l1.ref, l1.nom, a_t1.nom, l2.ref, l2.nom,
               al_dep.ordre, al_t1.ordre, al_t2.ordre, al_arr.ordre
        FROM arrets_lignes al_dep
        JOIN arrets a_dep ON a_dep.id = al_dep.arret_id AND a_dep.nom = ANY(%s)
        JOIN lignes l1 ON l1.id = al_dep.ligne_id
        JOIN arrets_lignes al_t1 ON al_t1.ligne_id = al_dep.ligne_id
                                 AND al_t1.ordre > al_dep.ordre
        JOIN arrets a_t1 ON a_t1.id = al_t1.arret_id
        JOIN arrets a_t2 ON a_t2.nom = a_t1.nom AND a_t2.id <> a_t1.id
        JOIN arrets_lignes al_t2 ON al_t2.arret_id = a_t2.id
                                 AND al_t2.ligne_id <> al_dep.ligne_id
        JOIN lignes l2 ON l2.id = al_t2.ligne_id
        JOIN arrets_lignes al_arr ON al_arr.ligne_id = al_t2.ligne_id
                                   AND al_arr.ordre > al_t2.ordre
        JOIN arrets a_arr ON a_arr.id = al_arr.arret_id AND a_arr.nom = ANY(%s)
        LIMIT 1;
    """, (variantes_dep, variantes_dest))
    return cur.fetchone()


def trouver_itineraire(depart, destination):
    conn = connexion(); cur = conn.cursor()

    direct = trajet_direct(cur, depart, destination)
    if direct:
        ref, nom_ligne, a1, a2, o1, o2 = direct
        cur.close(); conn.close()
        nb_arrets = o2 - o1
        duree = _formater_duree(nb_arrets)
        texte = (f"Ligne {ref} ({nom_ligne}) — trajet direct, sans changement de ligne.\n"
                 f"Montez à « {a1} », descendez à « {a2} » "
                 f"(environ {nb_arrets} arrêt(s), durée estimée : {duree}).")
        return {"type": "direct", "texte": texte, "lignes": [ref], "arrets": [a1, a2],
                "duree_min": round(nb_arrets * TEMPS_PAR_ARRET_MIN)}

    from app.faits import arret_est_isole
    if arret_est_isole(depart) or arret_est_isole(destination):
        arret_isole = depart if arret_est_isole(depart) else destination
        cur.close(); conn.close()
        return {"type": "aucun", "lignes": [], "arrets": [],
                "texte": (f"L'arrêt « {arret_isole} » figure dans nos données mais n'est "
                          f"actuellement rattaché à aucune ligne connue (limite des "
                          f"données cartographiques disponibles).")}

    corresp = trajet_avec_correspondance(cur, depart, destination)
    cur.close(); conn.close()
    if corresp:
        ref1, nom1, transfert, ref2, nom2, o_dep, o_t1, o_t2, o_arr = corresp
        nb_arrets_1 = o_t1 - o_dep
        nb_arrets_2 = o_arr - o_t2
        duree_totale = _formater_duree(nb_arrets_1 + nb_arrets_2)
        texte = (f"Trajet avec 1 changement (durée estimée : {duree_totale}) :\n"
                 f"1) Ligne {ref1} ({nom1}) jusqu'à « {transfert} » ({nb_arrets_1} arrêt(s))\n"
                 f"2) Changez pour la ligne {ref2} ({nom2}) jusqu'à « {destination} » ({nb_arrets_2} arrêt(s)).")
        return {"type": "correspondance", "texte": texte, "lignes": [ref1, ref2],
                "arrets": [depart, transfert, destination],
                "duree_min": round((nb_arrets_1 + nb_arrets_2) * TEMPS_PAR_ARRET_MIN)}

    resultat_multi = trouver_itineraire_multi(depart, destination)
    if resultat_multi:
        return resultat_multi

    return {"type": "aucun", "texte": f"Aucun itinéraire trouvé entre « {depart} » et « {destination} ».",
            "lignes": [], "arrets": []}


def _construire_graphe_lignes():
    conn = connexion(); cur = conn.cursor()
    cur.execute("""
        SELECT al.ligne_id, l.ref, a.nom, al.ordre
        FROM arrets_lignes al
        JOIN lignes l ON l.id = al.ligne_id
        JOIN arrets a ON a.id = al.arret_id
        ORDER BY al.ligne_id, al.ordre;
    """)
    lignes_par_id = {}
    for ligne_id, ref, nom, ordre in cur.fetchall():
        lignes_par_id.setdefault(ligne_id, {"ref": ref, "arrets": []})
        lignes_par_id[ligne_id]["arrets"].append((nom, ordre))
    cur.close(); conn.close()
    return lignes_par_id


def trouver_itineraire_multi(depart, destination, max_correspondances=3):
    variantes_dep = _variantes(depart)
    variantes_dest = _variantes(destination)
    lignes_par_id = _construire_graphe_lignes()

    depart_options = []
    for lid, info in lignes_par_id.items():
        for nom, ordre in info["arrets"]:
            if nom in variantes_dep:
                depart_options.append((lid, ordre))
    if not depart_options:
        return None

    file_attente = [(lid, ordre, [(lid, ordre, None)]) for lid, ordre in depart_options]
    visitees = set()

    while file_attente:
        ligne_id, ordre_embarq, chemin = file_attente.pop(0)
        if len(chemin) > max_correspondances + 1:
            continue

        for nom, ordre in lignes_par_id[ligne_id]["arrets"]:
            if nom in variantes_dest and ordre > ordre_embarq:
                chemin_final = chemin[:-1] + [(ligne_id, ordre_embarq, nom)]
                return _construire_reponse_multi(chemin_final, lignes_par_id, depart, destination)

        cle = (ligne_id, ordre_embarq)
        if cle in visitees:
            continue
        visitees.add(cle)

        for nom, ordre in lignes_par_id[ligne_id]["arrets"]:
            if ordre <= ordre_embarq:
                continue
            for autre_id, autre_info in lignes_par_id.items():
                if autre_id == ligne_id:
                    continue
                for nom2, ordre2 in autre_info["arrets"]:
                    if nom2 == nom:
                        nouveau_chemin = chemin[:-1] + [(ligne_id, ordre_embarq, nom)]
                        file_attente.append((autre_id, ordre2, nouveau_chemin + [(autre_id, ordre2, None)]))
                        break
    return None


def _construire_reponse_multi(chemin, lignes_par_id, depart, destination):
    noms_arrets_trajet = [depart]
    lignes_utilisees = []
    lignes_texte = []
    nb_arrets_total = 0

    for i, (ligne_id, ordre_embarq, nom_descente) in enumerate(chemin):
        if not nom_descente:
            continue
        ref = lignes_par_id[ligne_id]["ref"]
        # Retrouve l'ordre du point de descente pour calculer la longueur de cette étape
        ordre_descente = next((o for n, o in lignes_par_id[ligne_id]["arrets"] if n == nom_descente), ordre_embarq)
        nb_arrets_etape = ordre_descente - ordre_embarq
        nb_arrets_total += nb_arrets_etape

        lignes_utilisees.append(ref)
        noms_arrets_trajet.append(nom_descente)
        if i == 0:
            lignes_texte.append(f"1) Prenez la ligne {ref} jusqu'à « {nom_descente} » ({nb_arrets_etape} arrêt(s)).")
        else:
            lignes_texte.append(f"{i+1}) Changez pour la ligne {ref} jusqu'à « {nom_descente} » ({nb_arrets_etape} arrêt(s)).")

    noms_arrets_trajet[-1] = destination
    nb_correspondances = len(lignes_texte) - 1
    duree = _formater_duree(nb_arrets_total)
    texte = (f"Trajet avec {nb_correspondances} changement(s) — durée estimée : {duree} :\n" +
             "\n".join(lignes_texte))

    return {"type": "multi", "texte": texte, "lignes": lignes_utilisees, "arrets": noms_arrets_trajet,
            "duree_min": round(nb_arrets_total * TEMPS_PAR_ARRET_MIN)}


# ============================================================
# Comparateur d'itinéraires (06/08, inspiré de Citymapper) :
# rassemble plusieurs options possibles (direct + correspondances),
# classées par durée estimée croissante, plutôt qu'une seule réponse.
# ============================================================

def _trajet_direct_options(cur, depart, destination, limite=3):
    variantes_dep = _variantes(depart)
    variantes_dest = _variantes(destination)
    cur.execute("""
        SELECT l.ref, l.nom, a1.nom, a2.nom, al1.ordre, al2.ordre
        FROM arrets_lignes al1
        JOIN arrets_lignes al2 ON al1.ligne_id = al2.ligne_id
        JOIN lignes l ON l.id = al1.ligne_id
        JOIN arrets a1 ON a1.id = al1.arret_id
        JOIN arrets a2 ON a2.id = al2.arret_id
        WHERE a1.nom = ANY(%s) AND a2.nom = ANY(%s) AND al1.ordre < al2.ordre
        ORDER BY (al2.ordre - al1.ordre) ASC
        LIMIT 10;
    """, (variantes_dep, variantes_dest))
    options, refs_vues = [], set()
    for ref, nom_ligne, a1, a2, o1, o2 in cur.fetchall():
        if ref in refs_vues:
            continue
        refs_vues.add(ref)
        nb_arrets = o2 - o1
        options.append({
            "type": "direct", "duree_min": round(nb_arrets * TEMPS_PAR_ARRET_MIN),
            "nb_changements": 0,
            "texte": f"Ligne {ref} directe, {nb_arrets} arrêt(s)",
        })
        if len(options) >= limite:
            break
    return options


def _trajet_correspondance_options(cur, depart, destination, limite=3):
    variantes_dep = _variantes(depart)
    variantes_dest = _variantes(destination)
    cur.execute("""
        SELECT l1.ref, a_t1.nom, l2.ref,
               al_dep.ordre, al_t1.ordre, al_t2.ordre, al_arr.ordre
        FROM arrets_lignes al_dep
        JOIN arrets a_dep ON a_dep.id = al_dep.arret_id AND a_dep.nom = ANY(%s)
        JOIN lignes l1 ON l1.id = al_dep.ligne_id
        JOIN arrets_lignes al_t1 ON al_t1.ligne_id = al_dep.ligne_id
                                 AND al_t1.ordre > al_dep.ordre
        JOIN arrets a_t1 ON a_t1.id = al_t1.arret_id
        JOIN arrets a_t2 ON a_t2.nom = a_t1.nom AND a_t2.id <> a_t1.id
        JOIN arrets_lignes al_t2 ON al_t2.arret_id = a_t2.id
                                 AND al_t2.ligne_id <> al_dep.ligne_id
        JOIN lignes l2 ON l2.id = al_t2.ligne_id
        JOIN arrets_lignes al_arr ON al_arr.ligne_id = al_t2.ligne_id
                                   AND al_arr.ordre > al_t2.ordre
        JOIN arrets a_arr ON a_arr.id = al_arr.arret_id AND a_arr.nom = ANY(%s)
        LIMIT 15;
    """, (variantes_dep, variantes_dest))
    candidats, combos_vus = [], set()
    for ref1, transfert, ref2, o_dep, o_t1, o_t2, o_arr in cur.fetchall():
        combo = (ref1, transfert, ref2)
        if combo in combos_vus:
            continue
        combos_vus.add(combo)
        nb_arrets = (o_t1 - o_dep) + (o_arr - o_t2)
        candidats.append({
            "type": "correspondance", "duree_min": round(nb_arrets * TEMPS_PAR_ARRET_MIN),
            "nb_changements": 1,
            "texte": f"Ligne {ref1} puis {ref2} (via « {transfert} »), {nb_arrets} arrêt(s)",
        })
    candidats.sort(key=lambda c: c["duree_min"])
    return candidats[:limite]


def comparer_itineraires(depart, destination, max_options=3):
    """Renvoie jusqu'à max_options itinéraires possibles entre deux
    arrêts, classés par durée estimée croissante -- au lieu d'une
    seule réponse comme trouver_itineraire()."""
    conn = connexion(); cur = conn.cursor()

    options = []
    options += _trajet_direct_options(cur, depart, destination)
    options += _trajet_correspondance_options(cur, depart, destination)
    cur.close(); conn.close()

    if not options:
        itineraire_secours = trouver_itineraire(depart, destination)
        if itineraire_secours["type"] in ("multi", "aucun"):
            return [itineraire_secours] if itineraire_secours["type"] == "multi" else []

    options.sort(key=lambda o: o["duree_min"])
    return options[:max_options]


def formater_comparaison(depart, destination, options):
    if not options:
        return f"Aucun itinéraire trouvé entre « {depart} » et « {destination} »."
    lignes = [f"Voici {len(options)} option(s) pour aller de « {depart} » à « {destination} », "
              f"classées de la plus rapide à la plus lente :"]
    for i, opt in enumerate(options):
        etoile = " ⭐ (option la plus rapide)" if i == 0 else ""
        lignes.append(f"\n{i+1}) {opt['texte']} — durée estimée : environ {opt['duree_min']} min{etoile}")
    return "\n".join(lignes)
