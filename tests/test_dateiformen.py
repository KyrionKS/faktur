"""Tests, die das Repository in Form halten.

Zwei Dinge, die beim Bearbeiten von Hand immer wieder verloren gehen und die
man erst bemerkt, wenn sie weh tun.
"""

from __future__ import annotations

import re
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


#: Ein Verweis in einem Textdokument: [Text](Ziel)
VERWEIS = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")


@pytest.mark.parametrize(
    "text", sorted(WURZEL.rglob("*.md")), ids=lambda p: str(p.relative_to(WURZEL))
)
def test_jeder_verweis_zeigt_auf_etwas(text: Path) -> None:
    """Kein toter Verweis in den Dokumenten.

    Auf GitHub fallen die erst auf, wenn jemand klickt. Und geklickt wird,
    wenn man wissen will, wie man das Programm startet.

    Args:
        text: Das Dokument, das geprueft wird.
    """
    if any(teil in text.parts for teil in (".git", ".venv", "daten", "beispiele")):
        return

    inhalt = text.read_text(encoding="utf-8")

    tot = []
    for ziel in VERWEIS.findall(inhalt):
        if ziel.startswith(("http://", "https://", "#", "mailto:")):
            continue
        # Anker am Ende abtrennen: [Text](datei.md#abschnitt)
        pfad = ziel.split("#", 1)[0]
        if not pfad:
            continue
        if not (text.parent / pfad).exists():
            tot.append(ziel)

    assert tot == [], (
        f"{text.relative_to(WURZEL)} zeigt auf nichts: {', '.join(sorted(set(tot)))}"
    )


def test_das_readme_bleibt_kurz() -> None:
    """Das README ist die Seite, die jeder zuerst sieht.

    Es soll sagen, was es ist und wie es startet. Alles andere gehoert nach
    ``docs/``. Diese Grenze ist eine Entscheidung, kein Zufall, deshalb
    steht sie hier und nicht nur in meinem Kopf.
    """
    zeilen = (WURZEL / "README.md").read_text(encoding="utf-8").splitlines()

    ueberschreitungen = [z for z in zeilen if z.startswith("## ")]
    assert len(ueberschreitungen) <= 4, (
        f"Das README hat {len(ueberschreitungen)} Abschnitte. Gehoert nach docs/: "
        f"{ueberschreitungen}"
    )


def test_im_projektordner_liegt_nur_die_readme() -> None:
    """Alle Anleitungen liegen unter ``docs/``, nicht daneben.

    Drei Anleitungen im Wurzelordner, eine davon mit einem Verweis auf die
    nächste: Man sucht sie am falschen Ort, weil sie nicht am erwarteten
    Platz liegt. Das ist die ganze Begründung.

    Das README bleibt, weil GitHub es dort erwartet — dort findet jeder, der
    die Repository-Seite aufmacht.
    """
    im_ordner = sorted(pfad.name for pfad in WURZEL.glob("*.md") if pfad.is_file())

    assert im_ordner == ["README.md"], (
        f"Im Projekt-Root liegen Anleitungen neben dem README: {im_ordner}. "
        "Sie gehören nach docs/."
    )


def test_und_die_liegen_dort_auch_hin() -> None:
    """Sonst wäre die erste Regel nur die Hälfte."""
    gefunden = {pfad.name for pfad in (WURZEL / "docs").glob("*.md")}

    assert gefunden, "Unter docs/ liegt keine Anleitung"

    doppelt = gefunden - {"ANLEITUNG.md", "AUFBAU.md", "BEDIENUNG.md"}
    assert doppelt == set(), f"Unerwartet im docs-Ordner: {sorted(doppelt)}"
