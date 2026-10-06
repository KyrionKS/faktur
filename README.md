# Faktur — New Air Media Group

Angebote und Rechnungen für das Tonstudio. Ein Menü im Terminal, kein
Fenster. Kunden, Leistungen und Dokumente liegen in einer SQLite-Datei, das
Ergebnis ist eine PDF.

## Starten

```bash
cd /home/kyrion/Vibecoding/faktur
.venv/bin/python -m faktur
```

Alles liegt in einem Ordner neben dem Programm:

```
daten/
  faktur.db
  logo.png
  Dokumente/
    ANG - 0001 - Soundcheck GmbH.pdf
    RE - 0002 - Soundcheck GmbH.pdf
```

Angebot und Rechnung teilen sich den Ordner; die Art steht im Dateinamen.
Der ganze Bestan liegt an einer Stelle, lässt sich kopieren, verschieben
oder sichern, ohne dass man wissen muss, wo das Programm installiert ist.

`daten/` steht in `.gitignore`. Die Datenbank gehört nicht ins Repository.

## Das Menü

```
╲     ╲     ╲     ╲     ╲     ╲  NEW AIR
 ╲   ╱ ╲   ╱ ╲   ╱ ╲   ╱ ╲   ╱ ╲  MEDIA GROUP
  ╲ ╱   ╲ ╱   ╲ ╱   ╲ ◆   ╲ ╱
   ╲     ╲     ◆     ╲     ◆
  ╱ ╲   ╱ ◆   ╱ ╲   ╱ ◆   ╱ ╲
 ╱   ◆ ╱   ╲ ╱   ╲ ╱   ╲ ╱   ╲ ╱
╲     ╲     ╲     ◆     ╲     ╲
 ╲   ╱ ╲   ╱ ╲   ╱ ╲   ╱ ╲   ╱ ╲

▶   1. Angebot erstellen         Aus Leistungen ein Angebot bauen
    2. Rechnung erstellen        Aus Leistungen abrechnen
    3. Kunden                    Kunden anlegen, ansehen, suchen
    4. Leistungen                Die Preisliste pflegen
    5. Dokumente                 Angebote und Rechnungen durchsehen
    6. Stammdaten                Firma, Bank, Logo, Brieftexte
    7. PDF neu schreiben         Ein Dokument noch einmal ausgeben
    8. Rechnungsordner öffnen    Den Ordner mit den PDF zeigen
    q. Beenden                   Das Programm verlassen
```

## Wie du dich bewegst

**↑ und ↓** verschieben die Auswahl. Das Bild bleibt ruhig, es wird nur
die markierte Zeile neu gezeichnet.

**⏎ (Enter)** bestätigt den markierten Punkt.

Weiterhin möglich, wenn es schneller geht:

| Taste | Wirkung |
|---|---|
| `1` bis `9`, `q` | direkt zum Punkt |
| erster Buchstabe | passt auf den Punkt |
| `n` | neu anlegen |
| `F2` | ändern |
| `Entf` | löschen, fragt vorher nach |
| `esc` | einen Schritt zurück |
| `Strg+Q` | beenden |

## Angebot in Rechnung

Steht die Auswahl in der Dokumentenliste auf einem **Angebot**, macht `r`
daraus eine Rechnung. Kunde, alle Positionen, Texte und Preise wandern mit,
samt der Verknüpfung zur Preisliste. Das Angebot bleibt als Beleg stehen.

Offen bleiben nur Nummer, Datum und Fälligkeit — die stehen schon in der
Kontrolle, weil sie sich von Rechnung zu Rechnung unterscheiden.

Steht die Auswahl auf keinem Angebot, fängt `r` wie bisher eine neue Rechnung
an. Die Taste meint immer dasselbe: abrechnen.

## So arbeitest du damit

**Die Felder sind vorbelegt.** Wo sich etwas ausrechnen lässt, steht der
Vorschlag schon drin — Datum heute, Nummer als nächste freie, Fälligkeit in
zwei Wochen. Enter genügt.

**Positionen wählst du aus der Preisliste**, statt sie abzutippen. Wähle
dort eine Leistung, dann justierst du Menge und Preis.

**Vor dem Speichern kommt die Kontrolle**: alle Positionen, der
Gesamtbetrag, der Brieftext. Erst dann entsteht das Dokument und die PDF,
und der Pfad wird dir genannt.

**Angebot zu Rechnung.** Siehe oben, ein Tastendruck in der Dokumentenliste.

## Nummern

Vier Stellen, führende Nullen: `0001`, `0002`, `0003`. **Angebot und
Rechnung kommen aus einem Zähler**, damit nebeneinandersteht, dass sie zum
selben Vorgang gehören. Angebot `0001` und Rechnung `0002` sind Paar und
Vorgang.

Die Nummer wird vorgeschlagen, aber sie gehört dir und deinem Steuerberater.
Die Datenbank lässt keine doppelte Nummer zu, auch nicht über die Art
hinweg.

Beim ersten Start nach dem Umstieg werden die alten Nummern auf vier Stellen
geschrieben, nach Datum sortiert. Vorher landet eine Kopie neben der
Datenbank: `daten/faktur.db.bak`.

## Textbausteine

Unter `6` → `3` und `4`: je ein Text für Angebote und für Rechnungen.

Das ist ein eigener Editor mit Zeilennummern, kein einzeiliges Feld — der
Text hat Absätze, und die müssen beim Speichern unbeschädigt bleiben.
Leerzeilen trennen Absätze.

| Taste | Wirkung |
|---|---|
| `Strg+S` | speichern |
| `Strg+R` | den mitgelieferten Vorschlag zurückholen |
| `esc` | abbrechen |

Unter dem Feld stehen die Namen, die du verwenden kannst.

Doppelte Klammern ersetzt das Programm:

| Platzhalter | ergibt |
|---|---|
| `{{Kunde}}` | Soundcheck GmbH |
| `{{Kunde_Anrede}}` | Herr Mustermann |
| `{{Ansprechpartner}}` | Max Mustermann |
| `{{Nummer}}` | 2026-014 |
| `{{Datum}}` | 06.10.2026 |
| `{{Faellig}}` | 20.10.2026 |
| `{{Gueltig_bis}}` | 27.10.2026 |
| `{{Betrag}}` | 3.290,00 € |
| `{{Anzahl_Positionen}}` | 2 |
| `{{EigeneFirma}}` | New Air Media Group |
| `{{Bank}}` | Deutsche Kreditbank |
| `{{IBAN}}` | DE02 1203 0000 0000 2020 51 |

**Tippfehler bleiben sichtbar.** `{{Kuude}}` steht als `{{Kuude}}` auf der
PDF, statt still zu verschwinden. Beim Speichern sagt das Programm, welche
Namen es nicht kennt.

`{{Kunde_Anrede}}` schneidet den Vornamen ab: aus „Herr Max Mustermann"
wird „Herr Mustermann". Damit kannst du frei formulieren statt in
Höflichkeitsformeln zu verfallen.

## Rabatt

Im Schritt mit den Positionen gibt es einen eigenen Punkt **Rabatt
eintragen**. Gefragt wird nur der Betrag — das Minus setzt das Programm,
weil ein Rabatt immer abzieht. Die Bezeichnung bleibt „Rabatt" und ist
änderbar.

```
Aufnahme Ton                    2 Tag    1.700,00 €
Mischung und Mastering         10 Stunde     950,00 €
Rabatt                                        -300,00 €
                                  Gesamtbetrag  2.350,00 €
```

Auf der PDF steht der Rabatt in der Akzentfarbe, damit er als eigener
Posten erkennbar ist, ohne dass die Tabelle bunt wird. Er funktioniert auf
Angebot und Rechnung gleichermassen, und er wandert bei der Umwandlung eines
Angebots mit.

Es gibt keinen Prozentrabatt. Dafür müsste das Programm den Betrag aus der
Zwischensumme rechnen, was bei einem Rabatt auf einen Rabatt unangenehm
wird.

## Die Farben

Es sind zwei Farben mit demselben Farbton, aber für zwei Untergründe:

| | Wert | Kontrast |
|---|---|---|
| PDF, auf Papier | `#512E80` | 10.23:1 |
| Terminal, Hauptakzent | `#C9B5E3` | 7.28:1 |
| Terminal, Nebenton | `#A88CD4` | 4.79:1 |

Das Violett aus dem Logo ist auf Papier hervorragend und im Terminal
unbrauchbar — dort hat es nur 1.33:1, man sieht es kaum noch. Darum sind es
zwei Werte. Alle stehen in `faktur/farben.py` mit der gemessenen Zahl, und
`tests/test_farben.py` rechnet nach, damit niemand sie wieder dunkler macht.

## Wie die PDF aussieht

- eine einzige Akzentfarbe, `#512E80`, aus dem Logo ausgelesen
- viel Weissraum, dünne Linien statt Kästen
- gesperrte Spalten: Bezeichnung links, Preise rechts
- das Logo behält Proportionen und steht auf jeder Seite
- Fußzeile mit Firmenzeile und Seitenzahl
- auf Angeboten steht keine Steuernummer, auf Rechnungen schon

Preise enthalten keine Steuerausweisung. Die App ist als Werkzeug für
Kleinunternehmer gebaut; wer umsatzsteuerpflichtig ist, trägt den Betrag
inklusive Steuer als Endpreis ein.

## Aufbau

| Datei | Inhalt |
|---|---|
| `faktur/app.py` | die App und das Hauptmenü |
| `faktur/basis.py` | der Rahmen aller Bildschirme |
| `faktur/widgets.py` | Logo, Auswahlliste, Formular, Tabelle |
| `faktur/editor.py` | der mehrzeilige Editor für die Brieftexte |
| `faktur/zeichen.py` | das Logo als Text |
| `faktur/farben.py` | die Farben mit ihrem Kontrast |
| `faktur/db.py` | Schema, Verbindung, Umzug und Nummern |
| `faktur/dateien.py` | Kunden, Leistungen, Dokumente |
| `faktur/einstellungen.py` | Stammdaten, Logo, Textbausteine |
| `faktur/betraege.py` | Geldbeträge und Datumsangaben |
| `faktur/texte.py` | Platzhalter einsetzen |
| `faktur/gestaltung.py` | Farben und Schriften der PDF |
| `faktur/pdf.py` | Aufbau von Angebot und Rechnung |
| `faktur/screens/` | die Bildschirme |

Textual hält einen echten Bildschirmpuffer. Die Bildschirme beschreiben nur,
wie sie aussehen, und Textual zeichnet die Unterschiede. Deshalb bleibt das
Bild ruhig und nichts läuft über, wenn ein Untermenü zurückkommt.

## Starten

Faktur wird aus dem Quelltext gestartet, auf jedem System gleich:

```bash
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m faktur
```

Für den Mac gibt es `ANLEITUNG-MAC.md` mit denselben drei Schritten und den
Fällen, die dort schon vorgekommen sind.

Es gibt bewusst kein gebautes `.app`. Ein Packer übersetzt nicht: was auf
einem Rechner gebaut wird, startet auf einem anderen nicht zuverlässig. Ein
Programm im Terminal braucht das auch nicht — es braucht Python, und das
ist auf jedem Rechner in zwei Minuten installiert.

## Entwicklung

```bash
.venv/bin/python -m pip install -r requirements.txt -r requirements-dev.txt
.venv/bin/python -m pytest            # Tests
.venv/bin/python -m ruff check .      # Fehlerprüfung
.venv/bin/python -m ruff format .     # Formatierung
```

`requirements.txt` enthält nur, was das fertige Programm zum Laufen
braucht. Alles für die Entwicklung steht in `requirements-dev.txt`.

`target-version` in `pyproject.toml` muss zu `requires-python` passen. Steht
es zu hoch, schreibt ruff Syntax hinaus, die auf einem älteren Python gar
nicht läuft — mit `py314` ließ es die Klammern um `except` weglassen, und
das gibt es erst seit Python 3.14.

### Den Ablauf prüfen

```bash
.venv/bin/python scripts/durchlauf_pruefen.py   # Daten und PDF ohne Menü
.venv/bin/python scripts/ablauf_pruefen.py      # ganz durch die Oberfläche
.venv/bin/python scripts/bild_pruefen.py        # Menü in verschiedenen Grössen
.venv/bin/python scripts/bilder_speichern.py    # Bildschirme als PNG
```

`ablauf_pruefen.py` tippt sich durch die App wie ein Mensch und prüft nach
jedem Schritt, ob der richtige Bildschirm da steht — inklusive der Umwandlung
von Angebot in Rechnung. Das prüft genau das, woran die erste Fassung
gescheitert ist.

`bilder_speichern.py` legt PNG von jedem Bildschirm in `beispiele/` ab. Damit
sieht man den Kontrast, statt ihn zu rechnen.

## Was fehlt bewusst

Keine Verträge, keine Projektverwaltung, kein Storno, keine Mahnwesen, kein
Prozentrabatt. Preise sind Endpreise. Das Angebot wird beim Umwandeln
kopiert, nicht verschoben — der Beleg bleibt stehen.

## Auf macOS und Windows

```bash
python -m faktur
```

Die Pfeiltasten brauchen ein Terminal, das sie kennt: **Terminal.app**,
*iTerm*, Windows Terminal oder PowerShell. In der klassischen
Eingabeaufforderung von Windows funktionieren sie teilweise nicht — dort
helfen die Zahlen oder der Anfangsbuchstabe.

Ohne Farbe geht alles auch: mit `NO_COLOR=1` wird alles schwarz geschrieben,
das Menü bleibt bedienbar.

## Vor dem ersten echten Einsatz

Die PDF wurden unter Linux erzeugt. Auf macOS und Windows können Schriften
und Zeilenhöhen anders aussehen. Ein Angebot und eine Rechnung einmal dort
öffnen, bevor sie an Kunden gehen.