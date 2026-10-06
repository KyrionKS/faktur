# Faktur auf dem Mac

Zwei Wege zum fertigen Programm. Der erste baut es selbst, der zweite holt
es als Release.

## Weg 1: selbst bauen

Braucht: Terminal, und Python ab 3.11. Fehlt es:

```bash
brew install python@3.12
```

Dann das Programm holen und bauen:

```bash
git clone git@github.com:KyrionKS/faktur.git
cd faktur
.venv/bin/python scripts/app_bauen.py
```

Wer das Projekt schon hat, genügt `cd faktur` und der Aufruf von
`scripts/app_bauen.py`.

Das Ergebnis liegt in `dist/Faktur.app`:

```bash
open dist/Faktur.app
```

Beim ersten Start legt das Programm neben sich einen Ordner `daten/` an.
Dort liegen Datenbank, Logo und die PDF. Also:

```
Faktur/
  Faktur.app
  daten/
    faktur.db
    logo.png
    Dokumente/
      ANG - 0001 - Soundcheck GmbH.pdf
```

Legst du `Faktur.app` nach `~/Programme`, liegt alles unter
`~/Programme/daten/`.

## Weg 2: Release herunterladen

Unter <https://github.com/KyrionKS/faktur/releases> liegt zu jeder Version
ein `Faktur.app.zip`. Herunterladen, auspacken, `Faktur.app` doppelklicken.

Für Version 0.3 direkt:

<https://github.com/KyrionKS/faktur/releases/download/v0.3/Faktur.app.zip>

Ein aus dem Netz geladenes Programm trägt ein Attribut, das macOS blockiert.
Falls die Meldung *„Kann nicht geöffnet werden, weil der Entwickler nicht
verifiziert werden konnte"* kommt, im Terminal:

```bash
xattr -cr ~/Downloads/Faktur.app
```

Ein selbst gebautes Programm hat dieses Problem nicht.

Die Datei heißt `Faktur.app.zip` und ist rund 20 Megabyte groß. Nach dem
Auspacken bleibt sie liegen; das Programm selbst ist die Datei `Faktur.app`.

## Das Logo

Das Programm bekommt sein Symbol aus `logo.png`. Leg die Datei neben das
Projekt, eine Ebene höher:

```
Vibecoding/
  faktur/
  logo.png
```

Fehlt sie, startet das Programm ohne Symbol. Das ist kein Fehler, nur weniger
schön.

## Was in dem Programm steckt

Ein Python-Interpreter samt allem, was das Programm braucht. Auf dem Mac
ist also nichts weiter zu installieren — außer dem Programm selbst.

Die Datei ist rund 40 bis 60 Megabyte groß. Das ist normal: ein Python mit
Bildverarbeitung und PDF-Bibliothek ist keine Kleinigkeit.

## Wenn etwas nicht startet

**„Kann nicht geöffnet werden"** — siehe Weg 2, `xattr`.

**Fenster schließt sich sofort** — im Terminal starten, dann bleibt die
Fehlermeldung stehen:

```bash
./Faktur.app/Contents/MacOS/Faktur
```

**Pfeiltasten gehen nicht** — funktionieren in *Terminal.app*, in *iTerm* und
in einem Fenster mit *Terminal* als Standardprofil. In der klassischen
Eingabeaufforderung von Windows nicht, aber das ist ein anderes System. Als
Ausweichweg gehen die Ziffern und der Anfangsbuchstabe.

**Menü zu breit** — das Fenster schmaler als 80 Zeichen geht nicht. Das Logo
schrumpft, das Menü nicht.

## Aktuelle Version


0.3.0