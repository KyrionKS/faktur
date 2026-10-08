"""Tests für die Gestaltung der PDF.

Der wichtigste Test ist der erste: die Größen sind jetzt Anteile statt
fester Zahlen. Das ist nur dann eine Verbesserung und kein Umbau, wenn die
Anteile bei der Standardgröße genau die Zahlen ergeben, die vorher fest
eingetragen waren. Sonst hätte man beim Umbau jedes Dokument ein wenig
verschoben, ohne es zu merken.

Die Zahlen in :data:`ERWARTET` sind der Stand vor dem Umbau, abgelesen aus
der damaligen ``gestaltung.stile()``.
"""

from __future__ import annotations

import pytest
from faktur import gestaltung

#: Stilname: (Schriftgröße, Zeilenabstand) bei der Standardgröße.
#: Aus der Fassung vor der Umstellung auf Anteile.
ERWARTET = {
    "firma": (13.0, 16.0),
    "empfaenger": (10.0, 14.0),
    "art": (17.0, 21.0),
    "kopf_daten": (9.5, 13.0),
    "absatz": (9.5, 14.0),
    "anrede": (9.5, 14.0),
    "tab_kopf": (8.0, 11.0),
    "tab_text": (9.5, 13.0),
    "tab_zahl": (9.5, 13.0),
    "tab_zahl_fett": (9.5, 13.0),
    "summe": (12.0, 16.0),
    "rabatt_text": (9.5, 13.0),
    "rabatt_zahl": (9.5, 13.0),
    "klein": (7.5, 10.0),
}


@pytest.mark.parametrize(("name", "soll"), sorted(ERWARTET.items()))
def test_die_standardgroesse_ergibt_die_alten_zahlen(name: str, soll: tuple) -> None:
    """Bei der Standardgröße kommt genau heraus, was vorher drinstand.

    Args:
        name: Der Name des Stils.
        soll: Die Schriftgröße und der Zeilenabstand aus der alten Fassung.
    """
    assert gestaltung.groesse_von(name) == soll[0]
    assert gestaltung.zeilen_von(name) == soll[1]


def test_die_gebauten_stile_passen_zu_den_anteilen() -> None:
    """Auch das, was reportlab bekommt, muss den Anteilen folgen.

    Sonst wäre :func:`gestaltung.groesse_von` richtig und die PDF
    trotzdem falsch.
    """
    gebaut = gestaltung.stile()

    for name, (groesse, zeilen) in ERWARTET.items():
        assert gebaut[name].fontSize == groesse
        assert gebaut[name].leading == zeilen


def test_es_gibt_genau_die_stile_die_die_pdf_braucht() -> None:
    """Nichts ohne Verwendung, nichts ohne Ersatz.

    Vier Stile aus der alten Fassung wurden nirgends benutzt. Sie sind
    weg, und dieser Test verhindert, dass neue dazukommen.

    Es sind genau die, die in :data:`ERWARTET` stehen.
    """
    assert set(gestaltung.STILE) == set(ERWARTET)
    assert set(gestaltung.stile()) == set(ERWARTET)


def test_die_drei_groessen_sind_vorhanden() -> None:
    """Klein, normal, gross — in aufsteigender Reihenfolge."""
    assert list(gestaltung.GRUESSEN) == ["klein", "normal", "gross"]
    werte = list(gestaltung.GRUESSEN.values())
    assert werte == sorted(werte)
    assert werte[1] == 1.0, "Die Standardgröße muss genau 1.0 sein"


@pytest.mark.parametrize("name", sorted(ERWARTET))
def test_alle_stile_wachsen_mit_der_groesse(name: str) -> None:
    """Schrift *und* Abstand müssen mitgehen.

    Wächst nur die Schrift, klebt die Zeile an der nächsten. Genau das
    ist der Grund, warum beides aus einem Faktor kommt.

    Args:
        name: Der Name des Stils.
    """
    klein = gestaltung.zeilen_von(name, gestaltung.GRUESSEN["klein"])
    normal = gestaltung.zeilen_von(name)
    gross = gestaltung.zeilen_von(name, gestaltung.GRUESSEN["gross"])

    assert klein < normal < gross


def test_die_schrift_waechst_um_denselben_anteil_wie_der_abstand() -> None:
    """Das Verhältnis von Schrift zu Abstand bleibt gleich.

    Sonst sieht „groß" aus wie „groß und eng".
    """
    for name in ERWARTET:
        for faktor in gestaltung.GRUESSEN.values():
            verhaeltnis = gestaltung.zeilen_von(name, faktor) / gestaltung.groesse_von(
                name, faktor
            )
            soll = ERWARTET[name][1] / ERWARTET[name][0]
            assert verhaeltnis == pytest.approx(soll, abs=0.001), (
                f"{name} bei Faktor {faktor}: Verhältnis {verhaeltnis:.4f} "
                f"statt {soll:.4f}"
            )


def test_der_platz_um_absaetze_wächst_mit() -> None:
    """Der Abstand zwischen den Absätzen gehört zur Schrift."""
    for faktor in gestaltung.GRUESSEN.values():
        assert gestaltung.stile(faktor)["absatz"].spaceAfter == round(7.0 * faktor, 2)
        assert gestaltung.stile(faktor)["anrede"].spaceAfter == round(9.0 * faktor, 2)


@pytest.mark.parametrize("kaputt", ["", "   ", "riesig", "GROSS", "normal ", None])
def test_eine_unbekannte_groesse_ist_die_standardgroesse(kaputt) -> None:
    """Ein falscher Wert darf das Dokument nicht verziehen.

    Kommt aus einer alten Datenbank, aus einem Tippfehler oder von Hand
    in die Einstellungen geschrieben.

    Args:
        kaputt: Der Wert, der in der Einstellung stehen könnte.
    """
    assert gestaltung.groesse_faktor(kaputt or "") == 1.0


def test_die_fusszeile_waechst_mit_der_textgroesse() -> None:
    """Die Fußzeile wird auf die Leinwand gezeichnet, nicht als Absatz.

    Sie hat deshalb keinen Stil, sondern nur den Anteil des Kleinststils.
    Wächst sie nicht mit, schrumpft sie bei „groß" optisch weg.
    """
    assert gestaltung.STILE["klein"].groesse == gestaltung.KLEIN_FAKTOR

    # Das ist der Wert, mit dem die Fußzeile gezeichnet wird.
    assert gestaltung.groesse_von("klein", gestaltung.GRUESSEN["gross"]) == round(
        gestaltung.GRUND * gestaltung.KLEIN_FAKTOR * 1.1, 2
    )
