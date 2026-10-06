# Faktur auf dem Mac

Faktur ist ein Programm im Terminal. Es braucht Python, sonst nichts — kein
Installer, kein Programm mit Symbol.

```
git clone git@github.com:KyrionKS/faktur.git
cd faktur
```

## 1. Python prüfen

```bash
python3 --version
```

Es muss **3.11 oder neuer** sein. Ältere Versionen kann das Programm nicht
starten. Hat macOS ein altes Python mitgeliefert, holst du ein neues:

```bash
brew install python@3.12
```

Danach nochmal `python3 --version`. Bleibt es bei einer alten Nummer, nimm
ausdrücklich das neue:

```bash
/opt/homebrew/bin/python3.12 --version
```

Auf einem Mac mit Intel-Chip liegt es unter `/usr/local/bin`.

## 2. Umgebung anlegen

Im Ordner `faktur`:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
```

Das dauert eine Minute. Danach stehen Textual, Pillow und Reportlab im
venv. Alle drei gibt es fertig für den Mac, es wird nichts übersetzt.

## 3. Starten

```bash
.venv/bin/python -m faktur
```

Beim ersten Mal legt das Programm `daten/` neben sich an und trägt die fünf
Leistungen ein.

**Das Terminalfenster braucht mindestens 80 Spalten und 24 Zeilen.** Ist es
kleiner, passt das Menü nicht und es sieht abgeschnitten aus. Im Terminal
geht das über *Fenster → Größe* oder mit ⌘ und Maus ziehen.

## Wenn es nicht startet

**Der Grund für „geht nichts": Das Fenster öffnet sich und ist sofort wieder
weg.**

Ein Menü im Terminal stirbt ohne jede Meldung, wenn etwas schiefgeht. Deshalb
zwei Dinge:

**Im Terminal starten, nicht per Doppelklick.** Dann bleibt die
Fehlermeldung stehen, statt dass sie mit dem Fenster verschwindet. Das ist
der wichtigste Schritt, weil die Meldung sonst niemand zu sehen bekommt.

**Die Fehlermeldung herausschreiben.** Wenn die Ausgabe zu lang ist, legt
Terminal sie in eine Datei. Oder per Umleitung:

```bash
.venv/bin/python -m faktur 2>&1 | tee /tmp/faktur-fehler.txt
```

## Wenn beim Installieren etwas schiefgeht

**`externally-managed-environment`** — die neuere Python-Version von macOS
lässt sich nicht global verändern. Das ist genau der Grund für Schritt 2: mit
`.venv` wird in eine eigene Umgebung installiert und die Systeminstallation
bleibt unangetastet. Wer den Fehler sieht, hat Schritt 2 übersprungen.

**`No matching distribution found`** bei einer der drei Abhängigkeiten —
dann stimmt die Python-Version nicht. Zurück zu Schritt 1.

**`fatal: repository not found`** beim Klonen — mit `https://github.com/KyrionKS/faktur.git`
probieren, falls kein Schlüssel hinterlegt ist.

## Wenn die Daten nicht da sind, wo du sie erwartest

Das Programm legt alles neben sich ab:

```
faktur/
  daten/
    faktur.db
    logo.png
    Dokumente/
      ANG - 0001 - Soundcheck GmbH.pdf
      RE - 0002 - Soundcheck GmbH.pdf
```

Also immer neben dem Ordner `faktur`, unabhängig davon, von wo du startest.
Ein leerer Datenordner bedeutet: erster Start oder gerade zurückgesetzt.

## Das Logo

Ohne Logo kommen die PDF ohne Bild. Das Programm sucht die Datei hier:

```
faktur/daten/logo.png
```

Den Ordner `daten/` legt es beim ersten Start selbst an. Danach die Datei
hineinlegen. Oder über *Stammdaten → Logo*, dann kopiert das Programm sie
selbst an die richtige Stelle.

## Wenn gar nichts hilft

Diese drei Befehle zeigen, wo es hakt. Ihre Ausgabe sagt mehr als jede
Vermutung:

```bash
.venv/bin/python -c "import sys; print(sys.version)"
.venv/bin/python -c "import textual, reportlab, PIL; print('Abhängigkeiten da')"
.venv/bin/python -c "import faktur.app; print('Programm lädt sich')"
```

Der letzte Befehl ist der aussagekräftigste: Er zieht das ganze Programm
herein, und wenn etwas fehlt oder kaputt ist, steht hier die Fehlermeldung
und nicht irgendwo in einem weggeworfenen Fenster.

Die eigenen Tests laufen mit

```bash
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q
```

und sagen, ob das Programm an sich in Ordnung ist — unabhängig davon, was auf
deinem Rechner los ist.

## Daten mitnehmen

`daten/` ist der ganze Bestand: Kunden, Leistungen, Angebote, Rechnungen.
Der Ordner lässt sich kopieren, verschieben und sichern. Mehr braucht es
nicht.

## Aktuelle Version

0.3.0