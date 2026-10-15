"""Die Positionen eines Dokuments.

**Der Fehler aus 0.8.1, in anderer Gestalt.** Dort passte die Anzeige
nicht mehr zu den Daten. Hier ist es die Summe: Sie ändert sich bei jedem
Tastendruck, und eine Zahl, die nicht mitrechnet, ist schlimmer als gar
keine.

Der grösste Teil dieser Datei braucht **kein Fenster**. Das Modell rechnet,
verschiebt und liefert die Liste, die :func:`faktur.dateien.dokument_speichern`
nimmt — alles ohne, dass etwas gezeichnet würde.
"""

from __future__ import annotations

import os
import sqlite3

import pytest

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "minimal")

from faktur import betraege, dateien  # noqa: E402
from faktur.gui.positionen import SUMSPALTE, PositionenModell  # noqa: E402


def _posten(*paare: tuple[str, float, str, float]) -> list[dict[str, object]]:
    """Baut eine Liste von Positionen.

    Args:
        paare: Je Position Bezeichnung, Menge, Einheit und Einzelpreis.

    Returns:
        Die Positionen für :meth:`PositionenModell.setze`.
    """
    return [
        {"bezeichnung": name, "menge": menge, "einheit": einheit, "preis": preis}
        for name, menge, einheit, preis in paare
    ]


# --------------------------------------------------------------- Die Summe


def test_die_summe_steht_unten_und_rechnet_mit() -> None:
    """Sie steht in der rechten Spalte **und** rechnet sich mit.

    Args:
        None
    """
    modell = PositionenModell()
    modell.setze(_posten(("Aufnahme Ton", 2, "Tag", 850.0)))
    assert modell.summe() == 1700.0

    modell.setze(
        _posten(
            ("Aufnahme Ton", 2, "Tag", 850.0),
            ("Sprecherstimme", 1.5, "Stunde", 120.0),
        )
    )
    assert modell.summe() == 1700.0 + 180.0


def test_und_sie_aendert_sich_beim_tippen() -> None:
    """Getippt wird über das Modell, und die Summe folgt.

    Args:
        None
    """
    from faktur.gui.qt import QModelIndex  # noqa: F401
    from PySide6.QtCore import Qt

    modell = PositionenModell()
    modell.setze(_posten(("Aufnahme Ton", 2, "Tag", 850.0)))

    geaendert: list[float] = []
    modell.summen_geaendert.connect(lambda: geaendert.append(modell.summe()))

    vorher = modell.summe()
    modell.setData(modell.index(0, 1), "3", Qt.ItemDataRole.EditRole.value)

    assert modell.summe() > vorher, "Die Menge wurde nicht uebernommen"
    assert modell.summe() == 2550.0
    assert geaendert, "Es wurde niemanden davon verstaendigt"


def test_und_die_summe_der_zeile_stimmt_mit_der_gesamtsumme() -> None:
    """Die rechte Spalte zeigt je Zeile dasselbe wie unten.

    Args:
        None
    """
    from PySide6.QtCore import Qt

    modell = PositionenModell()
    modell.setze(
        _posten(
            ("Aufnahme Ton", 2, "Tag", 850.0),
            ("Mischung", 8, "Stunde", 95.0),
        )
    )

    zeilen = [
        modell.data(modell.index(zeile, SUMSPALTE), Qt.ItemDataRole.DisplayRole.value)
        for zeile in range(modell.rowCount())
    ]

    assert zeilen == ["1.700,00 €", "760,00 €"]
    assert modell.summe() == 2460.0


def test_und_getippt_wird_eine_zahl_und_nicht_ein_wort() -> None:
    """„1.700,50“ kommt als Zahl an, nicht als Text.

    Args:
        None
    """
    from PySide6.QtCore import Qt

    modell = PositionenModell()
    modell.setze(_posten(("Aufnahme Ton", 1, "Tag", 0.0)))

    modell.setData(modell.index(0, 3), "1.700,50", Qt.ItemDataRole.EditRole.value)

    assert modell.positionen[0]["preis"] == 1700.5
    assert modell.summe() == 1700.5


def test_und_unsinn_wird_nicht_zur_summe_gezählt() -> None:
    """Ein leeres Preisfeld ergibt null, nicht einen Absturz.

    Args:
        None
    """
    from PySide6.QtCore import Qt

    modell = PositionenModell()
    modell.setze(_posten(("Aufnahme Ton", 1, "Tag", 850.0)))

    modell.setData(modell.index(0, 3), "", Qt.ItemDataRole.EditRole.value)
    modell.setData(modell.index(0, 1), "", Qt.ItemDataRole.EditRole.value)

    assert modell.summe() == 0.0


def test_und_die_summe_ist_kein_text() -> None:
    """Die Methode gibt eine Zahl zurück, damit man damit rechnen kann.

    Args:
        None
    """
    modell = PositionenModell()
    modell.setze(_posten(("Aufnahme Ton", 3, "Tag", 850.0)))

    assert isinstance(modell.summe(), float)
    assert betraege.euro(modell.summe()) == "2.550,00 €"


# ----------------------------------------------------------- Das Umstellen


def test_verschieben_bringt_eine_zeile_nach_oben() -> None:
    """Die Reihenfolge ist die, die man sieht.

    Args:
        None
    """
    modell = PositionenModell()
    modell.setze(
        _posten(
            ("erste", 1, "", 10.0),
            ("zweite", 1, "", 20.0),
            ("dritte", 1, "", 30.0),
        )
    )

    assert modell.verschiebe(2, -1) is True
    assert [p["bezeichnung"] for p in modell.positionen] == [
        "erste",
        "dritte",
        "zweite",
    ]


def test_und_an_den_raendern_passiert_nichts() -> None:
    """Ganz oben nach oben und ganz unten nach unten geht nicht.

    Args:
        None
    """
    modell = PositionenModell()
    modell.setze(_posten(("erste", 1, "", 10.0), ("zweite", 1, "", 20.0)))

    assert modell.verschiebe(0, -1) is False
    assert modell.verschiebe(1, 1) is False
    assert [p["bezeichnung"] for p in modell.positionen] == ["erste", "zweite"]


def test_und_die_summe_aendert_sich_nicht_durch_das_umstellen() -> None:
    """Reihenfolge ist keine Rechnung.

    Args:
        None
    """
    modell = PositionenModell()
    modell.setze(
        _posten(
            ("Aufnahme Ton", 2, "Tag", 850.0),
            ("Mischung", 8, "Stunde", 95.0),
        )
    )

    vorher = modell.summe()
    modell.verschiebe(1, -1)

    assert modell.summe() == vorher


# ------------------------------------------------- Hinzufuegen und entfernen


def test_aus_einer_leistung_wird_eine_position(verbindung: sqlite3.Connection) -> None:
    """Der Preis wandert mit, und die Verknüpfung bleibt.

    Args:
        verbindung: Die Datenbankverbindung.
    """
    leistung = dateien.leistungen(verbindung)[0]
    modell = PositionenModell()
    modell.aus_leistung(leistung)

    assert modell.rowCount() == 1
    position = modell.positionen[0]
    assert position["bezeichnung"] == leistung["bezeichnung"]
    assert position["preis"] == leistung["preis"]
    assert position["leistung_id"] == leistung["id"]


def test_und_das_geht_so_in_die_datenbank(verbindung: sqlite3.Connection) -> None:
    """Die Liste, die das Modell zurückgibt, nimmt ``dokument_speichern``.

    Das ist der ganze Sinn von :meth:`PositionenModell.liste`: Es gibt
    keine Übersetzung dazwischen, die etwas verlieren könnte.

    Args:
        verbindung: Die Datenbankverbindung.
    """
    kunde = dateien.kunde_speichern(verbindung, {"firma": "Tonstudio Nordwind"})
    leistung = dateien.leistungen(verbindung)[0]

    modell = PositionenModell()
    modell.aus_leistung(leistung)
    modell.aus_leistung(leistung)
    modell.setData(modell.index(1, 1), "3", 2)

    kennung = dateien.dokument_speichern(
        verbindung,
        {
            "art": "rechnung",
            "nummer": dateien.naechste_nummer(verbindung),
            "kunde_id": kunde,
            "datum": "2026-10-12",
            "faellig": "2026-10-26",
        },
        modell.liste(),
    )

    gespeichert = dateien.positionen(verbindung, kennung)
    assert [str(p["bezeichnung"]) for p in gespeichert] == [
        str(leistung["bezeichnung"]),
        str(leistung["bezeichnung"]),
    ]
    assert [p["menge"] for p in gespeichert] == [1.0, 3.0]
    assert dateien.summe_von(verbindung, kennung) == pytest.approx(
        leistung["preis"] * 4
    )


def test_entfernen_nimmt_nur_die_markierte_zeile() -> None:
    """Zwei Zeilen mit gleichem Namen bleiben zwei.

    Args:
        None
    """
    modell = PositionenModell()
    modell.setze(
        _posten(
            ("Mischung", 1, "Stunde", 95.0),
            ("Mischung", 2, "Stunde", 95.0),
        )
    )

    assert modell.entferne(0) is True
    assert modell.rowCount() == 1
    assert modell.positionen[0]["menge"] == 2.0
    assert modell.entferne(9) is False


def test_und_eine_leere_position_ist_sofort_tippbar() -> None:
    """Die leere Zeile kommt ans Ende und ist markiert.

    Args:
        None
    """
    modell = PositionenModell()
    modell.setze(_posten(("erste", 1, "", 10.0)))

    zeile = modell.leere_zeile()

    assert zeile == 1
    assert modell.positionen[1]["bezeichnung"] == ""
    assert modell.positionen[1]["menge"] == 1.0


# ------------------------------------------------------- Angebote vs Rechnung


def test_bei_einem_angebot_stehen_keine_cent(verbindung: sqlite3.Connection) -> None:
    """Ein Angebotspreis ist eine Schätzung.

    Args:
        verbindung: Die Datenbankverbindung.
    """
    kunde = dateien.kunde_speichern(verbindung, {"firma": "Tonstudio Nordwind"})
    leistung = dateien.leistungen(verbindung)[0]

    von_angebot = PositionenModell(preise_genau=False)
    von_angebot.aus_leistung(leistung)

    nummer = dateien.naechste_nummer(verbindung)
    angebot = dateien.dokument_speichern(
        verbindung,
        {"art": "angebot", "nummer": nummer, "kunde_id": kunde, "datum": "2026-10-12"},
        von_angebot.liste(),
    )
    kopf, positionen = dateien.als_angebot_uebernehmen(verbindung, angebot)

    von_rechnung = PositionenModell()
    von_rechnung.setze(list(positionen))

    assert kopf["nummer"] == nummer, "Die Projektnummer muss mitwandern"
    assert von_rechnung.rowCount() == 1
    assert von_rechnung.summe() == pytest.approx(float(leistung["preis"]))


def test_und_ohne_positionen_ist_die_summe_null() -> None:
    """Ein leeres Dokument ist kein Fehler.

    Args:
        None
    """
    modell = PositionenModell()
    assert modell.summe() == 0.0
    assert modell.entferne(0) is False, "Ein leeres Dokument hat keine Zeile"

    assert modell.leere_zeile() == 0
    assert modell.entferne(0) is True


def test_und_die_liste_ist_eine_kopie(verbindung: sqlite3.Connection) -> None:
    """Wer an der Liste dreht, dreht nicht am Dokument.

    Args:
        verbindung: Die Datenbankverbindung.
    """
    leistung = dateien.leistungen(verbindung)[0]
    modell = PositionenModell()
    modell.aus_leistung(leistung)

    kopie = modell.liste()
    kopie[0]["bezeichnung"] = "kaputt"

    assert modell.positionen[0]["bezeichnung"] == leistung["bezeichnung"]
