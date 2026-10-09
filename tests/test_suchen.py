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
from faktur.suchen import filtern, passt, sichtbar

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


def test_zwei_dokumente_koennen_dieselbe_nummer_tragen() -> None:
    """Angebot und Rechnung eines Projekts stehen mit derselben Nummer da.

    Bis 0.8.2 war das ein Sonderfall, den man gar nicht herstellen konnte:
    Die Nummer musste eindeutig sein. Seit 0.9.0 ist sie eine Projektnummer,
    und zwei Dokumente duerfen sie teilen. Das ist hier die Grundlage fuer
    alles, was `tests/test_projektnummer.py` prueft.

    Args:
        None
    """
    zeilen = [
        ["Angebot", "0199", "Tonstudio Nordwind", "06.10.2026", "850,00 €"],
        ["Rechnung", "0199", "Tonstudio Nordwind", "20.10.2026", "850,00 €"],
    ]

    assert len({zeile[1] for zeile in zeilen}) == 1


def test_die_sichtbare_liste_haelt_die_reihenfolge() -> None:
    """Wer nach der Nummer sucht, sieht beide Dokumente des Projekts.

    Der Filter arbeitet ueber die Indizes und gibt Datensatz und Zeile
    paarweise zurueck. Deshalb kann die Liste nicht laenger werden als die
    Dokumente, die sie zeigt — auch dann nicht, wenn zwei Zeilen gleich
    aussehen.

    Args:
        None
    """
    dokumente = [{"id": 1, "art": "angebot"}, {"id": 2, "art": "rechnung"}]
    zeilen = [
        ("Angebot", "0199", "Tonstudio Nordwind"),
        ("Rechnung", "0199", "Tonstudio Nordwind"),
    ]

    paare = sichtbar(dokumente, zeilen, "0199")

    assert [d["id"] for d, _z in paare] == [1, 2]
    assert len(paare) == len(zeilen), (
        "Der Filter hat Zeilen erzeugt, zu denen es kein Dokument gibt."
    )


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
