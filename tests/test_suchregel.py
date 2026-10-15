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

import os
import tempfile
from pathlib import Path

import pytest
from faktur import db
from faktur.suchen import sichtbar

#: Wurzels des Projekts.
WURZEL = Path(__file__).resolve().parents[1]

#: Die Listen im Fenster. Dort gibt es das Suchfeld, seit es Qt gibt.
LISTEN = sorted((WURZEL / "faktur" / "gui").glob("*.py"))


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
    """Im ganzen Projekt wird nur ueber ``sichtbar`` gefiltert.

    **Kommentare zaehlen nicht.** Wer in einem Kommentar ``passt()`` erwaehnt,
    um zu erklaeren, warum er es nicht benutzt, hat es nicht benutzt. Sonst
    schlaegt der Waechter an der Erklaerung an statt am Aufruf.

    Args:
        None
    """
    for datei in LISTEN:
        for nummer, zeile in enumerate(_code(datei), start=1):
            assert "filtern(" not in zeile, (
                f"{datei.name}:{nummer} benutzt noch filtern(). Damit laufen "
                "Zeilen und Datensaetze auseinander — genau das war der "
                "Fehler auf der Kundenliste. Gewollt ist sichtbar()."
            )
            assert "passt(" not in zeile, (
                f"{datei.name}:{nummer} ruft passt() selbst. Das Filtern "
                "gehoert nach sichtbar(), sonst entstehen wieder eigene Wege."
            )


def _code(datei: Path) -> list[str]:
    """Gibt die Zeilen einer Datei ohne Kommentare zurück.

    Args:
        datei: Die Python-Datei.

    Returns:
        Die Zeilen, von denen keine ein Kommentar ist.
    """
    return [
        zeile
        for zeile in datei.read_text(encoding="utf-8").splitlines()
        if not zeile.lstrip().startswith("#")
    ]


def test_keine_seite_bildet_ueber_eine_spalte_zurueck() -> None:
    """Nach dem Filtern wird nicht ueber einen Spaltenwert zurueckgebildet.

    So stand es in *Offene Forderungen* und in der Dokumentenliste: erst
    filtern, dann die passenden Zeilen anhand ihrer Kennung oder Nummer
    wieder einsammeln. Zwei Schritte, von denen einer vergessen werden
    konnte.

    Im Fenster ist der Weg kuerzer: Das Modell haelt Datensatz und Zeile
    zusammen, also gibt es gar keinen Ruecksprung. Wer hier doch einen baut,
    hat den Fehler wieder eingebaut.

    Args:
        None
    """
    for datei in LISTEN:
        for nummer, zeile in enumerate(
            datei.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if "nummern = {" in zeile:
                pytest.fail(
                    f"{datei.name}:{nummer} bildet ueber eine Spalte zurueck: "
                    f"{zeile.strip()}"
                )


# ---------------------------------------------- die Taste, die hineinfuehrt


def test_jede_liste_hat_ein_erreichbares_suchfeld() -> None:
    """Wer eine Liste zeigt, muss sie auch durchsuchen können.

    Auf *Offene Forderungen* stand das Feld, und keine führte hinein. Die
    Suche war damit vorhanden und trotzdem tot — im Fenster darf sich das
    nicht wiederholen.

    Args:
        None
    """
    pytest.importorskip("PySide6")
    os.environ.setdefault("QT_QPA_PLATFORM", "minimal")

    from faktur import db
    from faktur.gui.fenster import Fenster
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    fenster = Fenster(db.verbinden(Path(tempfile.mkdtemp()) / "suche.db"))
    fenster.zeige()
    app.processEvents()

    tot = []
    for schluessel in fenster.reihenfolge:
        seite = fenster.seiten[schluessel]
        feld = getattr(seite, "suchfeld", None)
        if feld is None or not feld.isVisible():
            continue
        fenster.gehe(schluessel)
        app.processEvents()
        fenster._suchen()
        app.processEvents()
        if not feld.hasFocus():
            tot.append(schluessel)

    fenster.fenster.close()

    assert tot == [], (
        f"Diese Bereiche zeigen ein Suchfeld, aber Cmd+F führt nicht hinein: {tot}"
    )


def test_und_die_taste_ist_auch_gebunden() -> None:
    """Eine Aktion ohne Taste hilft niemandem.

    Args:
        None
    """
    app_quelle = (WURZEL / "faktur" / "gui" / "fenster.py").read_text(encoding="utf-8")

    assert 'suche.setShortcut("Ctrl+F")' in app_quelle, (
        "Die Aktion *Suchen* hat kein Kuerzel mehr."
    )
    assert "suche.triggered.connect(self._suchen)" in app_quelle, (
        "Die Aktion *Suchen* ist nicht mehr verdrahtet."
    )


# ------------------------------------------------------ das gestrichene Logo


def test_es_gibt_keinen_absturz_beim_logo_mehr() -> None:
    """In der Oberflaeche wird nie selbst kopiert.

    Der alte Menüpunkt suchte die Quelldatei an ``daten/logo.png`` und
    kopierte sie dann nach ``daten/logo.png``. Quelle und Ziel waren
    dieselbe Datei, und ``shutil.copyfile`` bricht das ab. Bei jedem
    Benutzer mit einem Logo, bei jedem Klick.

    Kopieren darf nur :mod:`faktur.einstellungen`, und das nennt sein Ziel
    ausdruecklich — siehe den naechsten Test.

    Args:
        None
    """
    quelle = (WURZEL / "faktur" / "gui" / "stammdaten.py").read_text(encoding="utf-8")

    assert "shutil" not in quelle, (
        "In der Oberflaeche wird nicht kopiert. Das macht "
        "faktur.einstellungen, und das nennt sein Ziel ausdruecklich."
    )
    assert "logo_waehlen" not in quelle, "Die abstürzende Methode ist noch da."


def test_und_die_logo_datei_wird_gar_nicht_mehr_kopiert() -> None:
    """Außer den Tests kopiert niemand eine Logodatei ohne Ziel.

    ``logo_uebernehmen`` nimmt ohne Angabe den echten Datenordner des
    Benutzers. Das hat zweimal die echten Daten überschrieben, weil ein
    Test genau das aufrief. Deshalb muss jeder Aufrufer das Ziel
    ausdrücklich nennen — auch das Programm selbst.

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
        if "ziel_ordner=" not in quelle:
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
