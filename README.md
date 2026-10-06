# Faktur — New Air Media Group

Angebote und Rechnungen für das Tonstudio. Ein Menü im Terminal, kein
Fenster. Kunden, Leistungen und Dokumente liegen in einer SQLite-Datei, das
Ergebnis ist eine PDF.

## Starten

```bash
cd /home/kyrion/Vibecoding/faktur
.venv/bin/python -m faktur
```

Die Datenbank liegt in `~/.faktur/faktur.db`, das Logo in
`~/.faktur/logo.png`, die PDF in `~/Rechnungen/`.

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

## So arbeitest du damit

**Die Felder sind vorbelegt.** Wo sich etwas ausrechnen lässt, steht der
Vorschlag schon drin — Datum heute, Nummer als nächste freie, Fälligkeit in
zwei Wochen. Enter genügt.

**Positionen wählst du aus der Preisliste**, statt sie abzutippen. Wähle
dort eine Leistung, dann justierst du Menge und Preis.

**Vor dem Speichern kommt die Kontrolle**: alle Positionen, der
Gesamtbetrag, der Brieftext. Erst dann entsteht das Dokument und die PDF,
und der Pfad wird dir genannt.

**Angebot zu Rechnung.** Punkt 2 nimmt die Positionen eines Angebots
unverändert mit. Du gibst nur Datum und Fälligkeit an.

## Textbausteine

Unter `6` → `3` und `4`: je ein Text für Angebote und für Rechnungen.
Leerzeilen trennen Absätze.

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
Namen es nicht kennt. Unter `6` → `5` steht die ganze Liste.

`{{Kunde_Anrede}}` schneidet den Vornamen ab: aus „Herr Max Mustermann"
wird „Herr Mustermann". Damit kannst du frei formulieren statt in
Höflichkeitsformeln zu verfallen.

## Nummern

Die Nummer wird vorgeschlagen, aber sie gehört dir und deinem Steuerberater.
Vergibt sind gleiche Nummern für die gleiche Art: ein Angebot und eine
Rechnung dürfen beide `2026-001` heißen, zwei Rechnungen nicht.

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
| `faktur/zeichen.py` | das Logo als Text |
| `faktur/db.py` | Schema und Verbindung |
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

## Entwicklung

```bash
.venv/bin/python -m pytest            # Tests
.venv/bin/python -m ruff check .      # Fehlerprüfung
.venv/bin/python -m ruff format .     # Formatierung
```

### Den Ablauf prüfen

```bash
.venv/bin/python scripts/durchlauf_pruefen.py   # Daten und PDF ohne Menü
.venv/bin/python scripts/ablauf_pruefen.py      # ganz durch die Oberfläche
.venv/bin/python scripts/bild_pruefen.py        # Menü in verschiedenen Grössen
```

`ablauf_pruefen.py` tippt sich durch die App wie ein Mensch und prüft nach
jedem Schritt, ob der richtige Bildschirm da steht. Das prüft genau das, woran
die erste Fassung gescheitert ist.

## Was fehlt bewusst

Keine Verträge, keine Projektverwaltung, kein Storno, keine Rabatte, kein
Mahnwesen. Preise sind Endpreise.

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