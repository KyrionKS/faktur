"""Tests für die Bedienliste des Bildschirms *Aussehen*.

Getestet werden die zwei Entscheidungen, die ohne Oberfläche auskommen:
welcher Wert als nächster kommt und was beim Umschalten passiert. Beides
steht in reinen Funktionen, damit man es hier prüfen kann.

Die Oberfläche selbst wird nicht getestet. Sie zu zeichnen und zu
bedienen loest keinen Test, sondern nur Aerger — der Ablauf wird von
``scripts/ablauf_pruefen.py`` gefahren.
"""

from __future__ import annotations

import pytest
from faktur import bloecke
from faktur.einstellungsliste import bauen, naechster_wert, schaltet_um

#: Die Werte einer Größe in ihrer Reihenfolge.
GROESSEN = ("klein", "normal", "gross")

#: Die Blöcke in der Reihenfolge, in der sie im Bildschirm stehen.
BLOECKE = [(b.name, b.ort, b.titel) for b in bloecke.BLOECKE]


# ------------------------------------------------------------------ naechster_wert


def test_rechts_waechst_der_wert() -> None:
    """ ""Weiter" geht eine Stelle nach vorn."""
    assert naechster_wert(GROESSEN, "klein", 1) == "normal"
    assert naechster_wert(GROESSEN, "normal", 1) == "gross"


def test_links_waechst_er_nach_links() -> None:
    """ "Zurück" geht eine Stelle zurück."""
    assert naechster_wert(GROESSEN, "gross", -1) == "normal"
    assert naechster_wert(GROESSEN, "normal", -1) == "klein"


def test_am_ende_wird_nicht_gewirbelt() -> None:
    """Wer dreimal nach rechts drückt, bleibt stehen.

    Gewickelt würde man unerwartet wieder bei *klein* landen, ohne es zu
    merken — die Hand ist schneller als das Nachdenken.
    """
    assert naechster_wert(GROESSEN, "gross", 1) == "gross"
    assert naechster_wert(GROESSEN, "klein", -1) == "klein"


def test_ein_wert_von_weit_herum_wird_akzeptiert() -> None:
    """Wer per Hand eine unbekannte Größe einträgt, landet bei der ersten.

    Args:
        None
    """
    assert naechster_wert(GROESSEN, "riesig", 1) == "klein"
    assert naechster_wert(GROESSEN, "riesig", -1) == "klein"
    assert naechster_wert(GROESSEN, "", 1) == "klein"


@pytest.mark.parametrize("richtung", [0, 2, -5])
def test_ohne_richtung_aendert_sich_nichts(richtung: int) -> None:
    """Nur rechts und links sind Richtungen.

    Args:
        richtung: Etwas, das keine Richtung ist.
    """
    assert naechster_wert(GROESSEN, "normal", richtung) == "normal"


def test_eine_leere_liste_liefert_ihren_wert_zurueck() -> None:
    """Ohne Werte gibt es nichts zu wählen."""
    assert naechster_wert((), "normal", 1) == "normal"


# ------------------------------------------------------------------ schaltet_um


def test_ein_ausgeschalteter_block_geht_an() -> None:
    assert schaltet_um(frozenset(), "logo") == frozenset({"logo"})


def test_ein_eingeschalteter_block_geht_aus() -> None:
    assert schaltet_um(frozenset({"logo"}), "logo") == frozenset()


def test_umschalten_aendert_nur_den_genannten_block() -> None:
    """Sonst verschwände beim Klick auf einen Kästchen ein anderes."""
    vorher = frozenset({"firma", "logo"})
    nachher = schaltet_um(vorher, "logo")

    assert "firma" in nachher
    assert "logo" not in nachher


def test_zweimal_umschalten_gibt_das_urspruengliche_zurueck() -> None:
    vorher = frozenset({"firma", "logo", "bank"})

    assert schaltet_um(schaltet_um(vorher, "bank"), "bank") == vorher


def test_alle_bloecke_aus_schaltet_sich_der_reihe_nach_aus() -> None:
    """Am Ende steht keiner mehr an."""
    an = frozenset(block.name for block in bloecke.BLOECKE)

    for name in list(an):
        an = schaltet_um(an, name)

    assert an == frozenset()


# ------------------------------------------------------------------------ bauen


def test_die_liste_beginnt_mit_drei_zeilen_und_den_groessen() -> None:
    """Dokumentart, Logogröße, Schriftgröße.

    Args:
        None
    """
    zeilen = bauen("angebot", "mittel", "normal", BLOECKE, frozenset({"logo"}))

    assert zeilen[0].art == "art"
    assert zeilen[0].titel == "Dokumentart"
    assert zeilen[0].wert == "angebot"
    assert zeilen[1].titel == "Logogröße"
    assert zeilen[1].wert == "mittel"
    assert zeilen[2].titel == "Schriftgröße"
    assert zeilen[2].wert == "normal"


def test_auf_der_liste_steht_jeder_block_einmal() -> None:
    """Dreizehn Blöcke, dreizehn Zeilen, keine doppelt."""
    zeilen = bauen("rechnung", "mittel", "normal", BLOECKE, frozenset({"logo"}))

    namen = [zeile.block for zeile in zeilen if zeile.art == "block"]

    assert namen == [name for name, _ort, _titel in BLOECKE]
    assert len(set(namen)) == len(namen)


def test_die_liste_zeigt_die_eingeschalteten_bloecke() -> None:
    """Was in der Datenbank an ist, steht in der Liste an."""
    an = frozenset({"firma", "logo", "bank"})

    zeilen = bauen("rechnung", "mittel", "normal", BLOECKE, an)

    for zeile in zeilen:
        if zeile.art != "block":
            continue
        assert zeile.an == (zeile.block in an), zeile.block


def test_jede_blockgruppe_bekommt_genau_eine_ueberschrift() -> None:
    """Sonst stünde „Absender" dreimal im Bild.

    Args:
        None
    """
    zeilen = bauen("angebot", "mittel", "normal", BLOECKE, frozenset())

    gruppen = [zeile.gruppe for zeile in zeilen if zeile.gruppe]

    assert gruppen == ["Absender", "Abschluss", "Fußzeile"]


def test_die_groessen_stehen_ueber_dem_ersten_block() -> None:
    """Sonst wäre der Bildschirm nicht am Stück zu sehen."""
    zeilen = bauen("angebot", "mittel", "normal", BLOECKE, frozenset())

    erster_block = next(
        nummer for nummer, zeile in enumerate(zeilen) if zeile.art == "block"
    )

    assert erster_block == 3


def test_alle_werte_einer_groesse_stehen_zur_wahl() -> None:
    """Die Liste, durch die ← und → gehen."""
    zeilen = bauen("angebot", "mittel", "normal", BLOECKE, frozenset())

    assert zeilen[1].werte == ("klein", "mittel", "gross")
    assert zeilen[2].werte == ("klein", "normal", "gross")
    assert zeilen[0].werte == ("angebot", "rechnung")
