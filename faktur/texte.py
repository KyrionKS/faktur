"""Platzhalter in den Textbausteinen einsetzen.

Ein Tippfehler in einem Platzhalter bleibt sichtbar. ``{{Kuude}}`` steht als
``{{Kuude}}`` auf der PDF, statt still zu verschwinden — ein Brief, in dem
ein Name fehlt, ist peinlicher als einer, der nach einem Fehler aussieht.
"""

from __future__ import annotations

import re

#: Wie ein Platzhalter geschrieben wird.
MUSTER = r"\{\{(\w+)\}\}"

#: Alle Namen, die es gibt.
PLATZHALTER = (
    "Kunde",
    "Kunde_Anrede",
    "Ansprechpartner",
    "Nummer",
    "Datum",
    "Faellig",
    "Gueltig_bis",
    "Betrag",
    "Anzahl_Positionen",
    "EigeneFirma",
    "EigeneFirma_voll",
    "Bank",
    "IBAN",
)


def unbekannte(text: str) -> list[str]:
    """Sucht die Platzhalter, für die es keinen Wert gibt.

    Args:
        text: Der Baustein mit den Platzhaltern.

    Returns:
        Die Namen, in der Reihenfolge des Auftretens, ohne Doppelungen.
    """
    gefunden: list[str] = []
    for name in re.findall(MUSTER, text or ""):
        if name not in PLATZHALTER and name not in gefunden:
            gefunden.append(name)
    return gefunden


def einsetzen(text: str, werte: dict[str, str]) -> str:
    """Ersetzt die bekannten Platzhalter.

    Args:
        text: Der Baustein mit den Platzhaltern.
        werte: Die Werte je Name.

    Returns:
        Der Text mit eingesetzten Werten. Unbekannte Platzhalter bleiben
        stehen.
    """
    if not text:
        return ""

    def ersetzen(treffer: re.Match[str]) -> str:
        name = treffer.group(1)
        if name in werte:
            return str(werte[name])
        return treffer.group(0)

    return re.sub(MUSTER, ersetzen, text)


def anrede(name: str) -> str:
    """Kürzt einen vollen Namen auf die Anrede.

    Aus ``Herr Max Mustermann`` wird ``Herr Mustermann``. So kann der Baustein
    frei formuliert werden, ohne in Höflichkeitsformeln zu verfallen.

    Args:
        name: Der Name aus der Kundendatenbank.

    Returns:
        Die gekürzte Anrede, oder der Name, wenn keine Titelfehler erkannt
        wird.
    """
    if not name:
        return ""

    titel = ("Herr", "Frau", "Divers", "Prof", "Dr")
    woerter = name.replace(",", " ").split()
    if not woerter:
        return ""

    # "Herr Max Mustermann" -> Titel suchen, dann den letzten Namen nehmen.
    for stelle, wort in enumerate(woerter):
        if wort.rstrip(".") in titel:
            nachname = woerter[-1] if len(woerter) > stelle + 1 else ""
            return f"{wort} {nachname}".strip()

    return " ".join(woerter)


def absaetze(text: str) -> list[str]:
    """Teilt einen Text an Leerzeilen in Absätze.

    Args:
        text: Der mehrzeilige Text.

    Returns:
        Die Absätze ohne Leerzeilen dazwischen.
    """
    return [absatz.strip() for absatz in (text or "").split("\n\n") if absatz.strip()]


def zeilen(text: str) -> list[str]:
    """Teilt einen Absatz an Zeilenumbrüchen.

    Args:
        text: Der Absatz.

    Returns:
        Die Zeilen ohne Leerzeilen.
    """
    return [zeile.rstrip() for zeile in (text or "").split("\n") if zeile.strip()]
