# Licensed under PolyForm Noncommercial 1.0.0
# © 2026 Clément THIEULEUX
"""
Export PDF du carnet de traitements phytosanitaires pour le contrôleur
bio — colonnes configurables depuis les Paramètres de l'application.
"""

import os
from datetime import datetime

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
)

from db import get_connection, get_entreprise, get_parametres_app
import utils.debug as debug


def exporter_carnet_bio_pdf(date_debut: str, date_fin: str,
                              chemin_sortie: str) -> str:
    """Génère le PDF du carnet de traitements pour la période donnée.

    date_debut/date_fin : 'YYYY-MM-DD'
    chemin_sortie : chemin complet du fichier .pdf à créer

    Retourne le chemin du fichier créé.
    """
    params = get_parametres_app()
    ent = get_entreprise()

    inclure_amm     = bool(params.get("export_inclure_amm"))
    inclure_dar     = bool(params.get("export_inclure_dar"))
    inclure_bio_agr = bool(params.get("export_inclure_bio_agr"))
    inclure_meteo   = bool(params.get("export_inclure_meteo"))
    inclure_epi     = bool(params.get("export_inclure_epi"))
    portrait        = params.get("export_orientation", "portrait") != "paysage"

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT t.date_traitement, parc.nom AS parcelle_nom,
               t.culture, t.categorie_ppp, p.nom_commercial, p.num_amm, u.dar,
               t.bio_agresseur, t.dose_appliquee, t.unite,
               t.meteo_temperature, t.meteo_vent, t.meteo_nebulosite,
               t.epi_utilises,
               ud.prenom || ' ' || ud.nom AS decideur_nom,
               ud.certiphyto_type AS decideur_cipp,
               uo.prenom || ' ' || uo.nom AS operateur_nom,
               uo.certiphyto_type AS operateur_cipp
        FROM ppp_traitements t
        JOIN ppp_produits p ON p.id = t.produit_id
        LEFT JOIN parcelles parc ON parc.id = t.parcelle_id
        LEFT JOIN ppp_decisions d ON d.id = t.decision_id
        LEFT JOIN ppp_usages u ON u.id = d.usage_id
        LEFT JOIN users ud ON ud.id = d.decideur_id
        JOIN users uo ON uo.id = t.operateur_id
        WHERE t.date_traitement BETWEEN ? AND ?
        ORDER BY t.date_traitement ASC
    """, (date_debut, date_fin))
    rows = cur.fetchall()
    cur.close()
    debug.debug(f"[export_bio] {len(rows)} traitement(s) trouvé(s) "
                f"entre {date_debut} et {date_fin}")

    # ── Construction de l'en-tête de colonnes selon les options ──
    entetes = ["Date", "Culture réelle (Parcelle)", "Cat. PPP", "Produit"]
    if inclure_amm:
        entetes.append("N° AMM")
    if inclure_bio_agr:
        entetes.append("Bio-agresseur")
    entetes.append("Dose")
    if inclure_dar:
        entetes.append("DAR (j)")
    if inclure_meteo:
        entetes.append("Météo")
    if inclure_epi:
        entetes.append("EPI")
    entetes.extend(["Décideur (CIPP)", "Applicateur (CIPP)"])

    donnees = [entetes]
    for r in rows:
        (date_t, parcelle, culture, categorie_ppp, produit, amm, dar, bio_agr,
         dose, unite, temp, vent, neb, epi,
         decideur_nom, decideur_cipp, operateur_nom, operateur_cipp) = r

        culture_parcelle = culture or "—"
        if parcelle:
            culture_parcelle += f" ({parcelle})"

        ligne = [_fmt_date(date_t), culture_parcelle,
                 categorie_ppp or "—", produit or "—"]
        if inclure_amm:
            ligne.append(amm or "—")
        if inclure_bio_agr:
            ligne.append(bio_agr or "—")
        ligne.append(f"{dose} {unite}" if dose else "—")
        if inclure_dar:
            ligne.append(str(dar) if dar else "—")
        if inclure_meteo:
            meteo_txt = []
            if temp is not None:
                meteo_txt.append(f"{temp}°C")
            if vent:
                meteo_txt.append(vent)
            if neb:
                meteo_txt.append(neb)
            ligne.append(" / ".join(meteo_txt) if meteo_txt else "—")
        if inclure_epi:
            ligne.append("Oui" if epi else "Non")

        ligne.append(_avec_cipp(decideur_nom, decideur_cipp))
        ligne.append(_avec_cipp(operateur_nom, operateur_cipp))
        donnees.append(ligne)

    _generer_pdf(chemin_sortie, ent, date_debut, date_fin, donnees,
                 len(entetes), portrait)
    debug.debug(f"[export_bio] PDF généré : {chemin_sortie}")
    return chemin_sortie


def _avec_cipp(nom: str, cipp: str) -> str:
    if not nom:
        return "—"
    if cipp:
        return f"{nom} ({cipp})"
    return nom


def _fmt_date(d: str) -> str:
    if not d:
        return "—"
    try:
        return datetime.strptime(d, "%Y-%m-%d").strftime("%d/%m/%Y")
    except Exception:
        return d


def _generer_pdf(chemin: str, entreprise: dict, date_debut: str,
                  date_fin: str, donnees: list, nb_colonnes: int,
                  portrait: bool = True):
    pagesize = A4 if portrait else landscape(A4)
    doc = SimpleDocTemplate(
        chemin, pagesize=pagesize,
        leftMargin=12 * mm, rightMargin=12 * mm,
        topMargin=15 * mm, bottomMargin=15 * mm,
    )

    styles = getSampleStyleSheet()
    style_titre = ParagraphStyle(
        "TitrePerso", parent=styles["Title"], fontSize=15, spaceAfter=4)
    style_sous_titre = ParagraphStyle(
        "SousTitre", parent=styles["Normal"], fontSize=9,
        textColor=colors.HexColor("#57534e"))
    style_cellule = ParagraphStyle(
        "Cellule", parent=styles["Normal"], fontSize=7, leading=8.5)
    style_entete = ParagraphStyle(
        "Entete", parent=styles["Normal"], fontSize=7.5, leading=9,
        textColor=colors.white, fontName="Helvetica-Bold")

    story = []

    nom_ent = entreprise.get("nom") or "Exploitation"
    story.append(Paragraph("Carnet de traitements phytosanitaires", style_titre))
    story.append(Paragraph(
        f"{nom_ent}"
        + (f" — N° agrément bio : {entreprise.get('num_bio')}"
           if entreprise.get("num_bio") else ""),
        style_sous_titre))
    story.append(Paragraph(
        f"Période : du {_fmt_date(date_debut)} au {_fmt_date(date_fin)}",
        style_sous_titre))
    story.append(Spacer(1, 8 * mm))

    if len(donnees) <= 1:
        story.append(Paragraph(
            "Aucun traitement enregistré sur cette période.",
            styles["Normal"]))
    else:
        largeur_page = pagesize[0] - 24 * mm
        largeur_col = largeur_page / nb_colonnes

        # Convertir chaque cellule en Paragraph pour permettre le
        # retour à la ligne automatique (important en portrait, où
        # les colonnes sont plus étroites)
        donnees_wrap = [
            [Paragraph(str(cell), style_entete if i == 0 else style_cellule)
             for cell in ligne]
            for i, ligne in enumerate(donnees)
        ]

        table = Table(donnees_wrap, repeatRows=1,
                      colWidths=[largeur_col] * nb_colonnes)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#16a34a")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d6d3d1")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1),
             [colors.white, colors.HexColor("#f5f5f4")]),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 3),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(table)

    story.append(Spacer(1, 8 * mm))
    story.append(Paragraph(
        f"Document généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}",
        style_sous_titre))

    doc.build(story)