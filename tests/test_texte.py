"""Tests für Platzhalter in den Brieftexten."""

from __future__ import annotations

from faktur import texte


def test_bekannte_platzhalter_werden_ersetzt() -> None:
    """Setzt ein, was es kennt."""
    baustein = "Hallo {{Kunde_Anrede}}, hier {{Betrag}} von {{EigeneFirma}}."
    werte = {
        "Kunde_Anrede": "Herr Mustermann",
        "Betrag": "3.290,00 €",
        "EigeneFirma": "New Air Media Group",
    }
    ergebnis = texte.einsetzen(baustein, werte)
    assert ergebnis == (
        "Hallo Herr Mustermann, hier 3.290,00 € von New Air Media Group."
    )


def test_tippfehler_bleiben_sichtbar() -> None:
    """Lässt einen unbekannten Platzhalter stehen.

    Ein still verschwundener Name auf einem Brief ist schlimmer als einer,
    der nach einem Fehler aussieht.
    """
    baustein = "Hallo {{Kuude}}, hier ist Ihr Angebot."
    assert texte.einsetzen(baustein, {}) == "Hallo {{Kuude}}, hier ist Ihr Angebot."


def test_unbekannte_werden_gemeldet() -> None:
    """Findet die Namen, für die es keinen Wert gibt."""
    gefunden = texte.unbekannte("{{Kunde}} und {{Kuude}} und {{Zahl}}")
    assert gefunden == ["Kuude", "Zahl"]


def test_unbekannte_ohne_fehler() -> None:
    """Meldet nichts, wenn alle Namen stimmen."""
    assert texte.unbekannte("{{Kunde}} {{Betrag}}") == []


def test_anrede_kuerzt_den_vornamen() -> None:
    """Nimmt aus dem vollen Namen die Anrede."""
    assert texte.anrede("Herr Max Mustermann") == "Herr Mustermann"
    assert texte.anrede("Frau Anna Beispiel") == "Frau Beispiel"
    assert texte.anrede("Dr. med. Klaus Test") == "Dr. Test"
    assert texte.anrede("Max Mustermann") == "Max Mustermann"
    assert texte.anrede("") == ""


def test_absaetze_und_zeilen() -> None:
    """Trennt an Leerzeilen und an Zeilenumbrüchen."""
    text = "Hallo,\n\nvielen Dank.\n\nFreundliche Grüße"
    assert texte.absaetze(text) == ["Hallo,", "vielen Dank.", "Freundliche Grüße"]
    assert texte.zeilen("Hallo,\nviel Erfolg") == ["Hallo,", "viel Erfolg"]
    assert texte.absaetze("") == []
