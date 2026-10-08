# Anleitung

Faktur ist ein Programm im Terminal. Es braucht Python ab 3.11, sonst nichts.

## Loslegen

```
git clone https://github.com/KyrionKS/faktur.git
cd faktur
./start.sh
```

Beim ersten Mal legt das Skript eine Umgebung an und holt die drei
Bibliotheken. Das dauert eine Minute. Danach startet es sofort.

Unter Windows gibt es kein Startskript, weil es dort zwei gekoppelte Dateien
wären. Zwei Befehle tun dasselbe:

```
py -3 -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python -m faktur
```

## Wenn vorher noch nichts da ist

**`python3 --version` sagt weniger als 3.11** — dann ein neues holen:

```bash
brew install python@3.12              # macOS
sudo apt install python3-venv         # Ubuntu und Fedora-artige
```

Bleibt es bei einer alten Nummer, nimm ausdrücklich das neue:

```bash
/opt/homebrew/bin/python3.12 --version
```

Auf einem Mac mit Intel-Chip liegt es unter `/usr/local/bin`.

## Das Startskript

| Datei | Für |
|---|---|
| `start.sh` | Linux und Mac im Terminal |
| `start.command` | Mac, doppelklickbar im Finder |
| `start.py` | die eigentliche Logik |

`start.command` im Finder öffnet ein Terminalfenster, in dem das Programm
läuft. Beenden mit `Strg+Q` — oder das Fenster schließen.

Beim zweiten Start arbeitet das Skript fast nichts: Es prüft die
Bibliotheken kurz und startet. Dauert rund eine halbe Sekunde.

## Das Logo

Ohne Logo kommen die PDF ohne Bild. Das Programm sucht die Datei hier:

```
faktur/daten/logo.png
```

Den Ordner `daten/` legt es beim ersten Start selbst an. Danach die Datei
hineinlegen, oder über `6` → *Stammdaten* → *Logo* — dann kopiert das
Programm sie selbst an die richtige Stelle.

Fehlt das Logo, sagt das Startskript es einmal beim ersten Start.

## Wenn es nicht startet

**Das Fenster öffnet sich und ist sofort wieder weg.**

Ein Menü im Terminal stirbt ohne jede Meldung, wenn etwas schiefgeht. Zwei
Dinge dagegen:

**Im Terminal starten, nicht per Doppelklick.** Dann bleibt die Fehlermeldung
stehen, statt dass sie mit dem Fenster verschwindet.

**Die Meldung herausschreiben**, falls die Ausgabe zu lang ist:

```bash
./start.sh 2>&1 | tee /tmp/faktur-fehler.txt
```

Das Startskript sagt von sich aus, was fehlt: kein Python, ein zu altes
Python, ein Python ohne pip, eine fehlgeschlagene Installation. Die Meldung
nennt auch, was man dagegen tun soll.

## Was beim Installieren schiefgehen kann

**`externally-managed-environment`** — die neuere Python-Version von macOS
lässt sich nicht global verändern. Das ist genau der Grund für das Startskript:
es installiert in eine eigene Umgebung und die Systeminstallation bleibt
unangetastet. Wer den Fehler sieht, hat `python3 -m venv` übersprungen.

**`ensurepip is not available`** — auf vielen Linux-Systemen fehlt pip im
mitgelieferten Python:

```bash
sudo apt install python3-venv
```

**`No matching distribution found`** bei einer der drei Bibliotheken — dann
stimmt die Python-Version nicht. Zurück nach oben.

## Wenn gar nichts hilft

Diese drei Befehle zeigen, wo es hakt:

```bash
.venv/bin/python -c "import sys; print(sys.version)"
.venv/bin/python -c "import textual, reportlab, PIL; print('Abhängigkeiten da')"
.venv/bin/python -c "import faktur.app; print('Programm lädt sich')"
```

Der letzte ist der aussagekräftigste. Er zieht das ganze Programm herein,
und wenn etwas fehlt oder kaputt ist, steht hier die Fehlermeldung und nicht
irgendwo in einem weggeworfenen Fenster.

Die eigenen Tests sagen, ob das Programm an sich in Ordnung ist —
unabhängig davon, was auf deinem Rechner los ist:

```bash
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q
```

## Die Daten

Alles liegt in einem Ordner `daten` neben dem Programm:

```
faktur/
  daten/
    faktur.db
    logo.png
    Dokumente/
      ANG - 0001 - Soundcheck GmbH.pdf
      RE - 0002 - Soundcheck GmbH.pdf
```

Immer neben dem Ordner `faktur`, unabhängig davon, von wo du startest. Ein
leerer Datenordner bedeutet: erster Start.

Angebot und Rechnung teilen sich den Ordner; die Art steht im Dateinamen.

`daten/` ist der ganze Bestand: Kunden, Leistungen, Angebote, Rechnungen.
Der Ordner lässt sich kopieren, verschieben und sichern. Mehr braucht es
nicht.

## Terminals

Die Pfeiltasten brauchen ein Terminal, das sie kennt: **Terminal.app**,
*iTerm*, Windows Terminal oder PowerShell. In der klassischen
Eingabeaufforderung von Windows funktionieren sie teilweise nicht — dort
helfen die Zahlen oder der Anfangsbuchstabe.

Das Terminalfenster braucht mindestens 80 Spalten und 24 Zeilen. Ist es
kleiner, passt das Menü nicht und es sieht abgeschnitten aus.

Ohne Farbe geht alles auch: mit `NO_COLOR=1` wird alles schwarz geschrieben,
das Menü bleibt bedienbar.
