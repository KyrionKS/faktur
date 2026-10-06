"""Aufbau von Angebot und Rechnung.

Beide Dokumente sind derselbe Brief mit anderem Titel und einem anderen
Abschlussteil. Deshalb gibt es nur eine Funktion, :func:`erzeugen`, und
zwei Stellen, die auf ``dokument["art"]`` schauen.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    Flowable,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from faktur import betraege, einstellungen, gestaltung, texte

#: Der Rand ringsum.
RAND = 20 * mm

#: Wie breit das kleine Logo in der Fusszeile sitzt.
LOGO_KLEIN = 22 * mm

#: Die Breite, die für den Text bleibt.
NUTZBREITE = A4[0] - 2 * RAND


class Linie(Flowable):
    """Eine dünne waagerechte Linie."""

    def __init__(self, breite: float, farbe: str = gestaltung.LINIE) -> None:
        """Legt die Linie an.

        Args:
            breite: Wie breit sie sein soll, in Punkten.
            farbe: Die Farbe als ``#RRGGBB``.
        """
        super().__init__()
        self.breite = breite
        self.hoehe = 0.6
        self.farbe = gestaltung.hex_rgb(farbe)

    def draw(self) -> None:
        """Zeichnet die Linie."""
        self.canv.setStrokeColor(colors.Color(*self.farbe))
        self.canv.setLineWidth(self.hoehe)
        self.canv.line(0, 0, self.breite, 0)


def sauber(text: str) -> str:
    """Maskiert die Sonderzeichen, die reportlab im Markup nicht mag.

    Args:
        text: Der Text mit möglichen ``&``, ``<`` und ``>``.

    Returns:
        Der Text, so wie reportlab ihn versteht.
    """
    return (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def werte_fuer(db: sqlite3.Connection, dokument: sqlite3.Row) -> dict[str, str]:
    """Sammelt alle Werte, die in den Platzhaltern stehen können.

    Args:
        db: Die Datenbankverbindung.
        dokument: Das Dokument aus :func:`faktur.dateien.dokument_holen`.

    Returns:
        Die Werte je Platzhalternamen.
    """
    from faktur import dateien

    ansprechpartner = dokument["ansprechpartner"] or dokument["firma"] or ""
    firma = einstellungen.hole(db, "firma", "New Air Media Group")
    zusatz = einstellungen.hole(db, "zusatz")
    positionen = dateien.positionen(db, dokument["id"])

    return {
        "Kunde": dokument["firma"] or "",
        "Kunde_Anrede": texte.anrede(ansprechpartner),
        "Ansprechpartner": ansprechpartner,
        "Nummer": dokument["nummer"] or "",
        "Datum": dokument["datum"] or "",
        "Faellig": dokument["faellig"] or "",
        "Gueltig_bis": dokument["gueltig_bis"] or "",
        "Betrag": betraege.euro(dateien.summe_von(db, dokument["id"])),
        "Anzahl_Positionen": str(len(positionen)),
        "EigeneFirma": firma,
        "EigeneFirma_voll": " ".join(teil for teil in (firma, zusatz) if teil),
        "Bank": einstellungen.hole(db, "bank"),
        "IBAN": einstellungen.hole(db, "iban"),
    }


def _ohne_kasten(spalten: list[float]) -> TableStyle:
    """Baut einen Tabellenstil ohne Rahmen und ohne Innenabstand.

    Args:
        spalten: Die Spaltenbreiten.

    Returns:
        Der Stil.
    """
    return TableStyle(
        [
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ("COLWIDTHS", (0, 0), (-1, -1), spalten),
        ]
    )


def kopfzeile(
    db: sqlite3.Connection, dokument: sqlite3.Row, stil: dict[str, ParagraphStyle]
) -> list[Flowable]:
    """Baut Firmenzeile, Logo, Empfängeranschrift und Titelblock.

    Args:
        db: Die Datenbankverbindung.
        dokument: Das Dokument.
        stil: Die Absatzstile.

    Returns:
        Die Bausteine des Briefkopfes.
    """
    teile: list[Flowable] = []

    # --- Firmenzeile links, Logo rechts, ohne Rahmen nebeneinander
    firma_zeile: list[Paragraph] = [
        Paragraph(
            sauber(einstellungen.hole(db, "firma", "New Air Media Group")),
            stil["firma"],
        )
    ]
    zusatz = einstellungen.hole(db, "zusatz")
    anschrift = einstellungen.hole(db, "strasse")
    stadt = " ".join(
        teil
        for teil in (einstellungen.hole(db, "plz"), einstellungen.hole(db, "ort"))
        if teil
    )
    kontakt = einstellungen.hole(db, "email")
    telefon = einstellungen.hole(db, "telefon")
    if telefon:
        kontakt = f"{kontakt} · {telefon}" if kontakt else telefon

    for stueck in (zusatz, anschrift, stadt, kontakt):
        if stueck:
            firma_zeile.append(Paragraph(sauber(stueck), stil["klein"]))

    # Rechts bleibt Platz für das Logo. Es setzt der Seitenkopf auf jede
    # Seite, deshalb hier nicht noch einmal.
    kopf = Table(
        [[firma_zeile, ""]],
        colWidths=[NUTZBREITE * 0.62, NUTZBREITE * 0.38],
    )
    kopf.setStyle(_ohne_kasten([NUTZBREITE * 0.62, NUTZBREITE * 0.38]))
    teile += [kopf, Spacer(1, 5), Linie(NUTZBREITE, gestaltung.AKZENT), Spacer(1, 16)]

    # --- Empfängeranschrift
    empfaenger: list[Paragraph] = []
    for feld in ("firma", "ansprechpartner", "strasse"):
        if dokument[feld]:
            empfaenger.append(Paragraph(sauber(dokument[feld]), stil["empfaenger"]))
    stadt = " ".join(teil for teil in (dokument["plz"], dokument["ort"]) if teil)
    if stadt:
        empfaenger.append(Paragraph(sauber(stadt), stil["empfaenger"]))
    teile += empfaenger + [Spacer(1, 18)]

    # --- Titel links, die Angaben rechtsbündig daneben
    ist_angebot = dokument["art"] == "angebot"
    titel = "Angebot" if ist_angebot else "Rechnung"

    angaben: list[tuple[str, str]] = [
        ("Angebot Nr." if ist_angebot else "Rechnung Nr.", dokument["nummer"] or ""),
        ("Datum", dokument["datum"] or ""),
    ]
    if ist_angebot and dokument["gueltig_bis"]:
        angaben.append(("Gültig bis", dokument["gueltig_bis"]))
    if not ist_angebot and dokument["faellig"]:
        angaben.append(("Fällig am", dokument["faellig"]))

    angaben_zeile = [
        Paragraph(f"{sauber(k)}: {sauber(w)}", stil["kopf_daten"])
        for k, w in angaben
        if w
    ]

    titelblock = Table(
        [[Paragraph(sauber(titel), stil["art"]), angaben_zeile]],
        colWidths=[NUTZBREITE * 0.42, NUTZBREITE * 0.58],
    )
    titelblock.setStyle(_ohne_kasten([NUTZBREITE * 0.42, NUTZBREITE * 0.58]))
    teile += [titelblock, Spacer(1, 14)]

    return teile


def brieftext(
    db: sqlite3.Connection, dokument: sqlite3.Row, stil: dict[str, ParagraphStyle]
) -> list[Flowable]:
    """Baut Anrede, Fliesstext und die eigene Notiz.

    Args:
        db: Die Datenbankverbindung.
        dokument: Das Dokument.
        stil: Die Absatzstile.

    Returns:
        Die Bausteine des Brieftextes.
    """
    eigener = dokument["eigener_text"] or ""
    vorlage = eigener or einstellungen.baustein(db, dokument["art"])
    werte = werte_fuer(db, dokument)

    # Ein eigener Text bleibt wörtlich stehen, der Baustein bekommt seine
    # Platzhalter eingesetzt.
    if not eigener:
        vorlage = texte.einsetzen(vorlage, werte)

    teile: list[Flowable] = []
    for nummer, absatz in enumerate(texte.absaetze(vorlage)):
        erste = texte.zeilen(absatz)[0]
        ist_anrede = nummer == 0 and erste.endswith(",") and len(erste) <= 40
        zielstil = stil["anrede"] if ist_anrede else stil["absatz"]
        teile.append(
            Paragraph("<br/>".join(sauber(z) for z in texte.zeilen(absatz)), zielstil)
        )

    if dokument["notiz"]:
        teile += [
            Spacer(1, 4),
            Paragraph(
                "<br/>".join(sauber(z) for z in texte.zeilen(dokument["notiz"])),
                stil["klein"],
            ),
        ]

    teile.append(Spacer(1, 6))
    return teile


def tabelle(
    db: sqlite3.Connection, dokument: sqlite3.Row, stil: dict[str, ParagraphStyle]
) -> list[Flowable]:
    """Baut die Positionstabelle und die Summe darunter.

    Args:
        db: Die Datenbankverbindung.
        dokument: Das Dokument.
        stil: Die Absatzstile.

    Returns:
        Die Bausteine der Tabelle.
    """
    from faktur import dateien

    # Die Bezeichnung nimmt den Rest, die Zahlen bekommen feste Spalten.
    zahlen_spalten = [16 * mm, 20 * mm, 28 * mm, 28 * mm]
    erste = NUTZBREITE - sum(zahlen_spalten)
    breiten = [erste, *zahlen_spalten]

    zeilen: list[list[Flowable]] = [
        [
            Paragraph("Bezeichnung", stil["tab_kopf"]),
            Paragraph("Menge", stil["tab_kopf"]),
            Paragraph("Einheit", stil["tab_kopf"]),
            Paragraph("Preis", stil["tab_kopf"]),
            Paragraph("Betrag", stil["tab_kopf"]),
        ]
    ]

    summe = 0.0
    for position in dateien.positionen(db, dokument["id"]):
        betrag = position["menge"] * position["preis"]
        summe += betrag
        zeilen.append(
            [
                Paragraph(sauber(position["bezeichnung"]), stil["tab_text"]),
                Paragraph(betraege.menge(position["menge"]), stil["tab_zahl"]),
                Paragraph(sauber(position["einheit"]), stil["tab_text"]),
                Paragraph(betraege.euro(position["preis"]), stil["tab_zahl"]),
                Paragraph(betraege.euro(betrag), stil["tab_zahl"]),
            ]
        )

    if len(zeilen) == 1:
        zeilen.append(
            [
                Paragraph("Keine Positionen.", stil["tab_text"]),
                "",
                "",
                "",
                "",
            ]
        )

    tabelle_ = Table(zeilen, colWidths=breiten, repeatRows=1)
    tabelle_.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("ALIGN", (3, 0), (3, -1), "RIGHT"),
                ("ALIGN", (4, 0), (4, -1), "RIGHT"),
                (
                    "LINEBELOW",
                    (0, 0),
                    (-1, 0),
                    0.6,
                    colors.Color(*gestaltung.hex_rgb(gestaltung.LINIE)),
                ),
                (
                    "LINEBELOW",
                    (0, -1),
                    (-1, -1),
                    0.6,
                    colors.Color(*gestaltung.hex_rgb(gestaltung.LINIE)),
                ),
                ("LEFTPADDING", (0, 0), (0, -1), 0),
                ("RIGHTPADDING", (0, 0), (0, -1), 12),
                ("LEFTPADDING", (1, 0), (-1, -1), 6),
                ("RIGHTPADDING", (1, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )

    # Die Summe steht rechts unter der Preisspalte, fett und in der
    # Akzentfarbe. Sie bleibt zusammen, damit sie nicht allein auf eine
    # neue Seite rutscht.
    summe_block = Table(
        [
            [
                "",
                "",
                "",
                Paragraph("Gesamtbetrag", stil["tab_zahl_fett"]),
                Paragraph(betraege.euro(summe), stil["summe"]),
            ]
        ],
        colWidths=breiten,
    )
    summe_block.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (3, 0), (3, 0), "RIGHT"),
                ("LEFTPADDING", (0, 0), (0, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )

    return [KeepTogether([tabelle_]), Spacer(1, 8), KeepTogether([summe_block])]


def abschluss(
    db: sqlite3.Connection, dokument: sqlite3.Row, stil: dict[str, ParagraphStyle]
) -> list[Flowable]:
    """Baut Bankverbindung, Steuernummer und Grussformel.

    Args:
        db: Die Datenbankverbindung.
        dokument: Das Dokument.
        stil: Die Absatzstile.

    Returns:
        Die Bausteine des Abschlussteils.
    """
    teile: list[Flowable] = [Spacer(1, 20)]

    if dokument["art"] != "angebot":
        hinweise: list[str] = ["Zahlbar ohne Abzug."]
        if dokument["faellig"]:
            hinweise.insert(0, f"Zahlbar bis {sauber(dokument['faellig'])}.")
        teile.append(Paragraph(" ".join(hinweise), stil["klein"]))

        bank = [
            f"{k}: {sauber(v)}"
            for k, v in (
                ("Bank", einstellungen.hole(db, "bank")),
                ("IBAN", einstellungen.hole(db, "iban")),
                ("BIC", einstellungen.hole(db, "bic")),
            )
            if v
        ]
        if bank:
            teile += [Spacer(1, 10), Paragraph("<br/>".join(bank), stil["klein"])]

        # Die Steuernummer steht nur auf der Rechnung. Auf einem Angebot
        # wäre sie irreführend.
        steuer = einstellungen.hole(db, "steuernummer")
        if steuer:
            teile += [
                Spacer(1, 8),
                Paragraph(sauber(f"Steuernummer {steuer}"), stil["klein"]),
            ]

    teile.append(Spacer(1, 16))

    # Die Grussformel steht schon im Brieftext, wenn der Baustein sie
    # enthält. Zweimal auf einem Brief sieht nach einem Fehler aus.
    if not _brief_hat_gruss(db, dokument):
        teile.append(Paragraph("Freundliche Grüße", stil["absatz"]))
        inhaber = einstellungen.hole(db, "inhaber")
        if inhaber:
            teile.append(Paragraph(sauber(inhaber), stil["absatz"]))

    return teile


def _brief_hat_gruss(db: sqlite3.Connection, dokument: sqlite3.Row) -> bool:
    """Sagt, ob der Brieftext schon mit einer Grussformel endet.

    Args:
        db: Die Datenbankverbindung.
        dokument: Das Dokument.

    Returns:
        ``True``, wenn der Baustein schon grüsst.
    """
    vorlage = dokument["eigener_text"] or einstellungen.baustein(db, dokument["art"])
    return "freundliche gr" in vorlage.lower()


def deko(db: sqlite3.Connection) -> Callable[[object, object], None]:
    """Macht Kopf- und Fusszeile für jede Seite.

    Args:
        db: Die Datenbankverbindung.

    Returns:
        Eine Funktion, die reportlab auf jeder Seite aufruft.
    """
    firma = einstellungen.hole(db, "firma", "New Air Media Group")
    logopfad = einstellungen.logo_pfad(db)
    breite, hoehe = A4
    grau = colors.Color(*gestaltung.hex_rgb(gestaltung.SEKUNDAER))

    def zeichnen(leinwand: object, _dokument: object) -> None:
        """Schreibt Logo und Fusszeile auf die Seite.

        Args:
            leinwand: Die reportlab-Leinwand.
            _dokument: Das Dokumentobjekt von reportlab, ungenutzt.
        """
        leinwand.saveState()

        if logopfad:
            leinwand.drawImage(
                str(logopfad),
                breite - LOGO_KLEIN - RAND,
                hoehe - LOGO_KLEIN * 0.35 - 10 * mm,
                width=LOGO_KLEIN,
                preserveAspectRatio=True,
                anchor="sw",
                mask="auto",
            )

        leinwand.setFont(gestaltung.SCHRIFT, 7.5)
        leinwand.setFillColor(grau)
        leinwand.drawString(RAND, 12 * mm, firma)
        leinwand.drawRightString(
            breite - RAND, 12 * mm, f"Seite {leinwand.getPageNumber()}"
        )
        leinwand.restoreState()

    return zeichnen


def erzeugen(db: sqlite3.Connection, dokument: sqlite3.Row, ziel: Path) -> Path:
    """Schreibt die PDF eines Dokuments.

    Args:
        db: Die Datenbankverbindung.
        dokument: Das Dokument aus :func:`faktur.dateien.dokument_holen`.
        ziel: Wohin geschrieben werden soll.

    Returns:
        Der Pfad der erzeugten Datei.
    """
    stil = gestaltung.stile()
    ziel.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        str(ziel),
        pagesize=A4,
        leftMargin=RAND,
        rightMargin=RAND,
        topMargin=20 * mm,
        bottomMargin=22 * mm,
        title=" ".join(
            teil for teil in (dokument["nummer"], dokument["firma"]) if teil
        ).strip(),
        author=einstellungen.hole(db, "firma"),
    )

    inhalt: list[Flowable] = []
    inhalt += kopfzeile(db, dokument, stil)
    inhalt += brieftext(db, dokument, stil)
    inhalt += tabelle(db, dokument, stil)
    inhalt += abschluss(db, dokument, stil)

    rahmen = deko(db)
    doc.build(inhalt, onFirstPage=rahmen, onLaterPages=rahmen)
    return ziel
