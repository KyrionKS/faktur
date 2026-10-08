"""Tests für das Startscript.

Der Grund, warum die Einrichtung in Python und nicht in der Schale steht:
alles hier ist prüfbar, ohne ein Programm zu starten und ohne eine Minute
zu warten.

Geprüft werden die Wege, die man nicht selbst ausprobieren möchte: ein
Rechner ohne Python, ein zu altes Python, ein Rechner ohne pip im Python,
und der Normalfall, in dem alles schon da ist.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
import start

#: Ein alter Interpreter, wie ihn macOS gern mitliefert.
ALT = (3, 9, 6)

#: Ein neuer, wie ihn der Bauvorgang einrichtet.
NEU = (3, 12, 4)


def test_erst_nach_dem_holen_startet_er_mal_nicht_vorbei(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Beim ersten Start wird eingerichtet, und nur dann.

    Args:
        monkeypatch: Zum Umbiegen der Pfade.
        tmp_path: Ein Weg, der nach dem Test wieder wegkann.
    """
    umgebung = tmp_path / ".venv"
    monkeypatch.setattr(start, "ORDNER_UMGEBUNG", umgebung)
    monkeypatch.setattr(
        start, "DATEI_LISTE", Path(__file__).parent.parent / "requirements.txt"
    )

    called: list[str] = []
    monkeypatch.setattr(start, "_installiere", lambda: called.append("installiert"))

    assert start.umgebung_fehlt() is True
    start.lege_umgebung_an()
    assert called == ["installiert"]


def test_beim_zweiten_start_wird_nur_geholt(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Wenn die Umgebung da ist, wird sie nicht neu gebaut.

    Sonst wäre der zweite Start genauso langsam wie der erste, und das
    wäre der ganze Zweck der Sache kaputt.

    Args:
        monkeypatch: Zum Umbiegen der Pfade.
        tmp_path: Ein Weg, der nach dem Test wieder wegkann.
    """
    interpreter = tmp_path / ".venv" / "bin" / "python"
    interpreter.parent.mkdir(parents=True)
    interpreter.write_text("", encoding="utf-8")
    monkeypatch.setattr(start, "ORDNER_UMGEBUNG", tmp_path / ".venv")

    gebaut: list[str] = []
    geholt: list[str] = []
    gestartet: list[str] = []
    monkeypatch.setattr(start, "lege_umgebung_an", lambda: gebaut.append("x"))
    monkeypatch.setattr(start, "_installiere", lambda: geholt.append("x"))
    monkeypatch.setattr(start, "starte", lambda: gestartet.append("x") or 0)

    assert start.umgebung_fehlt() is False
    assert start.main() == 0

    assert gebaut == [], "Die Umgebung darf nicht neu gebaut werden"
    assert geholt == ["x"], "Die Bibliotheken werden immer geholt"
    assert gestartet == ["x"]
    assert interpreter.is_file()


def test_ein_zu_altes_python_bekommt_eine_erklaerung(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ein altes Python ist der häufigste Grund für einen Abbruch.

    Die Meldung muss sagen, welche Version gebraucht wird und was zu tun
    ist. Sonst steht man da mit drei Zeilen Text und weiß nichts.

    Args:
        monkeypatch: Zum Vortaeuschen einer alten Version.
    """
    monkeypatch.setattr(sys, "version_info", ALT)

    with pytest.raises(start.Fehler) as fehler:
        start.lege_umgebung_an()

    text = str(fehler.value)
    assert "3.11" in text
    assert "3.9" in text, "Die vorhandene Version muss genannt werden"
    assert "brew install" in text, "Es muss stehen, was zu tun ist"


def test_ein_python_ohne_pip_bekommt_die_richtige_meldung(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Auf vielen Linux-Systemen fehlt pip im mitgelieferten Python.

    Der Fehler lautet dann etwas von ensurepip, und wer ihn nicht kennt,
    sucht lange danach. Die Meldung muss das sagen.

    Args:
        monkeypatch: Zum Vortaeuschen des Fehlers.
    """
    monkeypatch.setattr(sys, "version_info", NEU)

    def platte(*args: object, **kwargs: object) -> None:
        raise RuntimeError("ensurepip is not available on this platform")

    monkeypatch.setattr(start.venv.EnvBuilder, "create", platte)

    with pytest.raises(start.Fehler) as fehler:
        start.lege_umgebung_an()

    text = str(fehler.value)
    assert "python3-venv" in text
    assert "brew install" in text


def test_ohne_bibliotheksliste_geht_es_nicht_weiter(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Fehlt die Liste der Abhängigkeiten, muss das gesagt werden.

    Args:
        monkeypatch: Zum Umbiegen des Weges.
        tmp_path: Ein Weg, der nach dem Test wieder wegkann.
    """
    monkeypatch.setattr(start, "DATEI_LISTE", tmp_path / "gibt-es-nicht.txt")

    with pytest.raises(start.Fehler) as fehler:
        start._installiere()

    assert "gibt-es-nicht.txt" in str(fehler.value)
    assert "Bibliotheken" in str(fehler.value)


def test_der_fehlertext_nennt_die_letzte_zeile(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Von pip kommen viele Zeilen. Die letzte sagt das Wesentliche.

    Args:
        monkeypatch: Zum Umbiegen der Pfade.
        tmp_path: Ein Weg, der nach dem Test wieder wegkann.
    """
    liste = tmp_path / "requirements.txt"
    liste.write_text("textual\n", encoding="utf-8")
    monkeypatch.setattr(start, "DATEI_LISTE", liste)
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args=[],
            returncode=1,
            stdout="",
            stderr="Auch egal\nERROR: Could not find a version\n",
        ),
    )

    with pytest.raises(start.Fehler) as fehler:
        start._installiere()

    assert "Could not find a version" in str(fehler.value)


def test_der_vernuenftige_fehlertext_nennt_die_moeglichen_ursachen(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Zwei Ursachen, die es bei pip auf fremden Rechnern wirklich gibt.

    Args:
        monkeypatch: Zum Umbiegen der Pfade.
        tmp_path: Ein Weg, der nach dem Test wieder wegkann.
    """
    liste = tmp_path / "requirements.txt"
    liste.write_text("textual\n", encoding="utf-8")
    monkeypatch.setattr(start, "DATEI_LISTE", liste)
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args=[], returncode=1, stdout="", stderr="irgendwas\n"
        ),
    )

    with pytest.raises(start.Fehler) as fehler:
        start._installiere()

    text = str(fehler.value)
    assert "externally-managed-environment" in text
    assert "No matching distribution found" in text


def test_beim_ersten_start_wird_es_angekuendigt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Vorher sagen, dass es dauert. Sonst hält man es für einen Hänger.

    Args:
        monkeypatch: Zum Vortaeuschen einer frischen Installation.
    """
    monkeypatch.setattr(start, "hole_datenbank", lambda: None)

    assert "Erster Start" in start.text_start()


def test_beim_zweiten_start_wird_nichts_angekuendigt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Kein Theater, wenn schon alles da ist.

    Args:
        monkeypatch: Zum Vortaeuschen einer vorhandenen Datenbank.
    """
    monkeypatch.setattr(start, "hole_datenbank", lambda: Path("da"))

    assert "Erster Start" not in start.text_start()


def test_ohne_logo_gibt_es_einen_hinweis(monkeypatch: pytest.MonkeyPatch) -> None:
    """Das Logo fehlt, die PDF kommen trotzdem.

    Args:
        monkeypatch: Zum Vortaeuschen eines fehlenden Logos.
    """
    monkeypatch.setattr(start, "logo_fehlt", lambda: True)

    text = start.text_logo()
    assert "logo.png" in text
    assert "daten/" in text, "Es muss stehen, wohin die Datei gehört"


def test_mit_logo_gibt_es_keinen_hinweis(monkeypatch: pytest.MonkeyPatch) -> None:
    """Kein Text, wenn es nichts zu sagen gibt.

    Args:
        monkeypatch: Zum Vortaeuschen eines vorhandenen Logos.
    """
    monkeypatch.setattr(start, "logo_fehlt", lambda: False)

    assert start.text_logo() == ""


def test_der_weg_zum_interpreter_zeigt_auf_die_umgebung() -> None:
    """Das Programm startet aus der eigenen Umgebung, nicht aus dem System."""
    assert start.python_aus_der_umgebung() == start.ORDNER_UMGEBUNG / "bin" / "python"


def test_das_programm_sagt_auf_zuruf_seine_version() -> None:
    """``python -m faktur --version`` darf nichts anderes tun.

    Das ist die erste Frage, die man einem Programm stellt, wenn es sich
    weigert zu starten. Antwortet es darauf schon falsch, stimmt die
    Python-Version nicht und der Rest ist umsonst.
    """
    ergebnis = subprocess.run(
        [sys.executable, "-m", "faktur", "--version"],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
        cwd=str(Path(start.__file__).resolve().parent),
    )

    assert ergebnis.returncode == 0, ergebnis.stderr

    from faktur import __version__

    assert __version__ in ergebnis.stdout
    assert "Hinweise" not in ergebnis.stdout, (
        "Die Versionsabfrage darf nichts weiter ausgeben — das Menü "
        "wäre mit auf dem Schirm."
    )
