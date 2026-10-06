"""Farben und Schriften der PDF.

Eine einzige Akzentfarbe, aus dem Firmenlogo ausgelesen. Der Rest ist
Schwarz und Grau. Viel Weissraum und dünne Linien statt Kästen: ein Angebot
soll wie ein Brief aussehen, nicht wie ein Formular.
"""

from __future__ import annotations

#: Die Akzentfarbe, aus dem Logo ausgelesen.
AKZENT = "#512E80"

#: Der Fliesstext. Fast Schwarz, aber nicht hart.
TEXT = "#1A1A1A"

#: Kleinzeilen wie Seitenzahl und Fusszeile.
SEKUNDAER = "#6B6B6B"

#: Linien unter und ueber Tabellen.
LINIE = "#E2E2E2"

#: Ein sehr heller Ton, etwa für die Fusszeile.
FLACKE = "#F7F7F8"

#: Eine ruhige Groesse für Fliesstext auf A4.
GRUND = 9.5

#: Die Familie für Fliesstext und Tabellen.
SCHRIFT = "Helvetica"

#: Die Familie für Beträge und Überschriften.
BETRAG_SCHRIFT = "Helvetica-Bold"


def hex_rgb(wert: str) -> tuple[float, float, float]:
    """Wandelt ``#RRGGBB`` in die drei Anteile von 0 bis 1.

    Args:
        wert: Die Farbangabe mit führendem Rauten.

    Returns:
        Das Tripel für reportlab.
    """
    wert = wert.lstrip("#")
    return tuple(int(wert[i : i + 2], 16) / 255 for i in (0, 2, 4))  # type: ignore[return-value]


def stile() -> dict[str, object]:
    """Baut die Absatzstile für reportlab.

    Returns:
        Ein Dictionary aus Stilnamen und ``ParagraphStyle``.
    """
    from reportlab.lib.styles import ParagraphStyle

    return {
        "firma": ParagraphStyle(
            "firma",
            fontName=BETRAG_SCHRIFT,
            fontSize=13,
            leading=16,
            textColor=hex_rgb(AKZENT),
        ),
        "firma_rest": ParagraphStyle(
            "firma_rest",
            fontName=SCHRIFT,
            fontSize=8,
            leading=11,
            textColor=hex_rgb(SEKUNDAER),
        ),
        "empfaenger": ParagraphStyle(
            "empfaenger",
            fontName=SCHRIFT,
            fontSize=GRUND + 0.5,
            leading=14,
            textColor=hex_rgb(TEXT),
        ),
        "art": ParagraphStyle(
            "art",
            fontName=BETRAG_SCHRIFT,
            fontSize=17,
            leading=21,
            textColor=hex_rgb(AKZENT),
            spaceAfter=2,
        ),
        "kopf_daten": ParagraphStyle(
            "kopf_daten",
            fontName=SCHRIFT,
            fontSize=GRUND,
            leading=13,
            textColor=hex_rgb(SEKUNDAER),
            alignment=2,
        ),
        "absatz": ParagraphStyle(
            "absatz",
            fontName=SCHRIFT,
            fontSize=GRUND,
            leading=14,
            textColor=hex_rgb(TEXT),
            spaceAfter=7,
        ),
        "anrede": ParagraphStyle(
            "anrede",
            fontName=SCHRIFT,
            fontSize=GRUND,
            leading=14,
            textColor=hex_rgb(TEXT),
            spaceAfter=9,
        ),
        "ueberschrift": ParagraphStyle(
            "ueberschrift",
            fontName=BETRAG_SCHRIFT,
            fontSize=GRUND,
            leading=13,
            textColor=hex_rgb(AKZENT),
            spaceBefore=10,
            spaceAfter=5,
        ),
        "tab_kopf": ParagraphStyle(
            "tab_kopf",
            fontName=BETRAG_SCHRIFT,
            fontSize=8,
            leading=11,
            textColor=hex_rgb(SEKUNDAER),
        ),
        "tab_text": ParagraphStyle(
            "tab_text",
            fontName=SCHRIFT,
            fontSize=GRUND,
            leading=13,
            textColor=hex_rgb(TEXT),
        ),
        "tab_zahl": ParagraphStyle(
            "tab_zahl",
            fontName=SCHRIFT,
            fontSize=GRUND,
            leading=13,
            textColor=hex_rgb(TEXT),
            alignment=2,
        ),
        "tab_zahl_fett": ParagraphStyle(
            "tab_zahl_fett",
            fontName=BETRAG_SCHRIFT,
            fontSize=GRUND,
            leading=13,
            textColor=hex_rgb(TEXT),
            alignment=2,
        ),
        "summe": ParagraphStyle(
            "summe",
            fontName=BETRAG_SCHRIFT,
            fontSize=12,
            leading=16,
            textColor=hex_rgb(AKZENT),
            alignment=2,
        ),
        "klein": ParagraphStyle(
            "klein",
            fontName=SCHRIFT,
            fontSize=7.5,
            leading=10,
            textColor=hex_rgb(SEKUNDAER),
        ),
        "fuss": ParagraphStyle(
            "fuss",
            fontName=SCHRIFT,
            fontSize=7.5,
            leading=10,
            textColor=hex_rgb(SEKUNDAER),
            alignment=1,
        ),
        "platzhalter": ParagraphStyle(
            "platzhalter",
            fontName=SCHRIFT,
            fontSize=1,
            leading=1,
            spaceAfter=0,
            spaceBefore=0,
        ),
    }
