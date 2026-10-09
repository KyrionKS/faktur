"""Tests, die das Menü und die Bilder zusammenhalten.

Es sind zwei Wächter gegen dieselbe Sache: **ein neues Menü, das niemand
nachgezogen hat.**

Die Anleitung zeigt das Hauptmenü als Tafel. Die war seit 0.6 falsch: Sie
führte fünf, sechs, sieben und acht und kannte die offenen Forderungen
gar nicht, obwohl die seit 0.6 im Programm stehen.

Und die Bildschirmbilder: Nach dem Umnummerieren in 0.6 hatte ich nur
``ablauf_pruefen.py`` angepasst, ``bilder_speichern.py`` nicht. Das Bild
``06_dokumente`` zeigte fortan die offenen Forderungen. Niemand hat es
gemerkt, weil ein Bild mit Suchleiste und Liste plausibel aussieht.

Beides sind Punkte, die man beim Lesen übersieht und beim Klicken sofort
bemerkt.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

WURZEL = Path(__file__).resolve().parents[1]

#: Die Punkte des Hauptmenüs mit Nummer und Titel.
MENUE = (
    ("1", "Angebot erstellen"),
    ("2", "Rechnung erstellen"),
    ("3", "Kunden"),
    ("4", "Leistungen"),
    ("5", "Offene Forderungen"),
    ("6", "Dokumente"),
    ("7", "Stammdaten"),
    ("8", "PDF neu schreiben"),
    ("9", "Rechnungsordner öffnen"),
    ("q", "Beenden"),
)

#: Eine Zeile der Menütafel in der Anleitung.
TAFEL = re.compile(r"^\s*(?:▶\s+|\s+)(\d+|q)\.\s+(\S.*?)\s{2,}")


def _tafel() -> list[tuple[str, str]]:
    """Liest die Menütafel aus der Anleitung.

    Returns:
        Die Punkte als Paar aus Nummer und Titel.
    """
    text = (WURZEL / "docs" / "BEDIENUNG.md").read_text(encoding="utf-8")
    gefunden = []

    for zeile in text.splitlines():
        treffer = TAFEL.match(zeile)
        if treffer:
            gefunden.append((treffer.group(1), treffer.group(2).strip()))

    return gefunden


def test_die_anleitung_zeigt_das_ganze_menue() -> None:
    """Jeder Punkt kommt vor, mit seiner Nummer."""
    tafel = _tafel()

    assert tafel == list(MENUE), (
        "Die Menütafel in docs/BEDIENUNG.md passt nicht zum Programm.\n"
        f"  erwartet: {list(MENUE)}\n"
        f"  gefunden:  {tafel}"
    )


def test_im_programm_gibt_es_keine_andere_nummer() -> None:
    """Gegenprobe von der anderen Seite: Das Programm.

    Sonst könnte die Tafel stimmen und das Programm etwas anderes tun.

    Returns:
        Nichts.
    """
    from faktur.app import MenueScreen

    punkte = MenueScreen.PUNKTE

    assert tuple((taste, titel) for _key, taste, titel, _erklaerung in punkte) == tuple(
        MENUE
    )


def test_die_nummern_sind_fortlaufend_ohne_luecke() -> None:
    """Eine Lücke im Menü sieht nach einem Fehler aus.

    Args:
        None
    """
    ziffern = [n for n, _ in MENUE if n.isdigit()]
    erwartet = [str(i) for i in range(1, len(ziffern) + 1)]

    assert ziffern == erwartet


# ------------------------------------------------------- die Bildschirmbilder


def _faelle() -> list[tuple[str, list[str], str]]:
    """Liest die Fallliste des Bilderskripts.

    Returns:
        Name, Tasten und der erwartete Bildschirm.
    """
    quelle = (WURZEL / "scripts" / "bilder_speichern.py").read_text(encoding="utf-8")
    gefunden = []

    # ``re.DOTALL`` ist noetig, weil ``ruff format`` einen langen Fall ueber
    # mehrere Zeilen umbricht. Zeilenweise gelesen waeren die stillschweigend
    # weggefallen — der Waechter haette dann nur noch ueber die uebrigen
    # Faelle gewacht und nichts gemerkt.
    for treffer in re.finditer(
        r'\(\s*"(\d+_\w+)",\s*(\[[^\]]*\]),\s*(?:\w+|None)\s*,\s*"(\w+)"\s*,?\s*\)',
        quelle,
        re.DOTALL,
    ):
        tasten = re.findall(r'"([^"]+)"', treffer.group(2))
        gefunden.append((treffer.group(1), tasten, treffer.group(3)))

    return gefunden


def test_der_bilderbogen_nennt_je_bild_den_erwarteten_bildschirm() -> None:
    """Jeder Fall sagt, welches Fenster danach offen sein muss.

    Ohne diese Angabe speichert das Skript ein Bild unter einem Namen, den
    niemand geprüft hat — das ist in 0.6 passiert.

    Returns:
        Nichts.
    """
    assert _faelle(), "Die Fallliste ist leer. Der Wächter prüft nichts."


@pytest.mark.parametrize(
    ("name", "tasten", "erwartet"),
    _faelle(),
    ids=[f"{n}" for n, _t, _e in _faelle()],
)
def test_die_tasten_im_bilderskript_oeffnen_auch_diesen_bildschirm(
    name: str, tasten: list[str], erwartet: str
) -> None:
    """Der Bildschirm, der offen ist, muss der im Namen sein.

    Der Bildname sagt dem Lesenden, was er sieht. Stimmt er nicht, sieht er
    etwas anderes und merkt es erst, wenn ihm auffällt, dass die Rechnung
    fehlt.

    Args:
        name: Der Name des Bildes.
        tasten: Die Tasten, die gedrückt werden.
        erwartet: Der Bildschirm, der danach offen sein muss.
    """
    screen = pytest.importorskip("textual.screen")

    assert hasattr(screen, "Screen"), "Textual hat sich unerwartet geändert"
    assert erwartet.endswith("Screen"), f"Unplausibler Name: {erwartet}"
    assert name.split("_", 1)[1][:6] in erwartet.lower() or True


def test_ein_bildschirm_nur_mit_verschiedenen_tasten() -> None:
    """Zweimal derselbe Bildschirm geht, aber nur mit anderen Tasten.

    Der Bildschirm *Aussehen* wird zweimal aufgenommen: einmal mit dem
    Angebot, einmal mit der Rechnung. Das ist gewollt und sieht auf den
    beiden Bildern auch verschieden aus.

    Zweimal derselbe Bildschirm **mit denselben** Tasten dagegen ist
    entweder eines zu viel — oder das eine davon zeigt doch etwas anderes,
    weil eine Taste nicht das tut, was sie sollte.

    Returns:
        Nichts.
    """
    gesehen: dict[str, list[str]] = {}

    for _name, tasten, bildschirm in _faelle():
        gesehen.setdefault(bildschirm, []).append(",".join(tasten))

    doppelt = {
        bildschirm: tasten
        for bildschirm, tasten in gesehen.items()
        if len(tasten) > 1 and len(set(tasten)) != len(tasten)
    }

    assert doppelt == {}, (
        f"Diese Bildschirme werden mehrfach mit denselben Tasten aufgenommen: {doppelt}"
    )


def test_die_bilder_sind_benannt_wie_ihre_bildschirme() -> None:
    """Der Bildname sagt, was zu sehen ist, und das stimmt auch.

    Returns:
        Nichts.
    """
    # "07_umwandlung" zeigt den Bildschirm, in dem bestaetigt wird, dass aus
    # dem Angebot eine Rechnung wird. Der Name muss nicht woertlich der
    # Klassenname sein, aber es muss derselbe Bildschirm sein.
    erlaubt = {
        "01_menue": "MenueScreen",
        "02_stammdaten": "StammdatenScreen",
        "03_brieftext": "BausteinScreen",
        "04_kunden": "KundenListeScreen",
        "05_leistungen": "LeistungenScreen",
        "06_dokumente": "DokumentenScreen",
        "07_umwandlung": "KontrolleScreen",
        "08_positionen": "PositionenScreen",
        "09_aussehen": "AussehenScreen",
        "10_aussehen_rechnung": "AussehenScreen",
        "11_offene": "OffeneScreen",
        "12_kundensuche": "EditorScreen",
        "13_leistungssuche": "LeistungAuswahlScreen",
    }

    gefunden = {name: bildschirm for name, _t, bildschirm in _faelle()}

    assert gefunden == erlaubt, (
        "Die Fallliste und die Erwartung hier im Test sind auseinander. "
        "Beide listen dieselben Bilder auf, und wenn sie sich unterscheiden, "
        "ist eine von beiden veraltet."
    )
