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

    # 44 Zeilen, damit der ganze Bildschirm im Bild ist. Mit 34 schob
    # der Fokus beim Kontrollschirm die Hinweiszeile aus dem Bild, und der
    # Lauf pruefte an einer Zeile, die der Benutzer in diesem Fenster
    # schlicht nicht sieht.
    async with app.run_test(size=(100, 44)) as pilot:

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

        # --- Zweiter Kunde, und zwar absichtlich weiter unten im Alphabet.
        # Ohne ihn ist die Suche im ersten Schritt nicht pruefbar: Es gibt
        # nur einen Kunden, und bei einem einzigen kann die Suche gar nicht
        # danebenliegen.
        await tippen("n")
        await feld_ausfuellen(
            [
                "Tonstudio Nordwind",
                "Frau Erika Beispiel",
                "Hafenstrasse 9",
                "20457",
                "Hamburg",
            ],
            felder=8,
        )
        pruefe("Zweiter Kunde gespeichert", "Tonstudio Nordwind")

        # --- Suchen auf der Kundenliste, und dann benutzen. Das ist der
        # Fehler, der bis 0.8.2 keiner bemerkt hat: Gefiltert wurden nur
        # die Zeilen der Tabelle, die Liste selbst blieb ganz. Wer den
        # zweiten Kunden suchte, sah ihn und bekam den ersten.
        await tippen("suche")
        for zeichen in "nordw":
            await tippen(zeichen)
        pruefe("Kundensuche auf der Liste", "1 von 2 passen")
        await tippen("tab")  # aus dem Suchfeld in die Liste
        await tippen("delete")
        # Gefragt wird nach dem GESEHENEN Kunden. Steht hier der andere,
        # wäre beim Bestätigen ein fremder Kunde samt Dokumenten weg.
        pruefe("Löschen fragt nach dem gesehenen Kunden", "Tonstudio Nordwind")
        await tippen("n")  # abbrechen
        # ``suche`` zuerst: Nach der Frage liegt der Cursor auf der Liste,
        # und ein ``escape`` von dort springt aus dem Bildschirm heraus,
        # statt das Suchfeld zu leeren.
        await tippen("suche")
        await tippen("escape")  # Suchfeld leeren
        pruefe("Kundenliste wieder voll", "Soundcheck GmbH")
        # Und wieder aus dem Feld hinaus: Solange der Cursor dort steht,
        # landet die naechste Zahl im Suchfeld statt im Menue.
        await tippen("tab")

        # --- Angebot bauen
        await tippen("escape")
        await tippen("1")
        pruefe("Angebot, Kunde wählen", "Schritt 1 von 3")

        # Der Kunde wird **gesucht**, nicht geblaettert. Beachtet wird das
        # Ergebnis: Ist "Tonstudio Nordwind" der Filter, muss genau dieser
        # Kunde im Angebot stehen — nachgewiesen spaeter am Dateinamen des
        # PDF. Genau daran ginge es schief, wenn nach dem Filtern der erste
        # Eintrag der ungefilterten Liste genommen wuerde.
        await tippen("suche")
        for zeichen in "nordwind":
            await tippen(zeichen)
        pruefe("Kundensuche greift", "1 von 2 passen")
        # ``tab`` erst: Solange der Cursor im Suchfeld steht, nimmt ``enter``
        # das Feld und nicht die Liste.
        await tippen("tab", "enter")
        pruefe("Positionen sammeln", "Schritt 2 von 3")

        await tippen("enter")  # "Position aus der Preisliste"
        pruefe("Preisliste", "Aufnahme Ton")

        # Auch die Leistung wird gesucht. "Aufnahme Ton" ist die erste der
        # fuenf, das taugt als Probe nicht — der Filter muesste gar nichts
        # aendern. Gesucht wird deshalb nach der dritten, damit ein Fehler
        # sofort auffaellt.
        await tippen("suche")
        for zeichen in "sprecher":
            await tippen(zeichen)
        pruefe("Leistungssuche greift", "1 von 5 passen")
        await tippen("tab", "enter")  # siehe oben: erst aus dem Suchfeld
        pruefe("Position eintragen", "Bezeichnung")

        # Die Leistung ist schon eingetragen, Menge und Preis stimmen.
        await durch_das_formular(4)
        pruefe("Position übernommen", "Sprecherstimme")

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
        # Die gesuchte Leistung wurde mit Menge 1 übernommen: 120 minus 300.
        pruefe("Summe mit Rabatt", "-180,00 €")

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

        # Der Dateiname traegt den Kundennamen. Damit ist zum ersten Mal
        # belegt, dass im Dokument der Kunde steht, den man **gesehen** hat —
        # der Kundenschritt wird gesucht, und ein Index auf die ungefilterte
        # Liste wuerde hier den falschen Namen schreiben.
        if geschrieben and "Tonstudio Nordwind" not in geschrieben[0].name:
            nonlocal_fehler[0] += 1
            print("  FEHLT  gesuchter Kunde im Angebotsnamen")
        elif geschrieben:
            print("  ok     gesuchter Kunde im Angebotsnamen")

        # --- Angebot in Rechnung umwandeln. Steht die Auswahl auf einem
        # Angebot, heisst ``r`` abrechnen statt eine neue anfangen.
        await tippen("home")
        await tippen("r")
        pruefe("Umwandlung, Schritt 3", "Schritt 3 von 3")
        pruefe("Positionen übernommen", "Sprecherstimme")
        await durch_das_formular(4)
        pruefe("Rechnung gespeichert", "Gespeichert")

        # Die Projektnummer bleibt dieselbe. Bis 0.8.2 stand hier die
        # naechste freie Nummer, und die Nummer musste eindeutig sein —
        # beides hat verhindert, was der Benutzer braucht: Aus Angebot 0199
        # wird Rechnung 0199.
        projekt = [
            (d["art"], d["nummer"])
            for d in app.db.execute("SELECT art, nummer FROM dokumente")
        ]
        if len(projekt) == 2 and len({n for _a, n in projekt}) == 1:
            print(f"  ok     ein Projekt, eine Nummer: {projekt[0][1]}")
        else:
            nonlocal_fehler[0] += 1
            print(
                f"  FEHLT  Projektnummer: {projekt} — erwartet zwei Dokumente "
                "mit derselben Nummer"
            )

        await tippen("escape", "escape")
        await tippen("6")
        # Die Projektnummer, nicht "Rechnung": Das Wort steht auch im
        # Hauptmenue, und damit war diese Pruefung schon auf der falschen
        # Seite gruen.
        #
        # "0001" und nicht "0002": Der Lauf tippt keine eigene Nummer, er
        # nimmt den Vorschlag. Angebot und Rechnung bekommen deshalb beide
        # 0001 — und genau das wird zwei Zeilen weiter oben geprueft. Bis
        # 0.8.2 stand hier 0002, weil die Umwandlung die naechste freie
        # Nummer vorgeschlagen hat.
        pruefe("Rechnung in der Liste", "0001")

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
        # Punkt 2, seit 0.8.2: Der Punkt *Logo* ist weg, und mit ihm eine
        # Position. Genau solche Zahlen bleiben liegen, wenn man sie nicht
        # nachsieht — tests/test_menue.py waechtert jetzt ueber alle
        # Anleitungen, aber nicht ueber dieses Skript.
        await tippen("2")
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
        await tippen("5")  # auch das ist um eine Position gewandert
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

        # Erst suchen, dann markieren. Das ist der Fall, der bis 0.8.2
        # schiefging: Aus der gefilterten Liste zu zeichnen holte die gerade
        # bezahlte Rechnung sofort wieder zurueck, und die Liste blieb
        # stehen, als waere nichts passiert.
        await tippen("suche")
        for zeichen in "nordw":
            await tippen(zeichen)
        pruefe("Forderungen filtern", "Alle 1 passen")
        await tippen("tab")
        await tippen("b")
        pruefe("nach dem Markieren leer", "0 gefunden")
        pruefe("und die Liste ist leer", "Nichts vorhanden")

        # ``suche`` zuerst: Nach dem Markieren liegt der Cursor auf der
        # Liste, und ein ``escape`` von dort springt aus dem Bildschirm.
        await tippen("suche")
        await tippen("escape")  # Suchfeld leeren
        pruefe("auch ungefiltert leer", "0 Rechnungen")
        await tippen("tab")  # Fokus zurueck in die Liste

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
