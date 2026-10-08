# Faktur

Angebote und Rechnungen für ein Tonstudio. Ein Menü im Terminal, kein Fenster.

Kunden, Leistungen, Angebote und Rechnungen liegen in einer SQLite-Datei, das
Ergebnis ist eine PDF.

## Loslegen

```bash
./start.sh
```

Beim ersten Mal richtet das Skript alles ein, was fehlt. Danach geht es
sofort los. Unter Windows stattdessen:

```
py -3 -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python -m faktur
```

Es braucht Python ab 3.11 und sonst nichts.

## Was es kann

- Angebote und Rechnungen aus einer gemeinsamen Preisliste, Nummern aus
  einem Zähler
- Angebot per Tastendruck in eine Rechnung umwandeln
- Brieftexte mit Platzhaltern für Kunde, Datum, Betrag, Bank
- Rabatt als Position mit festem Betrag
- PDF in einer Akzentfarbe, dünne Linien, viel Weißraum
- Größen und Bausteine der PDF selbst einstellen, getrennt für Angebot
  und Rechnung

## Mehr

| | |
|---|---|
| [Anleitung](docs/ANLEITUNG.md) | Installation, Start, Fehlersuche, Daten |
| [Bedienung](docs/BEDIENUNG.md) | Menü, Tasten, Textbausteine, Rabatt, PDF |
| [Aufbau](docs/AUFBAU.md) | Dateien, Farben, Entscheidungen |
| [Releases](https://github.com/KyrionKS/faktur/releases) | fertige Quelltextdateien zum Auspacken |

Für die Arbeit daran:

```bash
.venv/bin/python -m pip install -r requirements.txt -r requirements-dev.txt
.venv/bin/python -m pytest            # Tests
.venv/bin/python -m ruff check .      # Fehlerprüfung
.venv/bin/python -m ruff format .     # Formatierung
```

