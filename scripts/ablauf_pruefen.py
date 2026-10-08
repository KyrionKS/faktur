#!/usr/bin/env python3
"""Geht den ganzen Weg durch die Oberfläche.

Kunde anlegen, Angebot bauen, PDF schreiben. Alles über Tastendrücke, wie
es der Benutzer tun würde. Damit lässt sich prüfen, ob die Bildschirme in
der richtigen Reihenfolge kommen und nichts hängen bleibt.
"""

from __future__ import annotations

import asyncio
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from faktur.app import FakturApp  # noqa: E402


def bild(app: FakturApp) -> str:
    """Liest das aktuelle Bild aus dem Speicher.

    Args:
        app: Die laufene App.

    Returns:
        Jede Bildschirmzeile als Text.
    """
    return "\n".join(
        "".join(teil.text for teil in streifen)
        for streifen in app.screen._compositor.render_strips()
    )


async def durchlauf() -> int:
    """Tippt sich durch die App und prüft nach jedem Schritt.

    Returns:
        ``0``, wenn alles geklappt hat, sonst die Anzahl der Fehler.
    """
    ordner = Path(tempfile.mkdtemp(prefix="faktur_ablauf_"))
    fehler = 0
    nonlocal_fehler = [0]
    app = FakturApp(ordner / "ablauf.db")

    # Die App legt ihre PDF in den echten Rechnungsordner im Heimverzeichnis.
    # Beim Prüfen gehört das in einen Ordner, der danach weg kann, sonst
    # landen Testdokumente zwischen den echten Rechnungen.
    from faktur import db as db_modul

    db_modul.DOKUMENTE = ordner / "Dokumente"

    async with app.run_test(size=(100, 34)) as pilot:

        async def tippen(*tasten: str) -> None:
            """Drückt Tasten und wartet, bis das Bild steht.

            Args:
                tasten: Die Tasten in Reihenfolge.
            """
            for taste in tasten:
                await pilot.press(taste)
            await pilot.pause()

        async def feld_ausfuellen(werte: list[str], felder: int) -> None:
            """Tippt ein Formular durch und sendet es ab.

            Args:
                werte: Die Werte für die ersten Felder.
                felder: Wie viele Felder das Formular hat.
            """
            for wert in werte:
                await tippen(*wert)
                await tippen("enter")
            for _ in range(max(0, felder - len(werte))):
                await tippen("enter")

        async def durch_das_formular(felder: int) -> None:
            """Bestätigt jedes Feld mit Enter und sendet ab.

            Die Felder sind schon vorbelegt. Genau das ist die Zusage der
            App: Enter genügt. Ein Test, der Werte hineintippt, würde sie
            an den vorhandenen Text anhängen und prüfte etwas anderes.

            Args:
                felder: Wie viele Felder das Formular hat.
            """
            for _ in range(felder):
                await tippen("enter")

        def pruefe(bezeichnung: str, erwartet: str) -> None:
            """Prüft, ob ein Text im Bild steht.

            Args:
                bezeichnung: Was geprüft wird.
                erwartet: Der Text, der dastehen muss.
            """
            nonlocal fehler
            if erwartet in bild(app):
                print(f"  ok     {bezeichnung}")
            else:
                fehler += 1
                print(f"  FEHLT  {bezeichnung}: {erwartet!r}")
                print("  --- Bild ---")
                for zeile in bild(app).splitlines():
                    if zeile.strip():
                        print(f"  | {zeile.rstrip()}")

        print("Ablauf durch die Oberfläche")
        pruefe("Startseite", "Angebot erstellen")

        # --- Kunde anlegen
        await tippen("3")
        pruefe("Kundenliste", "Kunden")
        await tippen("n")
        pruefe("Kundenformular", "Ansprechpartner")

        # Der Kunde ist neu, also wird jedes Feld getippt.
        await feld_ausfuellen(
            [
                "Soundcheck GmbH",
                "Herr Max Mustermann",
                "Klangstrasse 3",
                "10115",
                "Berlin",
            ],
            felder=8,
        )
        pruefe("Kunde gespeichert", "Soundcheck GmbH")

        # --- Angebot bauen
        await tippen("escape")
        await tippen("1")
        pruefe("Angebot, Kunde wählen", "Schritt 1 von 3")
        await tippen("enter")
        pruefe("Positionen sammeln", "Schritt 2 von 3")

        await tippen("enter")  # "Position aus der Preisliste"
        pruefe("Preisliste", "Aufnahme Ton")
        await tippen("enter")  # erste Leistung
        pruefe("Position eintragen", "Bezeichnung")

        # Die Leistung ist schon eingetragen, Menge und Preis stimmen.
        await durch_das_formular(4)
        pruefe("Position übernommen", "Aufnahme Ton")

        # Rabatt als eigene Position. Die Summe sinkt um genau den Betrag.
        # Nach dem Neuausbau steht der Cursor auf der ersten Position, der
        # Rabattpunkt ist der dritte.
        await tippen("down", "down")
        pruefe("Rabatt im Menue", "Rabatt eintragen")
        await tippen("enter")
        pruefe("Rabatt-Eingabe", "das Minus setzt das Programm")
        for zeichen in "300":
            await tippen(zeichen)
        await tippen("enter", "enter")
        pruefe("Rabatt übernommen", "-300,00 €")

        await tippen("end")
        await tippen("enter")  # "Fertig"
        pruefe("Kontrolle", "Schritt 3 von 3")
        # Die Position wurde mit Menge 1 übernommen: 850 minus 300.
        pruefe("Summe mit Rabatt", "550,00 €")

        await durch_das_formular(4)
        pruefe("Angebot gespeichert", "Gespeichert")

        # --- Dokumente und PDF
        await tippen("escape", "escape", "escape")
        await tippen("6")
        pruefe("Dokumentenliste", "Angebot")
        await tippen("enter")
        pruefe("PDF geschrieben", "Geschrieben")

        geschrieben = list((ordner / "Dokumente").glob("*.pdf"))
        if geschrieben:
            print(f"  ok     PDF im Prüfordner: {geschrieben[0].name}")
        else:
            nonlocal_fehler[0] += 1
            print("  FEHLT  PDF im Prüfordner")

        # --- Angebot in Rechnung umwandeln. Steht die Auswahl auf einem
        # Angebot, heisst ``r`` abrechnen statt eine neue anfangen.
        await tippen("home")
        await tippen("r")
        pruefe("Umwandlung, Schritt 3", "Schritt 3 von 3")
        pruefe("Positionen übernommen", "Aufnahme Ton")
        await durch_das_formular(4)
        pruefe("Rechnung gespeichert", "Gespeichert")

        await tippen("escape", "escape")
        await tippen("6")
        pruefe("Rechnung in der Liste", "Rechnung")

        # --- Preisliste
        await tippen("escape")
        await tippen("4")
        pruefe("Preisliste", "Mischung und Mastering")

        # --- Stammdaten
        await tippen("escape")
        await tippen("7")
        pruefe("Stammdaten", "Firma und Bank")

        # Der Brieftext ist mehrzeilig. Das war der Grund für den eigenen
        # Editor: ein einzeiliges Eingabefeld klappt die Absätze zusammen.
        await tippen("3")
        pruefe("Brieftext-Editor", "Text für Angebote")
        pruefe("Zeilennummern", " 1 ")

        await tippen("ctrl+home")
        for zeile in ("Hallo {{Kunde_Anrede}},", "", "Angebot für Ihr Projekt."):
            if zeile:
                await tippen(*zeile)
            await tippen("enter")
        await tippen("ctrl+s")
        pruefe("Brieftext gespeichert", "Gespeichert")

        gespeichert = app.db.execute(
            "SELECT wert FROM einstellungen WHERE schluessel = 'text_angebot'"
        ).fetchone()
        if gespeichert and "Angebot für Ihr Projekt." in gespeichert["wert"]:
            print("  ok     Absätze unbeschädigt gespeichert")
        else:
            nonlocal_fehler[0] += 1
            print("  FEHLT  Absätze unbeschädigt gespeichert")

        # --- Aussehen der PDF
        # Grösse ändern und einen Block abschalten. Beides wird sofort in
        # die Datenbank geschrieben, das prüft der Lauf danach direkt.
        await tippen("escape")
        await tippen("7")
        pruefe("Stammdaten", "Firma und Bank")
        await tippen("6")
        pruefe("Aussehen", "Logogröße")
        pruefe("Absender", "Firmenname")
        pruefe("Fußzeile", "Seitenzahl")

        await tippen("down")
        await tippen("left")
        pruefe("Logogröße kleiner", "klein")

        # Von der Logogröße bis zur Anschrift sind es sechs Plätze:
        # Schriftgröße, Nummer, Firmenname, Zusatz, Anschrift.
        for _ in range(5):
            await tippen("down")
        await tippen("space")
        pruefe("Anschrift abgeschaltet", "○")

        gespeichert = app.db.execute(
            "SELECT wert FROM einstellungen WHERE schluessel = 'logo_groesse'"
        ).fetchone()
        if gespeichert and gespeichert["wert"] == "klein":
            print("  ok     Logogröße gespeichert")
        else:
            nonlocal_fehler[0] += 1
            print("  FEHLT  Logogröße gespeichert")

        ausgabe = app.db.execute(
            "SELECT wert FROM einstellungen WHERE schluessel = 'ausgabe_angebot'"
        ).fetchone()
        if ausgabe and "anschrift" not in ausgabe["wert"].split(","):
            print("  ok     abgeschalteter Block gespeichert")
        else:
            nonlocal_fehler[0] += 1
            print("  FEHLT  abgeschalteter Block gespeichert")

        # Auf die Rechnung wechseln. Dort muss die Bankverbindung stehen,
        # auf dem Angebot nicht.
        await tippen("home")
        await tippen("right")
        pruefe("auf der Rechnung", "Bank, IBAN, BIC")

        # --- Offene Forderungen
        # Eine Rechnung anlegen, sie muss in der Liste stehen und wieder
        # verschwinden, wenn sie als bezahlt vermerkt ist.
        await tippen("escape")
        await tippen("escape")
        await tippen("escape")
        await tippen("5")
        pruefe("Offene Forderungen", "Rechnung")
        pruefe("Summe", "Offen:")

        await tippen("b")
        pruefe("nach dem Markieren leer", "0 Rechnungen")

        await tippen("escape")
        await tippen("escape")
        pruefe("zurueck im Menue", "Beenden")

    app.db.close()
    shutil.rmtree(ordner, ignore_errors=True)

    fehler += nonlocal_fehler[0]
    print()
    print("Alles in Ordnung." if fehler == 0 else f"{fehler} Prüfungen fehlgeschlagen.")
    return fehler


if __name__ == "__main__":
    raise SystemExit(asyncio.run(durchlauf()))
