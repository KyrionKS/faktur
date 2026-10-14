"""Tests für den Editor der Brieftexte.

Der Punkt ist nicht die Oberfläche, sondern das Verhalten: Ein mehrzeiliger
Text muss unbeschädigt gespeichert und wieder geladen werden. Mit einem
einzeiligen Eingabefeld ginge das nicht, weil die Absätze in einer Zeile
landen.
"""

from __future__ import annotations

import sqlite3

from faktur import einstellungen, texte


def _text_mit_absätzen() -> str:
    """Baut einen Text mit mehreren Absätzen.

    Returns:
        Der Text mit Leerzeilen dazwischen.
    """
    return (
        "Hallo {{Kunde_Anrede}},\n"
        "\n"
        "vielen Dank für Ihre Anfrage!\n"
        "\n"
        "Freundliche Grüße\n"
        "{{EigeneFirma}}"
    )


def test_absaetze_bleiben_beim_speichern_erhalten(
    verbindung: sqlite3.Connection,
) -> None:
    """Leerzeilen und Zeilenumbrüche überstehen den Weg in die Datenbank.

    Args:
        verbindung: Die Testdatenbank.
    """
    text = _text_mit_absätzen()
    einstellungen.speichere(verbindung, "text_angebot", text)

    geladen = einstellungen.baustein(verbindung, "angebot")

    assert geladen == text
    # Vier Absätze, also drei Trenner. Zwei davon sind echte Leerzeilen,
    # der letzte ist ein einfacher Umbruch vor der Signatur.
    assert geladen.count("\n\n") == 2
    assert geladen.split("\n")[0] == "Hallo {{Kunde_Anrede}},"


def test_alle_absatzarten_kommen_vor(verbindung: sqlite3.Connection) -> None:
    """Auch ein Text ganz ohne Leerzeilen und ein Text ganz aus Leerzeilen.

    Args:
        verbindung: Die Testdatenbank.
    """
    einstellungen.speichere(verbindung, "text_rechnung", "Einzeilig, ohne Absatz.")
    assert einstellungen.baustein(verbindung, "rechnung") == "Einzeilig, ohne Absatz."

    leer = "\n\n\n"
    einstellungen.speichere(verbindung, "text_rechnung", leer)
    assert einstellungen.baustein(verbindung, "rechnung") == leer


def test_platzhalter_werden_im_gespeicherten_text_gefunden() -> None:
    """Die unbekannten Namen lassen sich im Rohtext bestimmen."""
    text = "Hallo {{Kuude}}, Ihre Rechnung {{Betrag}} ist da. Bis bald, {{Gruss}}"
    gefunden = texte.unbekannte(text)

    assert gefunden == ["Kuude", "Gruss"]
