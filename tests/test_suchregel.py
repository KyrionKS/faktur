"""Eine Regel für die Suche, und eine für den Schalter, der hineinführt.

Bis 0.8.2 gab es vier Bildschirme mit einem Suchfeld und **vier verschiedene
Wege**, damit die Liste zusammen mit ihrem Inhalt übereinstimmt. Zwei davon
bildeten über eine Spalte zurück — über die Kennung, über die Nummer — und
einer, die Kundenliste, vergaß den Rücksprung ganz. Wer dort *Zeta Tonwerk*
suchte, sah *Zeta Tonwerk*, öffnete *Alpha Klangstudio* und konnte mit
derselben Tastenfolge einen fremden Kunden samt Dokumenten löschen.

Der Absturz beim Logo und die Suche, die nur mit zweimal `tab` zu erreichen
war, kamen in dieselbe Klasse: Etwas war da, sah aus wie eine Bedienung und
war es nicht.

Diese Wächter halten beides fest. Sie lesen den Quelltext, weil man über
Text prüfen kann, was ein *Verhalten* nicht verrät: dass es nur noch eine
Stelle im ganzen Projekt gibt, an der diese Falle überhaupt entstehen kann.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from faktur import db
from faktur.suchen import sichtbar

#: Wurzels des Projekts.
WURZEL = Path(__file__).resolve().parents[1]
SCREENS = WURZEL / "faktur" / "screens"

#: Alle Bildschirmdateien, die ein Suchfeld benutzen.
MIT_SUCHE = sorted(
    p for p in SCREENS.glob("*.py") if "Suchfeld" in p.read_text(encoding="utf-8")
)


# --------------------------------------------------------------- die Regel


def test_sichtbar_haelt_die_reihenfolge() -> None:
    """Was man sieht, steht in derselben Reihenfolge wie der Datensatz.

    Args:
        None
    """
    datensaetze = ["Alpha", "Beta", "Gamma"]
    zeilen = [("Alpha Klang",), ("Beta Ton",), ("Gamma Bau",)]

    paare = sichtbar(datensaetze, zeilen, "a")

    # "a" steckt in allen dreien, trotzdem in dieser Reihenfolge.
    assert [d for d, _z in paare] == ["Alpha", "Beta", "Gamma"]
    assert [z for _d, z in paare] == [tuple(z) for z in zeilen]


def test_sichtbar_behaelt_gleiche_zeilen_beide() -> None:
    """Zwei gleiche Zeilen dürfen nicht zu einer verschmelzen.

    Genau daran ist 0.8 zerbrochen: Vergleicht man die Zeilen nach ihrem
    Text, fallen zwei Leistungen mit derselben Bezeichnung und demselben
    Preis zusammen — und wer die zweite anklickt, bekommt die dritte.

    Args:
        None
    """
    gleich = ("Mischung und Mastering", "Stunde", "950,00 €")
    datensaetze = [{"id": 1}, {"id": 2}, {"id": 3}]
    zeilen = [list(gleich), list(gleich), ["Aufnahme Ton", "Tag", "850,00 €"]]

    paare = sichtbar(datensaetze, zeilen, "Mischung")

    assert [d["id"] for d, _z in paare] == [1, 2], (
        "Beide gleichen Leistungen müssen durchkommen, jede mit ihrer Kennung."
    )


def test_sichtbar_ohne_begriff_lässt_alles_durch() -> None:
    """Ein leeres Feld darf nichts aussortieren.

    Args:
        None
    """
    zeilen = [("a",), ("b",)]

    assert len(sichtbar(["x", "y"], zeilen, "")) == 2
    assert len(sichtbar(["x", "y"], zeilen, "   ")) == 2


def test_sichtbar_bemerkt_verschieden_lange_listen() -> None:
    """Zwei Listen, die nicht zusammenpassen, sind ein Fehler.

    Sonst ginge beim Filtern ein Datensatz verloren und alle Aktionen, die
    über den Zeilenindex gehen, zeigten auf den falschen.

    Args:
        None
    """
    with pytest.raises(ValueError, match="passen nicht zusammen"):
        sichtbar(["a", "b"], [("x",)], "")


def test_sichtbar_ist_die_einzige_stelle() -> None:
    """Im ganzen Projekt wird nur hier gefiltert.

    Args:
        None
    """
    for datei in MIT_SUCHE:
        quelle = datei.read_text(encoding="utf-8")
        assert "filtern(" not in quelle, (
            f"{datei.name} benutzt noch filtern(). Damit laufen Zeilen und "
            "Datensätze auseinander — genau das war der Fehler auf der "
            "Kundenliste. Gewollt ist sichtbar()."
        )
        assert "passt(" not in quelle, (
            f"{datei.name} ruft passt() selbst. Das Filtern gehört in "
            "sichtbar(), sonst entstehen wieder eigene Wege."
        )


def test_kein_bildschirm_bildet_ueber_eine_spalte_zurueck() -> None:
    """Nach dem Filtern wird nicht über einen Spaltenwert zurückgebildet.

    So stand es in *Offene Forderungen* und in der Dokumentenliste: erst
    filtern, dann die passenden Zeilen anhand ihrer Kennung oder Nummer
    wieder einsammeln. Zwei Schritte, von denen einer vergessen werden konnte.

    Args:
        None
    """
    for datei in MIT_SUCHE:
        for nummer, zeile in enumerate(
            datei.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if "nummern = {" in zeile:
                pytest.fail(
                    f"{datei.name}:{nummer} bildet über eine Spalte zurück: "
                    f"{zeile.strip()}"
                )


# ---------------------------------------------- die Taste, die hineinfuehrt


def _hat_suchaktion(datei: Path) -> bool:
    """Sagt, ob der Bildschirm eine Aktion ``suchen`` hat.

    Args:
        datei: Die Bildschirmdatei.

    Returns:
        ``True``, wenn ``action_suchen`` definiert ist.
    """
    baum = ast.parse(datei.read_text(encoding="utf-8"))
    return any(
        isinstance(k, ast.FunctionDef) and k.name == "action_suchen"
        for k in ast.walk(baum)
    )


def test_jedes_suchfeld_ist_auch_erreichbar() -> None:
    """Wer ein Suchfeld zeigt, muss es auch bedienen können.

    Auf *Offene Forderungen* stand das Feld, und keine führte hinein. Die
    Suche war damit vorhanden und trotzdem tot.

    Args:
        None
    """
    tot = [d.name for d in MIT_SUCHE if not _hat_suchaktion(d)]

    assert tot == [], (
        f"Diese Bildschirme zeigen ein Suchfeld, haben aber keine Taste, "
        f"die hineinführt: {tot}"
    )


def test_und_die_taste_ist_auch_gebunden() -> None:
    """Eine Aktion ohne Taste hilft niemandem.

    Args:
        None
    """
    ohne: list[str] = []

    for datei in MIT_SUCHE:
        quelle = datei.read_text(encoding="utf-8")
        if not _hat_suchaktion(datei):
            continue
        if '"suche", "suchen"' not in quelle:
            ohne.append(datei.name)

    assert ohne == [], f"Ohne Bindung auf ``suche``: {ohne}"


# ------------------------------------------------------ das gestrichene Logo


def test_es_gibt_keinen_absturz_beim_logo_mehr() -> None:
    """Der Menüpunkt *Logo* ist weg, weil er das Programm abstürzen ließ.

    Er suchte die Quelldatei an ``daten/logo.png`` und kopierte sie dann nach
    ``daten/logo.png``. Quelle und Ziel waren dieselbe Datei, und
    ``shutil.copyfile`` bricht das ab. Bei jedem Benutzer mit einem Logo,
    bei jedem Klick.

    Args:
        None
    """
    quelle = (SCREENS / "stammdaten.py").read_text(encoding="utf-8")

    assert "logo_waehlen" not in quelle, "Die abstürzende Methode ist noch da."
    assert '"logo"' not in quelle, "Der Menüpunkt ist noch da."
    assert "logo_uebernehmen" not in quelle, (
        "Es wird noch eine Logodatei kopiert — ohne Zielordner ist das der "
        "Weg, auf dem die Nutzerdaten kapttgehen."
    )


def test_und_die_logo_datei_wird_gar_nicht_mehr_kopiert() -> None:
    """Außer den Tests kopiert niemand eine Logodatei.

    Args:
        None
    """
    aufrufer = []
    for datei in sorted((WURZEL / "faktur").rglob("*.py")):
        quelle = datei.read_text(encoding="utf-8")
        if "logo_uebernehmen(" not in quelle:
            continue
        if datei.name == "einstellungen.py":
            continue
        aufrufer.append(datei.name)

    assert aufrufer == [], (
        f"Diese Dateien rufen logo_uebernehmen() ohne Zielordner auf: {aufrufer}. "
        "Das hat zweimal die echten Daten des Benutzers ueberschrieben."
    )


def test_das_standardlogo_liegt_wo_die_anleitung_sagt() -> None:
    """Der Ort, an dem die Anleitung das Logo nennt, stimmt noch.

    Args:
        None
    """
    assert db.STANDARD_LOGO == db.DATENORDNER / "logo.png", (
        "Die Anleitung sagt daten/logo.png. Weicht der Ort ab, sucht das "
        "Programm ins Leere."
    )
