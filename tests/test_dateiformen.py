"""Tests, die das Repository in Form halten.

Zwei Dinge, die beim Bearbeiten von Hand immer wieder verloren gehen und die
man erst bemerkt, wenn sie weh tun.
"""

from __future__ import annotations

from pathlib import Path

import pytest

WURZEL = Path(__file__).resolve().parents[1]

#: Dateien, die am Ende einen Zeilenumbruch brauchen.
TEXTENDEN = (
    ".py",
    ".sh",
    ".command",
    ".md",
    ".toml",
    ".txt",
    ".tcss",
    ".yml",
    ".gitignore",
)

#: Dateien, die keinen Zeilenumbruch am Ende haben *wollen*.
OHNE_UMBRUCH: tuple[str, ...] = ()


def _textdateien() -> list[Path]:
    """Sucht alle Textdateien im Repository.

    Returns:
        Die gefundenen Dateien.
    """
    gefunden: list[Path] = []

    for pfad in WURZEL.rglob("*"):
        if not pfad.is_file():
            continue
        if any(teil in pfad.parts for teil in (".git", ".venv", "daten", "beispiele")):
            continue
        if pfad.name in OHNE_UMBRUCH:
            continue
        if pfad.name.endswith(TEXTENDEN) or pfad.name == ".gitignore":
            gefunden.append(pfad)

    return sorted(gefunden)


def test_es_gibt_etwas_zu_pruefen() -> None:
    """Sonst waere der Test oben gruen, weil er nichts findet.

    Genau daran ist ein Wächter unauffaellig nutzlos.
    """
    assert len(_textdateien()) > 30


@pytest.mark.parametrize(
    "pfad", _textdateien(), ids=lambda p: str(p.relative_to(WURZEL))
)
def test_jede_datei_endet_mit_einem_zeilenumbruch(pfad: Path) -> None:
    """Jede Textdatei endet mit einem Zeilenumbruch.

    Das ist kein Schoenheitsfehler. Ein Shell-Skript ohne abschliessenden
    Zeilenumbruch laeuft unter ``/bin/sh`` nicht zuverlaessig — und
    ``start.command`` ist genau so eine Datei: Der Finder startet sie auf
    dem Mac ohne Terminal, und eine Fehlermeldung sieht dort niemand.

    Args:
        pfad: Die zu pruefende Datei.
    """
    inhalt = pfad.read_bytes()

    assert inhalt, f"{pfad.relative_to(WURZEL)} ist leer"
    assert inhalt.endswith(b"\n"), (
        f"{pfad.relative_to(WURZEL)} endet nicht mit einem Zeilenumbruch "
        f"(letztes Byte: {inhalt[-1:]!r})."
    )


@pytest.mark.parametrize(
    "pfad", _textdateien(), ids=lambda p: str(p.relative_to(WURZEL))
)
def test_keine_datei_hat_windows_zeilenenden(pfad: Path) -> None:
    """Kein ``\\r`` in einer Textdatei.

    Ein Skript mit ``\\r\\n`` gilt auf dem Mac als Befehl, den es nicht gibt.

    Args:
        pfad: Die zu pruefende Datei.
    """
    assert b"\r" not in pfad.read_bytes(), (
        f"{pfad.relative_to(WURZEL)} enthaelt ein Windows-Zeilenende."
    )


def test_die_startscripts_derfen_vom_finder_geoeffnet_werden() -> None:
    """``start.command`` braucht drei Dinge fuer den Doppelklick.

    Ein Fuehrungszeichen, damit das Betriebssystem weiss, in welcher
    Sprache es laeuft; das Bit zum Ausfuehren, weil der Finder sonst den
    Texteditor oeffnet; und einen Zeilenumbruch am Ende.
    """
    for name in ("start.sh", "start.command"):
        pfad = WURZEL / name

        assert pfad.is_file(), f"{name} fehlt"
        assert pfad.read_bytes().startswith(b"#!/"), f"{name} beginnt nicht mit #!"
        assert pfad.stat().st_mode & 0o111, (
            f"{name} ist nicht ausfuehrbar. Der Finder wuerde den "
            "Texteditor oeffnen statt das Programm zu starten."
        )
        assert pfad.read_bytes().endswith(b"\n"), f"{name} endet ohne Zeilenumbruch"
