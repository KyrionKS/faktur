#!/usr/bin/env python3
"""Baut das Programm als ausführbare Datei.

Auf macOS entsteht daraus ``dist/Faktur.app``, ein Programm mit Symbol, das
man doppelklicken kann. Auf anderen Systemen eine einzelne Datei, mit der
man dasselbe prüfen kann.

    .venv/bin/python scripts/app_bauen.py

Der Packer übersetzt nicht. Ein hier auf Linux gebautes Programm läuft auf
keinem Mac, und ein auf macOS gebautes hier nicht. Darum entsteht die Datei
auf dem Rechner, auf dem sie auch laufen soll.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import venv
from pathlib import Path

WURZEL = Path(__file__).resolve().parents[1]

#: Wohin das Ergebnis kommt.
AUSGABE = WURZEL / "dist"

#: Wohin das Symbol als macOS-Datei entsteht.
SYMBOL = WURZEL / "build" / "Faktur.icns"

#: Womit das Symbol aus dem PNG entsteht.
SYMBOL_QUELLE = WURZEL / "build" / "logo.png"

#: Die kleinste Python-Version, mit der sich bauen lässt.
MINDESTVERSION = (3, 11)

#: Der Packer. Er kommt bewusst nicht in requirements.txt, weil er ein
#: Werkzeug ist und keine Laufzeitabhängigkeit: im fertigen Programm ist
#: er nicht mehr enthalten.
PACKER = "pyinstaller>=6.10"

#: Die Seitenlängen, die macOS für ein Symbol erwartet.
SYMBOL_GROESSEN = (16, 32, 64, 128, 256, 512, 1024)


def pruefe_python() -> None:
    """Bricht ab, wenn der Interpreter zu alt ist.

    Raises:
        SystemExit: Mit einer verständlichen Meldung.
    """
    if sys.version_info < MINDESTVERSION:
        nötig = ".".join(str(teil) for teil in MINDESTVERSION)
        vorhanden = ".".join(str(teil) for teil in sys.version_info[:3])
        raise SystemExit(
            f"Gebaut wird mit Python ab {nötig}, hier läuft {vorhanden}.\n"
            "Auf einem Mac: brew install python@3.12"
        )


def lege_umgebung() -> Path:
    """Legt ein venv zum Bauen an und installiert alles Nötige.

    Returns:
        Der Pfad zum Python im venv.
    """
    ordner = WURZEL / ".buildvenv"

    if not (ordner / "bin" / "python").is_file():
        venv.EnvBuilder(with_pip=True).create(ordner)

    python = ordner / "bin" / "python"
    if sys.platform.startswith("win"):
        python = ordner / "Scripts" / "python.exe"

    if shutil.which(str(python)) is None and not python.is_file():
        raise SystemExit(f"Im venv fehlt der Interpreter: {python}")

    print("  Abhängigkeiten installieren")
    subprocess.run(  # noqa: S603
        [str(python), "-m", "pip", "install", "--quiet", "--upgrade", "pip"],
        check=True,
    )
    subprocess.run(  # noqa: S603
        [
            str(python),
            "-m",
            "pip",
            "install",
            "--quiet",
            "-r",
            str(WURZEL / "requirements.txt"),
            PACKER,
        ],
        check=True,
    )

    return python


def symbol_bauen() -> None:
    """Macht aus ``logo.png`` eine für macOS brauchbare Datei.

    macOS nimmt nur sein eigenes Format. Zwei Werkzeuge, die auf jedem Mac
    schon vorhanden sind, erzeugen es: ``sips`` für die Größen und
    ``iconutil`` für das Zusammenbauen.

    Fehlt eine Bildquelle, geht es ohne Symbol weiter. Ein zweifarbiges
    Programmsymbol wäre schöner, aber kein Grund für einen Abbruch.
    """
    if sys.platform != "darwin":
        print("  Symbol: nur auf macOS sinnvoll, wird übersprungen")
        return

    quelle = WURZEL.parent / "logo.png"
    if not quelle.is_file():
        print(f"  Symbol: keine Bildquelle unter {quelle}, wird übersprungen")
        return

    iconset = SYMBOL.with_suffix(".iconset")
    if iconset.is_dir():
        shutil.rmtree(iconset)
    iconset.mkdir(parents=True)

    print(f"  Symbol aus {quelle.name}")
    for groesse in SYMBOL_GROESSEN:
        subprocess.run(  # noqa: S603
            [
                "sips",
                "-z",
                str(groesse),
                str(groesse),
                str(quelle),
                "--out",
                str(iconset / f"icon_{groesse}x{groesse}.png"),
            ],
            check=True,
            capture_output=True,
        )

    subprocess.run(  # noqa: S603
        ["iconutil", "-c", "icns", str(iconset), "-o", str(SYMBOL)],
        check=True,
    )
    shutil.rmtree(iconset, ignore_errors=True)


def bauen(python: Path) -> None:
    """Ruft den Packer auf.

    Args:
        python: Der Interpreter aus dem Bau-venv.
    """
    print("  Programm bauen, das dauert einen Moment")
    subprocess.run(  # noqa: S603
        [
            str(python),
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            "--distpath",
            str(AUSGABE),
            "--workpath",
            str(WURZEL / "build" / "arbeit"),
            str(WURZEL / "faktur.spec"),
        ],
        check=True,
    )


def pruefe_ergebnis() -> None:
    """Sieht nach, ob das Ergebnis das Stylesheet enthält.

    Ohne die Datei startet das Programm nicht. Der Bauvorgang meldet das
    nicht, deshalb wird hier nachgesehen.

    Raises:
        SystemExit: Wenn die Datei fehlt.
    """
    programm = AUSGABE / ("Faktur.app" if sys.platform == "darwin" else "Faktur")
    if not programm.exists():
        raise SystemExit(f"Der Bauvorgang hat nichts erzeugt: {programm}")

    gefunden = list(programm.rglob("app.tcss"))
    if not gefunden:
        raise SystemExit(
            f"In {programm} fehlt die Datei app.tcss.\n"
            "Das Programm würde beim ersten Bild sterben. In faktur.spec "
            "muss app.tcss unter datas stehen."
        )

    print(f"  app.tcss ist dabei: {gefunden[0].name}")
    print(f"  Fertig: {programm}")


def main() -> int:
    """Baut das Programm.

    Returns:
        ``0``, wenn das Ergebnis da ist und geprüft wurde.
    """
    pruefe_python()
    version = f"{sys.version_info.major}.{sys.version_info.minor}"
    print(f"Faktur bauen für {sys.platform} (Python {version})")

    SYMBOL.parent.mkdir(parents=True, exist_ok=True)
    python = lege_umgebung()
    symbol_bauen()
    bauen(python)
    pruefe_ergebnis()

    print()
    print("Auf macOS startet das Programm mit einem Doppelklick.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
