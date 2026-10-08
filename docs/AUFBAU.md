# Aufbau

Für alle, die etwas ändern wollen. Wer Faktur benutzen will, braucht das
hier nicht.

## Dateien

| Datei | Inhalt |
|---|---|
| `start.py` | richtet beim Start alles ein und startet das Programm |
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
| `faktur/orte.py` | wo die Daten liegen |
| `faktur/screens/` | die Bildschirme |

## Der Bildschirmpuffer

Textual hält einen echten Bildschirmpuffer. Die Bildschirme beschreiben nur,
wie sie aussehen, und Textual zeichnet die Unterschiede. Deshalb bleibt das
Bild ruhig und nichts läuft über, wenn ein Untermenü zurückkommt.

Daraus folgt eine Konvention, die im ganzen Projekt gilt: **ein Callback pro
Bildschirmsprung.** Zwei `pop_screen()` für einen `push_screen()` führten
dazu, dass der Rückweg ins Leere lief.

## Die Farben

Es sind zwei Werte desselben Farbtons, weil es zwei Untergründe gibt:

| | Wert | Kontrast |
|---|---|---|
| PDF, auf Papier | `#512E80` | 10.23:1 |
| Terminal, Hauptakzent | `#C9B5E3` | 7.28:1 |
| Terminal, Nebenton | `#A88CD4` | 4.79:1 |

Das Violett aus dem Logo ist auf Papier hervorragend und im Terminal
unbrauchbar — dort hat es nur 1.33:1, man sieht es kaum noch. Darum sind es
zwei Werte. Alle stehen in `faktur/farben.py` mit der gemessenen Zahl, und
`tests/test_farben.py` rechnet nach, damit niemand sie wieder dunkler macht.

`faktur/app.tcss` trägt dieselben Werte als Zeichenketten. Textual liest CSS,
nicht Python, die Zahlen stehen deshalb an zwei Stellen — mit einem
Herkunftsvermerk, der sagt, woher sie kommen.

## Die Schriften der PDF

`faktur/gestaltung.py` setzt `Helvetica`. Das ist keine Schrift, die irgendwo
installiert sein muss, sondern eine der vierzehn Grundschriften, die im
PDF-Format selbst enthalten sind. Jeder Betrachter hat sie.

Daraus folgt: **Die PDF sieht auf jedem Betriebssystem gleich aus.** Es gibt
deshalb keinen Grund, sie auf einem bestimmten System zu erzeugen.

## Werkzeuge

| Datei | Wofür |
|---|---|
| `scripts/durchlauf_pruefen.py` | Daten anlegen und PDF schreiben, ohne Menü |
| `scripts/ablauf_pruefen.py` | Tastendurchlauf durch das ganze Programm |
| `scripts/bilder_speichern.py` | Bildschirme als PNG ablegen |
| `scripts/bild_pruefen.py` | ein Bild gegen einen Vergleich prüfen |
| `tests/test_repository.py` | verhindert, dass Benutzerdaten ins Repository kommen |
| `tests/test_dateiformen.py` | prüft Zeilenumbrüche und die Startskripte |
| `tests/test_version.py` | hält die Versionsangaben zusammen |
| `tests/test_python_version.py` | hält `requires-python` und den Quelltext zusammen |

`pyproject.toml` trägt `target-version` für ruff. Sie muss zu
`requires-python` passen: Steht sie zu hoch, schreibt ruff Syntax hinaus, die
auf einem älteren Python gar nicht läuft. Mit `py314` ließ es die Klammern um
`except` weglassen, und das gibt es erst seit Python 3.14.

## Was fehlt bewusst

Keine Verträge, keine Projektverwaltung, kein Storno, kein Mahnwesen, kein
Prozentrabatt. Preise sind Endpreise. Das Angebot wird beim Umwandeln
kopiert, nicht verschoben — der Beleg bleibt stehen.

Ein gebautes `.app` gibt es bewusst auch nicht. Ein Packer übersetzt nicht:
was auf einem Rechner gebaut wird, startet auf einem anderen nicht zuverlässig.
Ein Programm im Terminal braucht das auch nicht.

