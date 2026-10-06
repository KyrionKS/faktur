"""Tests für die Pfadauflösung.

Der Unterschied zwischen „neben dem Programm" aus dem Quelltext und „neben
dem Programm" im Bundle ist der Punkt, an dem die Daten sonst im Nichts
landen. Beide Wege werden hier nachgestellt.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from faktur import orte


def test_aus_dem_quelltext_liegt_daten_neben_dem_programm() -> None:
    """Ohne Packer ist der Datenordner das Verzeichnis über dem Paket."""
    erwartet = Path(orte.__file__).resolve().parent.parent / "daten"
    assert orte.datenordner() == erwartet


@pytest.mark.parametrize(
    ("einstieg", "erwartet"),
    [
        (
            "/Users/kyrion/Faktur/Faktur.app/Contents/MacOS/Faktur",
            "/Users/kyrion/Faktur/daten",
        ),
        (
            "/Users/kyrion/Programme/Faktur.app/Contents/MacOS/Faktur",
            "/Users/kyrion/Programme/daten",
        ),
        (
            "/Users/kyrion/Faktur/Meine apps/Faktur.app/Contents/MacOS/Faktur",
            "/Users/kyrion/Faktur/Meine apps/daten",
        ),
    ],
)
def test_im_bundle_liegt_daten_neben_der_app(
    monkeypatch: pytest.MonkeyPatch, einstieg: str, erwartet: str
) -> None:
    """Die Daten liegen neben der ``.app``, nicht darin.

    Args:
        monkeypatch: Zum Setzen von ``sys.executable``.
        einstieg: Der Pfad, den ein Bundle melden würde.
        erwartet: Wohin die Daten gehören.
    """
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", einstieg)

    assert orte.datenordner() == Path(erwartet)


def test_im_bundle_werden_die_daten_nicht_ins_bundle_geschrieben(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Kein Pfad darf innerhalb der ``.app`` liegen.

    Args:
        monkeypatch: Zum Setzen von ``sys.executable``.
    """
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(
        sys, "executable", "/Users/kyrion/Faktur/Faktur.app/Contents/MacOS/Faktur"
    )

    ordner = orte.datenordner()

    assert "Faktur.app" not in ordner.parts
    assert ordner.is_relative_to(Path("/Users/kyrion/Faktur"))


def test_ohne_app_im_pfad_gewinnt_der_elternordner() -> None:
    """Ein Programm ohne Bundle kommt mit dem Elternordner aus."""
    einstieg = Path("/opt/faktur/bin/faktur")
    assert orte.neben_programm(einstieg) == Path("/opt/faktur/bin")


def test_die_daten_dateien_liegen_im_datenordner() -> None:
    """Datenbank, Logo und Dokumente teilen sich einen Ordner."""
    ordner = orte.datenordner()

    assert orte.datenbank().parent == ordner
    assert orte.logo().parent == ordner
    assert orte.dokumente().parent == ordner
    assert orte.datenbank().name == "faktur.db"
    assert orte.logo().name == "logo.png"
    assert orte.dokumente().name == "Dokumente"


def test_ohne_bundle_wird_nicht_behauptet_man_sei_im_bundle() -> None:
    """ "Im Bundle" behauptet der Packer, nicht der Pfad."""
    if sys.version_info >= (3, 11) and "frozen" in sys.modules:
        pytest.fail("sys.frozen gehört nicht in sys.modules")
    assert orte.im_bundle() is False


def test_der_datenordner_heisst_immer_gleich(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Im Bundle und aus dem Quelltext heißt er gleich.

    Sonst sucht man auf dem Mac das Programm durch und die Daten direkt
    daneben, ohne sie zu finden.

    Args:
        monkeypatch: Zum Setzen von ``sys.executable``.
    """
    aus_quelltext = orte.datenordner()
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(
        sys, "executable", "/Users/kyrion/Faktur/Faktur.app/Contents/MacOS/Faktur"
    )
    im_bundle = orte.datenordner()

    assert aus_quelltext.name == im_bundle.name == orte.DATENORDNERNAME


def test_im_bundle_liegt_der_datenordner_nicht_im_programmordner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Der Datenordner ist ein eigener Ordner, nicht der mit dem Programm.

    Args:
        monkeypatch: Zum Setzen von ``sys.executable``.
    """
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(
        sys, "executable", "/Users/kyrion/Faktur/Faktur.app/Contents/MacOS/Faktur"
    )

    ordner = orte.datenordner()
    neben = orte.neben_programm(
        Path("/Users/kyrion/Faktur/Faktur.app/Contents/MacOS/Faktur")
    )

    assert ordner != neben
    assert ordner.parent == neben
