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
hineinlegen, fertig — das Programm findet sie beim nächsten Start von
selbst und zeigt unter `7` → *Stammdaten* an, welche Datei es benutzt.

Bis 0.8.2 gab es dort auch den Punkt **Logo**. Der hat die Datei an genau der
Stelle gesucht, an der er sie hinschreiben wollte, und das Programm beim
Klick abstürzen lassen. Ein Dateidialog wäre die Alternative gewesen, aber
Textual bringt keinen mit, der über ein Terminal funktioniert. Der Punkt
fliegt deshalb raus, statt dass er kaputt bleibt: **die Datei nach
`daten/logo.png` legen ist der ganze Weg.**

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

## Das Programm macht keine Sicherungen

Das ist Absicht und keine Vergesslichkeit: Es gab eine Sicherungsfunktion,
und sie wurde wieder entfernt, weil der Rahmen größer war als die Sache
selbst.

**Was das bedeutet:** Fällt die Platte aus, ist alles weg. Bei einem Angebot,
das schon beim Kunden liegt, gibt es kein Zurück — die Nummer steht gedruckt
auf einem Dokument, das niemandem mehr gehört.

**Was zu tun ist.** Den Ordner `daten` von Zeit zu Zeit auf eine andere Platte
kopieren, und zwar mit geschlossenem Programm:

```bash
cp -r ~/Vibecoding/faktur/daten ~/Sicherung-faktur
```

Ein Kopieren bei laufendem Programm kann eine halb geschriebene Datenbank
erwischen. Die ist dann zwar nicht verloren — neben ihr liegt eine Kopie —
aber die Meldung beim nächsten Start wäre verwirrend.

Wer das nicht selbst erinnern will, lässt den Ordner in einer Cloud
mitlaufen. Ein Programm, das seine eigenen Daten kopiert, kopiert sie
irgendwann ausgerechnet dann, wenn es damit beschäftigt ist, eine Rechnung zu
schreiben.

## Terminals

Die Pfeiltasten brauchen ein Terminal, das sie kennt: **Terminal.app**,
*iTerm*, Windows Terminal oder PowerShell. In der klassischen
Eingabeaufforderung von Windows funktionieren sie teilweise nicht — dort
helfen die Zahlen oder der Anfangsbuchstabe.

Das Terminalfenster braucht mindestens 80 Spalten und 24 Zeilen. Ist es
kleiner, passt das Menü nicht und es sieht abgeschnitten aus.

Ohne Farbe geht alles auch: mit `NO_COLOR=1` wird alles schwarz geschrieben,
das Menü bleibt bedienbar.

