"""Tests für die Pfadauflösung.

Dass die Daten neben dem Programm liegen und nicht irgendwo in der
Benutzerbibliothek, ist eine Zusage. Sie wird hier festgehalten.
"""

from __future__ import annotations

from pathlib import Path

from faktur import orte

WURZEL = Path(orte.__file__).resolve().parent.parent


def test_der_datenordner_liegt_neben_dem_programm() -> None:
    """Ohne alles: ``daten`` neben dem Paket, nicht im Benutzerordner."""
    assert orte.datenordner() == WURZEL / "daten"
    assert orte.datenordner().parent == WURZEL


def test_der_datenordner_ist_nicht_irgendwo_in_der_benutzerbibliothek() -> None:
    """Nicht ``~/Library`` und nicht ``~/.local``.

    Solche Pfade liegen an Orten, die man beim Suchen nicht erwartet.
    """
    start = str(orte.datenordner())
    verboten = ("/.faktur", "/Library/", "/.local/", "/.config/", "/.cache/")

    gefunden = [teil for teil in verboten if teil in start]
    assert gefunden == [], (
        f"Der Datenordner liegt an einem unerwarteten Ort: {gefunden}"
    )


def test_die_daten_dateien_liegen_im_datenordner() -> None:
    """Datenbank, Logo und Dokumente teilen sich einen Ordner."""
    ordner = orte.datenordner()

    assert orte.datenbank().parent == ordner
    assert orte.logo().parent == ordner
    assert orte.dokumente().parent == ordner


def test_die_dateinamen_bleiben_wie_sie_sind() -> None:
    """An den Namen hängt mehr als es aussieht.

    Die PDF bekommen ihren Namen aus dem Dokument, die Datenbank aus
    :mod:`faktur.db`. Verschiebt sich eine dieser Angaben, findet das
    Programm die vorhandenen Daten nicht mehr.
    """
    assert orte.datenbank().name == "faktur.db"
    assert orte.logo().name == "logo.png"
    assert orte.dokumente().name == "Dokumente"


def test_der_datenordner_ist_gleich_egal_wo_man_startet() -> None:
    """Der Pfad hängt nicht vom Arbeitsverzeichnis ab.

    Wer das Programm aus einem anderen Ordner startet, findet dieselben
    Daten. Sonst legt jeder Start eine eigene leere Datenbank an.
    """
    import os

    vorher = orte.datenordner()
    os.chdir("/tmp")  # noqa: PTH109
    try:
        assert orte.datenordner() == vorher
    finally:
        os.chdir(WURZEL)
