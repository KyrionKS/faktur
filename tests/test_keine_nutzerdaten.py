"""Tests, die nicht an die Daten des Benutzers heranreichen.

Der Vorfall, der diesen Test ausgelöst hat: Ein Test rief
``einstellungen.logo_uebernehmen()`` auf. Das kopiert in den echten
Datenordner des Projekts und überschrieb dabei das Logo des Benutzers mit
17 Bytes Text. Es fiel nur deshalb auf, weil das Programm danach nicht mehr
startete — die Sicherung in ``~/Faktur-Stammdaten`` war die Rettung.

Ein Testlauf darf die Daten des Benutzers nie verändern. Dieser Test
verhindert das, indem er vorher und nachher den *Inhalt* vergleicht. Ein
Vergleich der Dateinamen genügt nicht: ``logo.png`` gab es schon, es wurde
nur überschrieben.

Für die Datenbank gilt das seit Anfang an: ``tests/conftest.py`` legt sie
mit :func:`faktur.db.verbinden` in ein temporäres Verzeichnis.
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

import pytest

WURZEL = Path(__file__).resolve().parents[1]

#: Der echte Datenordner des Projekts. Er gehört dem Benutzer.
DATEN = WURZEL / "daten"

#: Dieser Test selbst. Er muss sich ausschließen, sonst startet er den
#: Testsatz, der ihn wieder enthält, der wieder den Testsatz startet.
SELBST = (
    f"{Path(__file__).relative_to(WURZEL)}::test_der_testlauf_fasst_die_daten_nicht_an"
)


def _abdruck(ordner: Path) -> dict[str, str]:
    """Bildet einen Ordner als Namen und Prüfsummen ab.

    Args:
        ordner: Der Ordner, nicht rekursiv.

    Returns:
        Der Name der Datei und ihre Prüfsumme.
    """
    if not ordner.is_dir():
        return {}

    return {
        pfad.name: hashlib.sha256(pfad.read_bytes()).hexdigest()
        for pfad in sorted(ordner.iterdir())
        if pfad.is_file()
    }


def _lauf() -> subprocess.CompletedProcess:
    """Lässt den Testsatz ohne diesen Test laufen.

    Returns:
        Das Ergebnis des Laufs.
    """
    return subprocess.run(  # noqa: S603
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "--deselect",
            SELBST,
        ],
        capture_output=True,
        text=True,
        timeout=900,
        check=False,
        cwd=str(WURZEL),
    )


@pytest.mark.skipif(
    not DATEN.is_dir(), reason="Kein Datenordner im Projekt, es gibt nichts zu schützen"
)
def test_der_testlauf_fasst_die_daten_nicht_an() -> None:
    """Kein Test darf im echten Datenordner etwas anlegen oder verändern.

    Der Testlauf läuft ein zweites Mal, mit sich selbst. Das ist der Preis
    dafür, dass hier nichts passieren kann: Der Wächter prüft genau den Weg,
    den er selbst geht.
    """
    vorher = _abdruck(DATEN)

    ergebnis = _lauf()

    nachher = _abdruck(DATEN)

    assert ergebnis.returncode == 0, (
        "Der Testlauf ist fehlgeschlagen, das Vergleichsergebnis sagt nichts:\n"
        f"{ergebnis.stdout[-2000:]}"
    )

    veraendert = {
        name: (vorher.get(name, "(neu)"), nachher.get(name, "(weg)"))
        for name in set(vorher) | set(nachher)
        if vorher.get(name) != nachher.get(name)
    }

    assert veraendert == {}, (
        "Der Testlauf hat die Daten des Benutzers verändert: "
        f"{veraendert}. Er darf nur in sein temporäres Verzeichnis schreiben."
    )


def test_jeder_test_der_ein_logo_ablegt_sagt_wohin() -> None:
    """Die Stellen, an denen ein Test ein Logo ablegt, brauchen ein Ziel.

    Ohne den letzten Parameter landet das Bild im Datenordner des
    Benutzers — das hat schon zweimal das Logo zerstört.
    """
    verdächtig: list[str] = []

    for datei in sorted((WURZEL / "tests").rglob("*.py")):
        if datei.name == Path(__file__).name:
            # Diese Datei nennt den Aufruf in ihrer Beschreibung.
            continue

        zeilen = datei.read_text(encoding="utf-8").splitlines()
        for nummer, zeile in enumerate(zeilen):
            if "logo_uebernehmen" not in zeile or zeile.lstrip().startswith("#"):
                continue

            # Der letzte Parameter des Aufrufs muss das Ziel sein. Er kann
            # in der nächsten Zeile stehen.
            abschnitt = " ".join(zeilen[nummer : nummer + 3])
            abschnitt = abschnitt.split("logo_uebernehmen", 1)[1]

            # Es zählt, dass nach dem Bildpfad ein zweites Argument steht.
            argumente = abschnitt.split(")", 1)[0]
            if "," not in argumente:
                verdächtig.append(f"{datei.relative_to(WURZEL)}:{nummer + 1}")

    assert verdächtig == [], (
        "Diese Stellen legen ein Logo im echten Datenordner ab. Sie brauchen "
        f"als zweiten Parameter ein temporäres Verzeichnis: {verdächtig}"
    )
