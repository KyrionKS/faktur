"""Tests, die das Repository vor fremden Daten schützen.

In ``daten/`` liegen die Datenbank, das Logo und die PDF des Benutzers: IBAN,
Steuernummer, Anschrift, Kundennamen. Nichts davon darf je im Repository
landen, denn es wird veröffentlicht.

``daten/`` steht in der ``.gitignore``, aber eine Ausnahme in der Liste oder
ein ``git add -f`` umgeht das. Dieser Test schlägt an, sobald so etwas
passiert.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

#: Was niemals im Repository stehen darf.
VERBOTENE_ENDUNGEN = (".db", ".db.bak", ".sqlite", ".sqlite3", ".pdf", ".bak")

#: Ordner, deren Inhalt dem Benutzer gehört.
GESCHUETZT = ("daten/",)


def _git(*args: str) -> str | None:
    """Führt einen Git-Befehl aus.

    Args:
        args: Die Befehlszeile.

    Returns:
        Die Ausgabe, oder ``None``, wenn Git nicht da ist oder der Aufruf
        fehlschlägt.
    """
    if shutil.which("git") is None:
        return None
    try:
        ergebnis = subprocess.run(  # noqa: S603
            ["git", *args],
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None
    return ergebnis.stdout


def test_datenordner_steht_in_der_ignore_liste() -> None:
    """``daten/`` muss in der ``.gitignore`` stehen."""
    inhalt = (Path(__file__).resolve().parents[1] / ".gitignore").read_text(
        encoding="utf-8"
    )
    zeilen = {zeile.strip() for zeile in inhalt.splitlines()}

    for ordner in GESCHUETZT:
        assert ordner in zeilen, (
            f"{ordner} fehlt in der .gitignore. Dort liegen die Daten des "
            "Benutzers und dürfen nicht ins Repository."
        )


def test_keine_fremden_dateien_werden_verfolgt() -> None:
    """Keine Datenbank, kein Backup und keine PDF im Repository.

    Läuft nicht, wenn kein Git zur Hand ist, etwa in einem Quellarchiv.
    """
    ausgabe = _git("ls-files")
    if ausgabe is None:
        pytest.skip("Kein Git vorhanden")

    verfolgt = [zeile for zeile in ausgabe.splitlines() if zeile.strip()]
    schuldig = [
        zeile
        for zeile in verfolgt
        if zeile.startswith(GESCHUETZT) or zeile.endswith(VERBOTENE_ENDUNGEN)
    ]

    assert schuldig == [], (
        "Im Repository sind Dateien des Benutzers: "
        + ", ".join(schuldig)
        + ". Sie werden veröffentlicht und gehören dort nicht hin."
    )


def test_der_datenordner_wird_ignoriert() -> None:
    """Git muss ``daten/`` wirklich auslassen, nicht nur in der Liste stehen.

    Das prüft die Wirkung statt der Absicht.
    """
    ergebnis = _git("check-ignore", "-v", "daten/faktur.db")
    if ergebnis is None:
        pytest.skip("Kein Git vorhanden")

    assert ".gitignore" in ergebnis, (
        "daten/faktur.db wird nicht ignoriert. Die Datei würde beim "
        "Hochladen mitgehen."
    )


def test_die_ignore_liste_hat_keine_gefaehrliche_ausnahme() -> None:
    """Keine Ausnahme, die ``daten/`` wieder freigibt.

    Ein ``!daten/faktor.db`` in der ``.gitignore`` hebt genau diese eine
    Datei vom Ausschluss aus.
    """
    inhalt = (Path(__file__).resolve().parents[1] / ".gitignore").read_text(
        encoding="utf-8"
    )

    ausnahmen = [
        zeile.strip()
        for zeile in inhalt.splitlines()
        if zeile.strip().startswith("!")
    ]

    gefaehrlich = [
        zeile
        for zeile in ausnahmen
        if zeile.lstrip("!").startswith("daten/")
    ]

    assert gefaehrlich == [], (
        "Die .gitignore nimmt Ausnahmen für den Datenordner: "
        + ", ".join(gefaehrlich)
    )


def test_keine_fremden_daten_in_der_historie() -> None:
    """Auch früher committete Dateien dürfen keine Daten enthalten.

    Eine Datenbank, die einmal im Repository war und dann gelöscht wurde,
    steckt sonst weiter im Verlauf und wird mitveröffentlicht.
    """
    ausgabe = _git("log", "--all", "--diff-filter=A", "--name-only", "--pretty=format:")
    if ausgabe is None:
        pytest.skip("Kein Git vorhanden")

    dateien = {zeile.strip() for zeile in ausgabe.splitlines() if zeile.strip()}
    schuldig = [
        zeile
        for zeile in dateien
        if zeile.startswith(GESCHUETZT) or zeile.endswith(VERBOTENE_ENDUNGEN)
    ]

    assert schuldig == [], (
        "Im Verlauf stehen Dateien des Benutzers: "
        + ", ".join(sorted(schuldig)[:10])
        + ". Sie werden mitveröffentlicht und müssen mit git filter-repo "
        "herausgeschrieben werden."
    )