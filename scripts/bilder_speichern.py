#!/usr/bin/env python3
"""Zeichnet jeden Bereich des Fensters als PNG.

Qt kann ein Fenster von sich selbst abzeichnen lassen, mit `grab()`. Damit
entfällt der Umweg über den Bildschirmspeicher, den es in der
Terminaloberfläche geben musste und der eine private Schnittstelle war.

    .venv/bin/python scripts/bilder_speichern.py

Die Bilder landen in `bilder/`. Sie sind nicht Teil des Projekts, und der
Wächter `tests/test_repository.py` schlägt an, falls doch.
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from faktur import db  # noqa: E402
from faktur.gui.fenster import BEREICHE, Fenster  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

#: Wohin die Bilder kommen.
ZIEL = Path(__file__).resolve().parents[1] / "bilder"


def _datenbank(ordner: Path) -> object:
    """Legt eine Datenbank mit etwas Inhalt an.

    Args:
        ordner: Das Verzeichnis fuer die Datei.

    Returns:
        Die offene Verbindung.
    """
    from faktur import dateien

    verbindung = db.verbinden(ordner / "bilder.db")
    dateien.kunde_speichern(
        verbindung,
        {
            "firma": "Soundcheck GmbH",
            "ansprechpartner": "Max Mustermann",
            "strasse": "Tonstraße 12",
            "plz": "20457",
            "ort": "Hamburg",
            "email": "max@soundcheck.de",
            "telefon": "040 1234567",
        },
    )
    dateien.kunde_speichern(verbindung, {"firma": "Zeta Tonwerk", "ort": "Berlin"})
    dateien.kunde_speichern(verbindung, {"firma": "Alpha Klangstudio", "ort": "Köln"})

    # Zwei Belege: ein offener und ein bezahlter. Sonst steht in der
    # Dokumentenliste nur eine graue Flaeche, und man sieht nicht, ob die
    # Spalten und der Status stimmen.
    leistung = dateien.leistung_speichern(
        verbindung,
        {"bezeichnung": "Aufnahme Ton", "einheit": "Tag", "preis": "850"},
    )
    _beleg(
        verbindung,
        art="angebot",
        nummer="0199",
        kunde=1,
        datum="2026-09-14",
        gueltig_bis="2026-10-14",
        leistung=leistung,
    )
    rechnung = _beleg(
        verbindung,
        art="rechnung",
        nummer="0231",
        kunde=1,
        datum="2026-10-12",
        faellig="2026-09-01",
        leistung=leistung,
    )
    verbindung.execute(
        "UPDATE dokumente SET bezahlt_am = ? WHERE id = ?",
        ("2026-09-20", rechnung),
    )
    verbindung.commit()  # noqa: E501
    return verbindung


def _beleg(
    verbindung: object,
    art: str,
    nummer: str,
    kunde: int,
    datum: str,
    leistung: int,
    gueltig_bis: str = "",
    faellig: str = "",
) -> int:
    """Legt einen Beleg mit einer Position an.

    Args:
        verbindung: Die Datenbankverbindung.
        art: Angebot oder Rechnung.
        nummer: Die Projektnummer.
        kunde: Die Nummer des Kunden.
        datum: Das Belegdatum.
        leistung: Die Nummer der Leistung.
        gueltig_bis: Bei einem Angebot das Ablaufdatum.
        faellig: Bei einer Rechnung das Fälligkeitsdatum.

    Returns:
        Die Nummer des neuen Belegs.
    """
    from faktur import dateien

    return dateien.dokument_speichern(
        verbindung,
        {
            "art": art,
            "nummer": nummer,
            "kunde_id": kunde,
            "datum": datum,
            "gueltig_bis": gueltig_bis,
            "faellig": faellig,
        },
        [
            {
                "leistung_id": leistung,
                "bezeichnung": "Aufnahme Ton",
                "menge": 2,
                "einheit": "Tag",
                "preis": 850,
            }
        ],
    )


def speichere(fenster: Fenster, schluessel: str) -> Path:
    """Zeichnet einen Bereich und legt das Bild ab.

    Args:
        fenster: Das Fenster.
        schluessel: Der Bereich aus :data:`BEREICHE`.

    Returns:
        Der Pfad zum Bild.
    """
    fenster.gehe(schluessel)
    fenster.fenster.repaint()
    nummer = fenster.reihenfolge.index(schluessel) + 1
    ziel = ZIEL / f"{nummer:02d}_{schluessel}.png"
    fenster.fenster.grab().save(str(ziel))
    return ziel


def _editor(verbindung: object) -> Path:
    """Zeichnet das Dokumentfenster mit zwei Positionen.

    Das ist das Fenster, in dem die meiste Zeit verbracht wird. Wer es
    nie gesehen hat, glaubt nicht, dass es das gibt.

    Args:
        verbindung: Die Datenbankverbindung.

    Returns:
        Der Pfad zum Bild.
    """
    from faktur import dateien
    from faktur.gui.editor import EditorFenster

    leistungen = dateien.leistungen(verbindung)
    editor = EditorFenster(verbindung)
    for nummer in range(editor.kunde.count()):
        if editor.kunde.itemText(nummer):
            editor.kunde.setCurrentIndex(nummer)
            break
    editor.positionen.aus_leistung(leistungen[0])
    editor.positionen.aus_leistung(leistungen[1])
    editor.positionen.verschiebe(1, -1)
    editor.notiz.setText("Aufnahme fuer den neuen Kurzfilm")

    editor.show()
    app = QApplication.instance()
    if app is not None:
        app.processEvents()
    ziel = ZIEL / "08_editor.png"
    editor.grab().save(str(ziel))
    editor.close()
    return ziel


def main() -> int:
    """Zeichnet alle Bereiche und sagt, wo die Bilder liegen.

    Returns:
        ``0``, wenn alles gelungen ist.
    """
    ordner = Path(tempfile.mkdtemp(prefix="faktur_bilder_"))
    app = QApplication.instance() or QApplication(sys.argv)

    verbindung = _datenbank(ordner)
    fenster = Fenster(verbindung)
    fenster.zeige()
    app.processEvents()

    if ZIEL.exists():
        shutil.rmtree(ZIEL)
    ZIEL.mkdir(parents=True)

    geschrieben: list[Path] = []
    for schluessel, _titel, _kuerzel in BEREICHE:
        geschrieben.append(speichere(fenster, schluessel))
        app.processEvents()

    fenster.fenster.close()
    geschrieben.append(_formular(verbindung))
    geschrieben.append(_editor(verbindung))
    shutil.rmtree(ordner, ignore_errors=True)

    print(f"{len(geschrieben)} Bilder in {ZIEL}")  # noqa: T201
    for pfad in geschrieben:
        print(f"  {pfad.name}")  # noqa: T201
    return 0


def _formular(verbindung: object) -> Path:
    """Zeichnet das Blatt fuer einen neuen Kunden.

    Das Blatt ist ein eigenes Fenster und taucht in keinem der
    Bereichsbilder auf. Wer es nie gesehen hat, glaubt nicht, dass es
    da ist.

    Args:
        verbindung: Die Datenbankverbindung.

    Returns:
        Der Pfad zum Bild.
    """
    from faktur.gui.aktionen import KUNDENFELDER
    from faktur.gui.formular import Formular

    blatt = Formular(verbindung, "Neuer Kunde", KUNDENFELDER, {})
    blatt.show()
    app = QApplication.instance()
    if app is not None:
        app.processEvents()
    ziel = ZIEL / "07_formular.png"
    blatt.grab().save(str(ziel))
    blatt.close()
    return ziel


if __name__ == "__main__":
    raise SystemExit(main())
