"""Tests für das Aussehen der PDF.

Hier wird geprüft, was auf dem Dokument steht und wo. Der Aufbau des
Dokuments steckt in ``tests/test_pdf.py``.

Ein Teil dieser Tests benutzt eine Attrappe: eine Leinwand, die statt zu
zeichnen aufschreibt, was ihr gesagt wurde. Nur so lässt sich prüfen, wo
das Logo genau sitzt — im fertigen Dokument steckt das in einem Bildstrom,
den man nicht ohne Mühe auseinanderbaut.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from faktur import einstellungen, pdf
from reportlab.lib.units import mm


class Attrappe:
    """Eine Leinwand, die festhält, was gezeichnet werden soll.

    Attributes:
        bilder: Die Aufrufe von ``drawImage``.
        texte: Die Texte mit der Art des Aufrufs.
        schrift: Die zuletzt gesetzte Größe in Punkt.
    """

    def __init__(self) -> None:
        """Legt die Strichliste an."""
        self.bilder: list[dict] = []
        self.texte: list[tuple[str, str]] = []
        self.schrift: float | None = None

    def saveState(self) -> None:  # noqa: N802 - reportlab schreibt so
        """Beginnt einen Zustand."""

    def restoreState(self) -> None:  # noqa: N802 - reportlab schreibt so
        """Beendet einen Zustand."""

    def setFont(self, _name: str, size: float) -> None:  # noqa: N802
        """Setzt die Schrift.

        Args:
            _name: Der Name der Schrift.
            size: Die Größe in Punkt.
        """
        self.schrift = size

    def setFillColor(self, _farbe: object) -> None:  # noqa: N802
        """Setzt die Füllfarbe.

        Args:
            _farbe: Die Farbe.
        """

    def getPageNumber(self) -> int:  # noqa: N802 - reportlab schreibt so
        """Nennt die Seitenzahl.

        Returns:
            Immer die erste Seite.
        """
        return 1

    def drawImage(self, pfad, x, y, **kwargs) -> None:  # noqa: N802
        """Schreibt ein Bild.

        Args:
            pfad: Der Pfad der Bilddatei.
            x: Die linke Kante.
            y: Die untere Kante.
            kwargs: Breite, Höhe und alles andere.
        """
        self.bilder.append({"pfad": str(pfad), "x": x, "y": y, **kwargs})

    def drawString(self, _x, _y, text) -> None:  # noqa: N802
        """Schreibt einen Text von links.

        Args:
            _x: Die linke Kante.
            _y: Die Grundlinie.
            text: Der Text.
        """
        self.texte.append(("links", str(text)))

    def drawRightString(self, _x, _y, text) -> None:  # noqa: N802
        """Schreibt einen Text rechtsbündig.

        Args:
            _x: Die rechte Kante.
            _y: Die Grundlinie.
            text: Der Text.
        """
        self.texte.append(("rechts", str(text)))


def zeichne(verbindung: sqlite3.Connection, art: str) -> Attrappe:
    """Lässt die Fusszeile einmal auf eine Attrappe zeichnen.

    Args:
        verbindung: Die Datenbankverbindung.
        art: Die Dokumentart.

    Returns:
        Die Attrappe mit allem, was gezeichnet wurde.
    """
    attrappe = Attrappe()
    pdf.deko(verbindung, art)(attrappe, None)
    return attrappe


def logo_anlegen(ziel: Path, breite: int = 800, hoehe: int = 400) -> Path:
    """Erzeugt ein Bild mit bekanntem Seitenverhältnis.

    Args:
        ziel: Wohin die Datei soll.
        breite: Die Breite in Pixel.
        hoehe: Die Höhe in Pixel.

    Returns:
        Der Pfad der erzeugten Datei.
    """
    from PIL import Image

    Image.new("RGB", (breite, hoehe), (80, 40, 128)).save(ziel)
    return ziel


@pytest.fixture
def mit_logo(verbindung: sqlite3.Connection, tmp_path: Path) -> sqlite3.Connection:
    """Legt ein Logo in die Datenbank.

    Args:
        verbindung: Die Datenbankverbindung.
        tmp_path: Das temporäre Verzeichnis.

    Returns:
        Dieselbe Verbindung, jetzt mit Logo.
    """
    einstellungen.logo_uebernehmen(
        verbindung, logo_anlegen(tmp_path / "quelle.png"), tmp_path
    )
    return verbindung


# --------------------------------------------------------------------------
# Das Logo
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("groesse", "breite_mm"),
    [("klein", 16.0), ("mittel", 22.0), ("gross", 32.0)],
)
def test_die_logogroesse_wird_gesetzt(
    mit_logo: sqlite3.Connection, groesse: str, breite_mm: float
) -> None:
    """Jede der drei Grössen ergibt genau ihre Breite.

    Args:
        mit_logo: Die Verbindung mit Logo.
        groesse: Der Name der Grösse.
        breite_mm: Die erwartete Breite in Millimeter.
    """
    einstellungen.speichere(mit_logo, "logo_groesse", groesse)

    bild = zeichne(mit_logo, "rechnung").bilder[0]

    assert bild["width"] == pytest.approx(breite_mm * mm, abs=0.01)


def test_das_seitenverhaeltnis_bleibt_erhalten(
    mit_logo: sqlite3.Connection,
) -> None:
    """Die Höhe folgt dem echten Verhältnis der Datei.

    Ein hohes Logo darf nicht gestreckt werden, nur weil es eine feste
    Breite bekommen hat.

    Args:
        mit_logo: Die Verbindung mit Logo.
    """
    bild = zeichne(mit_logo, "rechnung").bilder[0]

    # Das erzeugte Bild ist 800 zu 400, also 2 zu 1.
    assert bild["height"] == pytest.approx(bild["width"] / 2, abs=0.01)


def test_ein_breites_logo_bekommt_eine_kleinere_hoehe(
    verbindung: sqlite3.Connection, tmp_path: Path
) -> None:
    """Dasselbe Seitenverhältnis wird wirklich gelesen und nicht geraten.

    Args:
        verbindung: Die Verbindung.
        tmp_path: Das temporäre Verzeichnis.
    """
    einstellungen.logo_uebernehmen(
        verbindung, logo_anlegen(tmp_path / "quelle.png", 800, 200), tmp_path
    )

    bild = zeichne(verbindung, "rechnung").bilder[0]

    assert bild["height"] == pytest.approx(bild["width"] / 4, abs=0.01)


def test_das_logo_steht_immer_gleich_weit_oben(mit_logo: sqlite3.Connection) -> None:
    """Der Abstand zur Oberkante hängt nicht an der Grösse.

    Genau das war vorher geraten und stimmte nicht: Das eigene Logo hat
    2.07 zu 1, geraten wurde mit 2.86 zu 1. Bei einer grösseren Variante
    wäre der Fehler mitgewachsen.

    Args:
        mit_logo: Die Verbindung mit Logo.
    """
    kanten = []

    for groesse in ("klein", "mittel", "gross"):
        einstellungen.speichere(mit_logo, "logo_groesse", groesse)
        bild = zeichne(mit_logo, "rechnung").bilder[0]
        kanten.append(pdf.A4[1] - (bild["y"] + bild["height"]))

    assert kanten[0] == pytest.approx(kanten[1], abs=0.01)
    assert kanten[1] == pytest.approx(kanten[2], abs=0.01)
    assert kanten[0] == pytest.approx(pdf.LOGO_ABSTAND, abs=0.01)


def test_ohne_logo_wird_auch_keines_gezeichnet(verbindung: sqlite3.Connection) -> None:
    """Das Kästchen entscheidet, nicht die Grösse.

    Args:
        verbindung: Die Verbindung.
    """
    einstellungen.speichere(verbindung, "ausgabe_rechnung", "firma")

    assert zeichne(verbindung, "rechnung").bilder == []


def test_auf_dem_angebot_gilt_die_eigene_auswahl(
    verbindung: sqlite3.Connection,
) -> None:
    """Angebot und Rechnung sind unabhängig.

    Args:
        verbindung: Die Verbindung.
    """
    einstellungen.speichere(verbindung, "ausgabe_rechnung", "firma,logo")
    einstellungen.speichere(verbindung, "ausgabe_angebot", "firma")

    assert len(zeichne(verbindung, "rechnung").bilder) == 1
    assert zeichne(verbindung, "angebot").bilder == []


def test_eine_kaputte_bilddatei_ruft_nichts_hervor(
    verbindung: sqlite3.Connection, tmp_path: Path
) -> None:
    """Kein Bild, aber auch kein Absturz.

    Args:
        verbindung: Die Verbindung.
        tmp_path: Das temporäre Verzeichnis.
    """
    kaputt = tmp_path / "kaputt.png"
    kaputt.write_text("das ist kein Bild", encoding="utf-8")
    einstellungen.logo_uebernehmen(verbindung, kaputt, tmp_path)

    assert zeichne(verbindung, "rechnung").bilder == []


@pytest.mark.parametrize(
    ("kaputt", "soll"),
    [("", "mittel"), ("   ", "mittel"), ("riesig", "mittel"), ("sehr klein", "mittel")],
)
def test_eine_unbekannte_logogroesse_ist_die_standardgroesse(
    verbindung: sqlite3.Connection, kaputt: str, soll: str
) -> None:
    """Ein Tippfehler darf das Dokument nicht verschieben.

    Args:
        verbindung: Die Verbindung.
        kaputt: Der gespeicherte Wert.
        soll: Der Name, der danach gilt.
    """
    einstellungen.speichere(verbindung, "logo_groesse", kaputt)

    assert pdf.logo_groesse(verbindung) == soll


@pytest.mark.parametrize("geschrieben", ["GROSS", "Gross", " gross "])
def test_gross_und_klein_werden_akzeptiert(
    verbindung: sqlite3.Connection, geschrieben: str
) -> None:
    """ "GROSS" ist derselbe Wert wie "gross".

    Wer es im Terminal eintippt, hat keine Lust auf Groß- und Kleinschreibung.

    Args:
        verbindung: Die Verbindung.
        geschrieben: Der Wert, wie ihn jemand getippt haben könnte.
    """
    einstellungen.speichere(verbindung, "logo_groesse", geschrieben)

    assert pdf.logo_groesse(verbindung) == "gross"


# --------------------------------------------------------------------------
# Die Fußzeile
# --------------------------------------------------------------------------


def test_die_fusszeile_hat_firma_und_seitenzahl(verbindung: sqlite3.Connection) -> None:
    """So sieht sie von heute aus.

    Args:
        verbindung: Die Verbindung.
    """
    einstellungen.speichere(verbindung, "firma", "New Air Media Group")

    texte = zeichne(verbindung, "rechnung").texte

    assert ("links", "New Air Media Group") in texte
    assert ("rechts", "Seite 1") in texte


def test_ohne_firmenzeile_bleibt_nur_die_seitenzahl(
    verbindung: sqlite3.Connection,
) -> None:
    """Ohne Firmenzeile steht nur die Seitenzahl unten.

    Args:
        verbindung: Die Verbindung.
    """
    einstellungen.speichere(verbindung, "firma", "New Air Media Group")
    einstellungen.speichere(verbindung, "ausgabe_rechnung", "seitenzahl")

    assert zeichne(verbindung, "rechnung").texte == [("rechts", "Seite 1")]


def test_ohne_seitenzahl_bleibt_nur_die_firmenzeile(
    verbindung: sqlite3.Connection,
) -> None:
    """Manche wollen auf der Rechnung keine Seitenzahl.

    Args:
        verbindung: Die Verbindung.
    """
    einstellungen.speichere(verbindung, "firma", "New Air Media Group")
    einstellungen.speichere(verbindung, "ausgabe_rechnung", "firmenzeile")

    assert zeichne(verbindung, "rechnung").texte == [("links", "New Air Media Group")]


def test_eine_leere_fusszeile_ist_echt_leer(verbindung: sqlite3.Connection) -> None:
    """Beide abgeschaltet heisst: nichts unten.

    Args:
        verbindung: Die Verbindung.
    """
    einstellungen.speichere(verbindung, "ausgabe_rechnung", "firma")

    assert zeichne(verbindung, "rechnung").texte == []


def test_die_fusszeile_waechst_mit_der_textgroesse(
    verbindung: sqlite3.Connection,
) -> None:
    """Sie wird auf die Leinwand gezeichnet und hat also keinen Stil.

    Ohne eigene Anpassung würde sie bei „gross" kleiner wirken als der
    Text und bei „klein" grösser.

    Args:
        verbindung: Die Verbindung.
    """
    gemessen = {}

    for name in ("klein", "normal", "gross"):
        einstellungen.speichere(verbindung, "text_groesse", name)
        gemessen[name] = zeichne(verbindung, "rechnung").schrift

    assert gemessen["klein"] < gemessen["normal"] < gemessen["gross"]
    assert gemessen["normal"] == pytest.approx(7.5, abs=0.01)
