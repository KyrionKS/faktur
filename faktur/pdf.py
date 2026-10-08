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

from faktur import betraege, bloecke, einstellungen, gestaltung, texte

#: Der Rand ringsum.
RAND = 20 * mm

#: Die Breiten, die das Logo haben kann, in Millimeter.
LOGO_GROESSEN = {"klein": 16.0, "mittel": 22.0, "gross": 32.0}

#: Die Größe, die gilt, wenn keine eingestellt oder eine unbekannte ist.
LOGO_STANDARD = "mittel"

#: Der Abstand der Logo-Oberkante von der Blattkante. Er ist fest, damit das
#: Logo bei jeder Größe gleich weit oben steht.
LOGO_ABSTAND = 10 * mm

#: Die Breite, die für den Text bleibt.
NUTZBREITE = A4[0] - 2 * RAND


def logo_groesse(db: sqlite3.Connection) -> str:
    """Liest die gewünschte Logogröße.

    Args:
        db: Die Datenbankverbindung.

    Returns:
        ``klein``, ``mittel`` oder ``gross``.
    """
    wert = einstellungen.hole(db, "logo_groesse", LOGO_STANDARD).strip().lower()
    return wert if wert in LOGO_GROESSEN else LOGO_STANDARD


def logo_breite(db: sqlite3.Connection | None = None) -> float:
    """Nennt die Breite des Logos in Millimeter.

    Args:
        db: Die Datenbankverbindung, oder ``None`` für die Standardgröße.

    Returns:
        Die Breite in Millimetern.
    """
    if db is None:
        return LOGO_GROESSEN[LOGO_STANDARD]
    return LOGO_GROESSEN[logo_groesse(db)]


def bildverhaeltnis(pfad: Path) -> float | None:
    """Liest das echte Seitenverhältnis einer Bilddatei.

    Ohne das echte Verhältnis sähe ein breites Logo anders aus als ein
    hohes, obwohl beide gleich breit gesetzt sind.

    Args:
        pfad: Die Bilddatei.

    Returns:
        Breite geteilt durch Höhe, oder ``None``, wenn die Datei nicht
        lesbar ist.
    """
    from PIL import Image, UnidentifiedImageError

    try:
        with Image.open(pfad) as bild:
            breite, hoehe = bild.size
    except (OSError, UnidentifiedImageError, ValueError):
        return None

    if not breite or not hoehe:
        return None

    return breite / hoehe


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
    art = dokument["art"]

    def gehoert(name: str) -> bool:
        """Sagt, ob ein Block auf dieses Dokument gehört.

        Args:
            name: Der Name des Blocks.

        Returns:
            ``True``, wenn er erscheinen soll.
        """
        return bloecke.gehoert(db, art, name)

    firma_zeile: list[Paragraph] = []

    if gehoert("firma"):
        firma_zeile.append(
            Paragraph(
                sauber(einstellungen.hole(db, "firma", "New Air Media Group")),
                stil["firma"],
            )
        )

    # Telefon und E-Mail stehen heute in einer gemeinsamen Zeile. Das bleibt
    # so, solange beide an sind. Schaltet man nur eines ab, bleibt das
    # andere für sich allein stehen — eine Zeile mit einem einzigen Eintrag
    # sieht nach einem Fehler aus.
    kontakt: list[str] = []
    if gehoert("email"):
        email = einstellungen.hole(db, "email")
        if email:
            kontakt.append(email)
    if gehoert("telefon"):
        telefon = einstellungen.hole(db, "telefon")
        if telefon:
            kontakt.append(telefon)

    rest: list[tuple[str, str]] = []
    if gehoert("zusatz"):
        rest.append(einstellungen.hole(db, "zusatz"))
    if gehoert("anschrift"):
        rest.append(einstellungen.hole(db, "strasse"))
        rest.append(
            " ".join(
                teil
                for teil in (
                    einstellungen.hole(db, "plz"),
                    einstellungen.hole(db, "ort"),
                )
                if teil
            )
        )
    if kontakt:
        rest.append(" · ".join(kontakt))
    if gehoert("webseite"):
        rest.append(einstellungen.hole(db, "webseite"))

    for stueck in rest:
        if stueck:
            firma_zeile.append(Paragraph(sauber(stueck), stil["klein"]))

    # Rechts bleibt Platz für das Logo. Es setzt der Seitenkopf auf jede
    # Seite, deshalb hier nicht noch einmal. Ohne Logo gehört die ganze
    # Breite der Firmenzeile: Ein leerer rechter Rand, den niemand
    # bestellt hat, sieht nach einem Fehler aus.
    with_logo = gehoert("logo")
    spalten = [NUTZBREITE * 0.62, NUTZBREITE * 0.38] if with_logo else [NUTZBREITE]

    kopf = Table(
        [[firma_zeile, ""]] if with_logo else [firma_zeile],
        colWidths=spalten,
    )
    kopf.setStyle(_ohne_kasten(spalten))
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
        ist_rabatt = betrag < 0
        # Ein Rabatt steht in derselben Schrift wie die anderen Zeilen, aber
        # in der Akzentfarbe. So ist er als eigener Posten erkennbar, ohne
        # dass die Tabelle bunt wird.
        text_stil = stil["rabatt_text"] if ist_rabatt else stil["tab_text"]
        zahl_stil = stil["rabatt_zahl"] if ist_rabatt else stil["tab_zahl"]

        zeilen.append(
            [
                Paragraph(sauber(position["bezeichnung"]), text_stil),
                Paragraph(betraege.menge(position["menge"]), zahl_stil),
                Paragraph(sauber(position["einheit"]), text_stil),
                Paragraph(betraege.euro(position["preis"]), zahl_stil),
                Paragraph(betraege.euro(betrag), zahl_stil),
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

    art = dokument["art"]

    def gehoert(name: str) -> bool:
        """Sagt, ob ein Block auf dieses Dokument gehört.

        Args:
            name: Der Name des Blocks.

        Returns:
            ``True``, wenn er erscheinen soll.
        """
        return bloecke.gehoert(db, art, name)

    # Bankverbindung, Steuernummer und Zahlhinweis standen früher fest auf
    # „nur Rechnung". Jetzt entscheidet die Auswahl, und die Voreinstellung
    # sagt dasselbe wie vorher.
    if art != "angebot":
        if gehoert("zahlbar"):
            hinweise: list[str] = ["Zahlbar ohne Abzug."]
            if dokument["faellig"]:
                hinweise.insert(0, f"Zahlbar bis {sauber(dokument['faellig'])}.")
            teile.append(Paragraph(" ".join(hinweise), stil["klein"]))

        if gehoert("bank"):
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
                teile += [
                    Spacer(1, 10),
                    Paragraph("<br/>".join(bank), stil["klein"]),
                ]

        # Die Steuernummer stand früher nur auf der Rechnung. Auf einem
        # Angebot wäre sie irreführend.
        if gehoert("steuer"):
            steuer = einstellungen.hole(db, "steuernummer")
            if steuer:
                teile += [
                    Spacer(1, 8),
                    Paragraph(sauber(f"Steuernummer {steuer}"), stil["klein"]),
                ]

    teile.append(Spacer(1, 16))

    # Die Grussformel steht schon im Brieftext, wenn der Baustein sie
    # enthält. Zweimal auf einem Brief sieht nach einem Fehler aus. Sie
    # bleibt auch dann stehen, wenn der Inhaber abgeschaltet ist: ein
    # Brief ohne Abschluss sieht schlimmer aus als einer mit einem leeren.
    if not _brief_hat_gruss(db, dokument):
        teile.append(Paragraph("Freundliche Grüße", stil["absatz"]))
        if gehoert("inhaber"):
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


def deko(db: sqlite3.Connection, art: str) -> Callable[[object, object], None]:
    """Macht Kopf- und Fusszeile für jede Seite.

    Args:
        db: Die Datenbankverbindung.
        art: ``angebot`` oder ``rechnung``. Die Fußzeile kann je nach Art
            anders aussehen, deshalb muss sie die Art kennen.

    Returns:
        Eine Funktion, die reportlab auf jeder Seite aufruft.
    """
    firma = einstellungen.hole(db, "firma", "New Air Media Group")
    logopfad = einstellungen.logo_pfad(db) if bloecke.gehoert(db, art, "logo") else None
    breite, hoehe = A4
    grau = colors.Color(*gestaltung.hex_rgb(gestaltung.SEKUNDAER))
    verhaeltnis = bildverhaeltnis(logopfad) if logopfad else None
    breite_logo = logo_breite(db) * mm
    # Die Fußzeile wird auf die Leinwand geschrieben und hat deshalb keinen
    # Absatzstil. Sie braucht die Größe des Kleinststils, aber mit dem
    # Faktor der gewählten Textgröße — sonst schrumpft sie bei „groß".
    schrift = gestaltung.groesse_von(
        "klein", gestaltung.groesse_faktor(text_groesse(db))
    )

    def zeichnen(leinwand: object, _dokument: object) -> None:
        """Schreibt Logo und Fusszeile auf die Seite.

        Args:
            leinwand: Die reportlab-Leinwand.
            _dokument: Das Dokumentobjekt von reportlab, ungenutzt.
        """
        leinwand.saveState()

        if logopfad and verhaeltnis:
            # Die Höhe folgt dem echten Seitenverhältnis der Datei. Vorher
            # stand hier ein geratener Wert, der für das eigene Logo nicht
            # stimmte: Es saß mehrere Millimeter zu tief, und bei einer
            # größeren Variante wäre der Fehler mitgewachsen.
            hoehe_logo = breite_logo / verhaeltnis
            leinwand.drawImage(
                str(logopfad),
                breite - breite_logo - RAND,
                hoehe - hoehe_logo - LOGO_ABSTAND,
                width=breite_logo,
                height=hoehe_logo,
                preserveAspectRatio=True,
                anchor="sw",
                mask="auto",
            )

        leinwand.setFont(gestaltung.SCHRIFT, schrift)
        leinwand.setFillColor(grau)

        if bloecke.gehoert(db, art, "firmenzeile"):
            leinwand.drawString(RAND, 12 * mm, firma)
        if bloecke.gehoert(db, art, "seitenzahl"):
            leinwand.drawRightString(
                breite - RAND, 12 * mm, f"Seite {leinwand.getPageNumber()}"
            )

        leinwand.restoreState()

    return zeichnen


def text_groesse(db: sqlite3.Connection) -> str:
    """Liest die gewünschte Textgröße.

    Args:
        db: Die Datenbankverbindung.

    Returns:
        ``klein``, ``normal`` oder ``gross``.
    """
    wert = einstellungen.hole(db, "text_groesse", "normal").strip().lower()
    return wert if wert in gestaltung.GRUESSEN else "normal"


def erzeugen(db: sqlite3.Connection, dokument: sqlite3.Row, ziel: Path) -> Path:
    """Schreibt die PDF eines Dokuments.

    Args:
        db: Die Datenbankverbindung.
        dokument: Das Dokument aus :func:`faktur.dateien.dokument_holen`.
        ziel: Wohin geschrieben werden soll.

    Returns:
        Der Pfad der erzeugten Datei.
    """
    stil = gestaltung.stile(gestaltung.groesse_faktor(text_groesse(db)))
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

    rahmen = deko(db, dokument["art"])
    doc.build(inhalt, onFirstPage=rahmen, onLaterPages=rahmen)
    return ziel
