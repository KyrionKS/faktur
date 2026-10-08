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
| `faktur/einstellungsliste.py` | die Liste mit Werten und Schaltern |
| `faktur/editor.py` | der mehrzeilige Editor für die Brieftexte |
| `faktur/zeichen.py` | das Logo als Text |
| `faktur/farben.py` | die Farben mit ihrem Kontrast |
| `faktur/db.py` | Schema, Verbindung, Umzug und Nummern |
| `faktur/dateien.py` | Kunden, Leistungen, Dokumente |
| `faktur/einstellungen.py` | Stammdaten, Logo, Textbausteine |
| `faktur/bloecke.py` | welche Bausteine auf ein Dokument kommen |
| `faktur/offen.py` | offene und überfällige Rechnungen |
| `faktur/sichern.py` | die Sicherungskopie |
| `faktur/suchen.py` | das Suchfeld über den Listen |
| `faktur/nummer.py` | wie eine Nummer auf dem Dokument aussieht |
| `faktur/betraege.py` | Geldbeträge und Datumsangaben |
| `faktur/texte.py` | Platzhalter einsetzen |
| `faktur/gestaltung.py` | Farben und Größen der PDF |
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

## Die Größen der PDF

Jeder Absatzstil beschreibt sich als Anteil der Grundgröße und als Anteil
seiner eigenen Schriftgröße für den Zeilenabstand. Es gibt keine festen
Zahlen in den Stilen.

Der Grund: Fünfzehn Stile mit eigenen Zahlen müsste man bei einer dritten
Größe von Hand nachziehen, und die meisten hätte man nicht nachgezogen. Der
Zeilenabstand bliebe stehen, während die Schrift wächst, und die Zeile klebt
an der nächsten.

`tests/test_gestaltung.py` hält fest, dass die Anteile bei der
Standardgröße genau die Zahlen ergeben, die vor der Umstellung fest
eingetragen waren.

## Die Bausteine des Dokuments

`faktur/bloecke.py` hält fest, welche Bausteine ein Dokument haben kann und
welche davon die Voreinstellung sind. `faktur/pdf.py` fragt dort nach und
entscheidet selbst nichts mehr.

Ein Bytevergleich zweier PDF sagt nichts: reportlab schreibt einen Zeitstempel
hinein, zweimal derselbe Code liefert verschiedene Bytes. Vergleichen lassen
sich nur die Schriften und ihre Positionen.

## Werkzeuge

| Datei | Wofür |
|---|---|
| `scripts/durchlauf_pruefen.py` | Daten anlegen und PDF schreiben, ohne Menü |
| `scripts/ablauf_pruefen.py` | Tastendurchlauf durch das ganze Programm |
| `scripts/bilder_speichern.py` | Bildschirme als PNG ablegen |
| `scripts/bild_pruefen.py` | ein Bild gegen einen Vergleich prüfen |
| `tests/test_repository.py` | verhindert, dass Benutzerdaten ins Repository kommen |
| `tests/test_keine_nutzerdaten.py` | verhindert, dass ein Testlauf die Daten des Benutzers anfasst |
| `tests/test_gestaltung.py` | hält fest, dass die Größen das Alte ergeben |
| `tests/test_bloecke.py` | hält fest, dass die Voreinstellung das alte Dokument ist |
| `tests/test_ausgabe.py` | prüft, was auf der PDF steht und wo |
| `tests/test_einstellungsliste.py` | prüft die Entscheidungen der Bedienliste |
| `tests/test_offen.py` | prüft, was offen ist und was nicht |
| `tests/test_sichern.py` | prüft, dass gesichert und nicht gezogen wird |
| `tests/test_suchen.py` | prüft die Suche und dass keine Taste ins Leere zeigt |
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



