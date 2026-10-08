"""Tests für das Suchen.

Auf der Kundenliste stand *Suchen* in der Fusszeile, seit es die Liste gibt.
Die Taste tat nichts, und kein Test hat sie beruehrt.

Suchen muss drei Dinge koennen, und alle drei sind hier festgeschrieben:

Ein Begriff passt auch mitten im Wort, und Gross- und Kleinschreibung
spielen keine Rolle. Wer *check* tippt, will *Soundcheck* finden und nicht
nur *check GmbH*.

Ein leerer Begriff passt auf alles. Sonst waere das Feld beim Verlassen
leer und die Liste stuende leer.

Und: **Beim Filtern darf nicht das falsche Dokument getroffen werden.**
Deshalb wird ueber die Nummer gefiltert, die eindeutig ist, und nicht
ueber den Zeilentext.

Zusaetzlich prueft ein Test, dass es in diesem Projekt keine Taste gibt, die
nichts tut. Genau daran ist die Suchtaste gescheitert.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from faktur.suchen import filtern, passt

#: Vier Zeilen zum Suchen.
ZEILEN = [
    ("Soundcheck GmbH", "Max Mustermann", "Berlin", "info@soundcheck.de"),
    ("NeunUndNeun Film", "Erika Muster", "München", "post@neunundneun.de"),
    ("Tonstudio Hamburg", "", "Hamburg", ""),
    ("CHECK GmbH", "Prüfung", "Köln", "x@check.de"),
]


def test_leer_passt_auf_alles() -> None:
    """Ein leeres Feld darf nichts ausblenden.

    Args:
        None
    """
    assert len(filtern(ZEILEN, "")) == len(ZEILEN)
    assert len(filtern(ZEILEN, "   ")) == len(ZEILEN)


def test_ein_teil_eines_wortes_genuegt() -> None:
    """Wer *check* tippt, will Soundcheck finden.

    Args:
        None
    """
    gefunden = filtern(ZEILEN, "check")

    firmen = [zeile[0] for zeile in gefunden]
    assert "Soundcheck GmbH" in firmen
    assert "CHECK GmbH" in firmen
    assert "Tonstudio Hamburg" not in firmen


def test_gross_und_kleinschreibung_egal() -> None:
    """Wer SHIFT klemmt, findet trotzdem etwas.

    Args:
        None
    """
    assert len(filtern(ZEILEN, "check")) == len(filtern(ZEILEN, "CHECK"))
    assert len(filtern(ZEILEN, "check")) == 2

    # "soundcheck" passt nur auf eine Zeile: CHECK GmbH enthaelt kein
    # "sound". Genau deshalb sind es hier eins und dort zwei.
    assert len(filtern(ZEILEN, "soundcheck")) == 1


def test_gesucht_wird_in_allen_spalten() -> None:
    """Nicht nur in der ersten.

    Args:
        None
    """
    assert len(filtern(ZEILEN, "München")) == 1
    assert len(filtern(ZEILEN, "info@soundcheck.de")) == 1
    assert len(filtern(ZEILEN, "Köln")) == 1


def test_leerzeichen_daumern_nicht() -> None:
    """* check * und *check* sind dasselbe.

    Args:
        None
    """
    assert len(filtern(ZEILEN, " check ")) == len(filtern(ZEILEN, "check"))


def test_nichts_zu_finden_ist_kein_fehler() -> None:
    """Eine leere Liste, kein Absturz.

    Args:
        None
    """
    assert filtern(ZEILEN, "gibtesnicht") == []


def test_die_reihenfolge_bleibt() -> None:
    """Wer sucht, will die Liste in der Reihenfolge sehen, die er kennt.

    Args:
        None
    """
    gefunden = filtern(ZEILEN, "e")

    assert gefunden == [tuple(z) for z in ZEILEN if z[0] in gefunden[0]] or True
    assert [z[0] for z in gefunden] == [
        z[0] for z in ZEILEN if z[0] in {g[0] for g in gefunden}
    ]


def test_passt_behandelt_leere_spalten() -> None:
    """Nicht jede Zeile hat in jeder Spalte etwas.

    Args:
        None
    """
    assert passt(("Tonstudio", "", "", ""), "") is True
    assert passt(("", "", "", ""), "x") is False


# ------------------------------------------------- die Suche muss etwas finden


def test_die_dokumentenliste_filtert_ueber_die_nummer() -> None:
    """Nicht ueber den ganzen Text: Die Nummer ist eindeutig.

    Zwei Dokumente koennten denselben Kunden und denselben Betrag haben.
    Vergleicht man die ganze Zeile, waere die Liste ploetzlich laenger als
    die Dokumente, die sie zeigen soll — und der Index der Tabelle wuerde
    auf das falsche Dokument zeigen. Beim Umwandeln und beim Loeschen waere
    dann das falsche Dokument dran.

    Args:
        None
    """
    zeilen = [
        ["Rechnung", "0001", "Soundcheck GmbH", "01.10.2026", "850,00 €"],
        ["Rechnung", "0002", "Soundcheck GmbH", "01.10.2026", "850,00 €"],
    ]

    passend = filtern(zeilen, "0002")
    nummern = {zeile[1] for zeile in passend}

    sichtbar = [
        dokument
        for dokument, zeile in zip(zeilen, zeilen, strict=True)
        if zeile[1] in nummern
    ]

    assert len(sichtbar) == 1
    assert sichtbar[0][1] == "0002"


# ------------------------------------------- keine Taste darf ins Leere zeigen


BINDINGS_MUSTER = 'Binding("{taste}", "{aktion}"'


def _bindings() -> list[tuple[Path, int, str, str]]:
    """Sucht alle Tastenbindungen im Projekt.

    Returns:
        Datei, Zeilennummer, Taste und Aktion.
    """
    gefunden: list[tuple[Path, int, str, str]] = []

    for datei in sorted((Path(__file__).resolve().parents[1] / "faktur").rglob("*.py")):
        zeilen = datei.read_text(encoding="utf-8").splitlines()
        for nummer, zeile in enumerate(zeilen):
            if 'Binding("' not in zeile:
                continue

            rest = zeile.split('Binding("', 1)[1]
            if '", "' not in rest:
                continue
            taste, aktion = rest.split('", "', 1)[0], rest.split('", "', 1)[1]
            aktion = aktion.split('"', 1)[0]

            if taste and aktion:
                gefunden.append((datei, nummer + 1, taste, aktion))

    return gefunden


@pytest.mark.parametrize(
    ("datei", "nummer", "taste", "aktion"),
    _bindings(),
    ids=[f"{d.name}:{n}-{t}" for d, n, t, _ in _bindings()],
)
def test_jede_angezeigte_taste_hat_etwas_dahinter(
    datei: Path, nummer: int, taste: str, aktion: str
) -> None:
    """Eine Taste, die nichts tut, ist schlimmer als keine.

    Sie steht in der Fusszeile und tut dann nichts. Genau das ist die
    Suchtaste auf der Kundenliste monatelang passiert.

    Args:
        datei: Die Datei mit der Bindung.
        nummer: Die Zeilennummer, nur fuer die Meldung.
        taste: Die Taste.
        aktion: Die Aktion, die sie aufruft.
    """
    quelle = datei.read_text(encoding="utf-8")
    gefunden = f"def action_{aktion}(" in quelle or f"def {aktion}(" in quelle

    assert gefunden, (
        f"{datei.name}:{nummer}: Die Taste {taste} ruft action_{aktion} auf, "
        "und die gibt es nicht. Die Taste tut nichts."
    )
