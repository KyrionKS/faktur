"""Die Werkzeuge unter `scripts/` und was sie voraussetzen.

`ablauf_pruefen.py` braucht 23 Sekunden, das taugt nicht für den Testlauf.
Es wird von Hand gefahren und nicht von hier. Was aber in den Testlauf
gehört, sind die beiden Voraussetzungen, an denen es und
`bilder_speichern.py` hängen:

- Beide lesen den Bildschirm über ``screen._compositor``, und das ist eine
  **private** Schnittstelle von Textual. Bricht sie beim Aufrüsten, fallen
  beide Skripte lautlos um — niemand merkt es, weil sie nicht laufen.
- Beide brauchen die Laufzeitabhängigkeiten aus `requirements.txt`. Fehlt
  dort eine, die der Code direkt benutzt, laeuft das Programm nur, weil
  etwas anderes sie zufällig mitinstalliert.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest
from faktur.app import FakturApp

#: Wurzels des Projekts.
WURZEL = Path(__file__).resolve().parents[1]

#: Die Skripte, die es geben muss, und wozu.
SKRIPTE = {
    "ablauf_pruefen.py": "Tastendurchlauf durch die ganze Oberfläche",
    "bilder_speichern.py": "Bildschirme als PNG",
    "durchlauf_pruefen.py": "Daten anlegen und PDF schreiben, ohne Menü",
}

#: Pakete, die direkt benutzt werden. ``pillow`` heisst in Python ``PIL``.
DIREKT = {
    "PIL": "pillow",
    "reportlab": "reportlab",
    "textual": "textual",
    "rich": "rich",
}


def _importe(wurzel: Path) -> set[str]:
    """Sammelt alle importierten Namen aus dem Python-Code.

    Args:
        wurzel: Der Ordner, in dem gesucht wird.

    Returns:
        Die Namen der obersten Ebenen, ohne ``faktur`` und ohne die
        Standardbibliothek.
    """
    gefunden: set[str] = set()

    for ordner in ("faktur", "scripts", "tests"):
        for datei in sorted((wurzel / ordner).rglob("*.py")):
            baum = ast.parse(datei.read_text(encoding="utf-8"))
            for knoten in ast.walk(baum):
                if isinstance(knoten, ast.Import):
                    gefunden.update(a.name.split(".")[0] for a in knoten.names)
                elif (
                    isinstance(knoten, ast.ImportFrom)
                    and knoten.level == 0
                    and knoten.module
                ):
                    gefunden.add(knoten.module.split(".")[0])

    return gefunden


def test_alle_skripte_sind_da() -> None:
    """Die Werkzeuge aus `docs/AUFBAU.md` liegen auch vor.

    Raises:
        AssertionError: Wenn eines fehlt.
    """
    fehlend = [name for name in SKRIPTE if not (WURZEL / "scripts" / name).is_file()]

    assert fehlend == [], f"Es fehlen Skripte: {fehlend}"


def test_und_die_anleitung_nennt_kein_verschwundenes_skript() -> None:
    """Kein Skript darf in `AUFBAU.md` stehen, das es nicht mehr gibt.

    `bild_pruefen.py` stand dort drei Fassungen lang, obwohl es niemand
    aufrief und es eine private Schnittstelle benutzt.

    Raises:
        AssertionError: Wenn die Anleitung etwas nennt, das fehlt.
    """
    text = (WURZEL / "docs" / "AUFBAU.md").read_text(encoding="utf-8")

    genannt = set(re.findall(r"scripts/([a-z_]+\.py)", text))
    vorhanden = {name for name in SKRIPTE}

    assert genannt <= vorhanden, (
        f"`AUFBAU.md` nennt Skripte, die es nicht gibt: {sorted(genannt - vorhanden)}"
    )


def test_der_bildschirm_laesst_sich_lesen(tmp_path: Path) -> None:
    """Die private Schnittstelle, auf der beide Skripte aufbauen, gibt es noch.

    Args:
        tmp_path: Das Verzeichnis fuer die Datenbank. **Nicht** im Projekt:
            eine Datenbankdatei im Repository ist ein Fehler, und
            `tests/test_repository.py` schlaegt sofort an.
    """
    import asyncio

    async def lauf() -> str:
        app = FakturApp(tmp_path / "probelauf.db")
        async with app.run_test(size=(90, 30)) as pilot:
            await pilot.pause()
            return "\n".join(
                teil.text for teil in app.screen._compositor.render_strips()
            )

    bild = asyncio.run(lauf())

    assert "Angebot erstellen" in bild, (
        "Der Bildschirm liest sich nicht mehr. `ablauf_pruefen.py` und "
        "`bilder_speichern.py` gehen daran still vorbei, weil sie auf "
        "`screen._compositor` setzen — einer privaten Schnittstelle von "
        "Textual, die ohne Vorwarnung verschwinden darf."
    )


def test_jede_bibliothek_steht_in_der_liste() -> None:
    """Was der Code direkt benutzt, steht auch in `requirements.txt`.

    `rich` wurde dreimal direkt importiert und stand in keiner Liste. Es
    lief nur, weil Textual es zufällig mitinstalliert — ohne das hätte der
    erste, der Textual aufrüstet, ein `ModuleNotFoundError` bekommen.

    Raises:
        AssertionError: Wenn eine direkt benutzte Bibliothek fehlt.
    """
    liste = (WURZEL / "requirements.txt").read_text(encoding="utf-8")
    gepinnt = set(re.findall(r"^([a-z0-9_-]+)==", liste, re.M))

    importierte = _importe(WURZEL)
    benutzt = {paket for modul, paket in DIREKT.items() if modul in importierte}
    fehlend = sorted(benutzt - gepinnt)

    assert fehlend == [], (
        f"Diese Bibliotheken werden direkt benutzt, stehen aber nicht in "
        f"`requirements.txt`: {fehlend}"
    )


@pytest.mark.parametrize("name", sorted(SKRIPTE))
def test_die_skripte_sind_gueltiges_python(name: str) -> None:
    """Jedes Skript lässt sich zumindest lesen.

    Args:
        name: Der Dateiname im Ordner `scripts`.
    """
    quelle = (WURZEL / "scripts" / name).read_text(encoding="utf-8")

    ast.parse(quelle), f"{name} ist kein gültiges Python."
