"""Tests für das Sichern.

Der wichtigste Test ist der erste: **Eine Sicherung ist eine Kopie, kein
Umzug.** Der Ordner bleibt, wo er ist. Wer die Daten beim Sichern wegzieht,
verliert sie beim ersten Fehlgriff.

Und der letzte: Das Alter wird an der Backup-Kapazität gemessen, nicht an
irgendeiner Heuristik. Der Ordner heisst so, weil er unabhaengig davon, was
das Programm sonst fuer richtig haelt.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest
from faktur import sichern


def test_der_stempel_hat_datum_und_uhrzeit() -> None:
    """Sonst ist nicht zu erkennen, welche Sicherung welche ist.

    Args:
        None
    """
    wann = datetime(2026, 10, 8, 14, 32)

    assert sichern.stempel(wann) == "2026-10-08_1432"


def test_zwei_sicherungen_an_einem_tag_ueberschreiben_nicht_einander(
    tmp_path: Path,
) -> None:
    """Mit Sekunden im Namen. Ohne sie waere die zweite weg.

    Args:
        tmp_path: Das temporäre Verzeichnis.
    """
    ziel = tmp_path / "kopie"

    sichern.sichere(ziel)
    (ziel / "spaeter.txt").write_text("später", encoding="utf-8")

    assert (ziel / "spaeter.txt").is_file()


def test_gesichert_wird_eine_kopie_und_kein_umzug(tmp_path: Path, monkeypatch) -> None:
    """Das Wichtigste an der ganzen Funktion.

    Args:
        tmp_path: Das temporäre Verzeichnis.
        monkeypatch: Zum Umbiegen des Datenordners.
    """
    daten = tmp_path / "daten"
    daten.mkdir()
    (daten / "faktur.db").write_text("die datenbank", encoding="utf-8")

    monkeypatch.setattr(sichern.orte, "datenordner", lambda: daten)

    ordner = sichern.sichere(tmp_path / "kopie")

    assert (daten / "faktur.db").is_file(), "Der Ordner muss noch da sein"
    assert (ordner / "faktur.db").is_file(), "Und die Kopie auch"
    assert ordner != daten


def test_ohne_datenordner_gibt_es_eine_erklaerung(tmp_path: Path, monkeypatch) -> None:
    """Statt eines Absturzes ein Satz, der sagt, was fehlt.

    Args:
        tmp_path: Das temporäre Verzeichnis.
        monkeypatch: Zum Umbiegen des Datenordners.
    """
    monkeypatch.setattr(sichern.orte, "datenordner", lambda: tmp_path / "gibtsnicht")

    with pytest.raises(sichern.Fehler) as fehler:
        sichern.sichere(tmp_path / "kopie")

    assert "Datenordner" in str(fehler.value)


def test_die_groesse_wird_in_megabyte_angegeben(tmp_path: Path) -> None:
    """Und nicht in Bytes, denn_bytes sind nicht lesbar.

    Args:
        tmp_path: Das temporäre Verzeichnis.
    """
    ordner = tmp_path / "kopie"
    ordner.mkdir()
    (ordner / "gross.pdf").write_bytes(b"0" * 1048576)

    assert sichern.groesse(ordner) == "1,0 MB"


def test_ohne_ablage_ist_die_liste_leer_aber_sagts(tmp_path: Path, monkeypatch) -> None:
    """„Noch keine Sicherung." ist eine Antwort. Eine leere Zeile nicht.

    Args:
        tmp_path: Das temporäre Verzeichnis.
        monkeypatch: Zum Umbiegen der Ablage.
    """
    monkeypatch.setattr(sichern, "ablage", lambda: tmp_path / "gibtsnicht")

    assert sichern.texte() == ["Noch keine Sicherung."]
    assert sichern.alte() == []


def test_die_aeltesten_kommen_zuerst_als_loeschkandidaten(
    tmp_path: Path, monkeypatch
) -> None:
    """Nur die neuesten bleiben, sonst frisst die Ablage die Platte.

    Args:
        tmp_path: Das temporäre Verzeichnis.
        monkeypatch: Zum Umbiegen der Ablage.
    """
    ablage = tmp_path / "Sicherung"
    ablage.mkdir()

    nummern = [f"2026-10-0{tag}_1200" for tag in range(1, 6)]
    for name in nummern:
        (ablage / name).mkdir()

    monkeypatch.setattr(sichern, "ablage", lambda: ablage)

    alt = sichern.alte(grenze=2)

    assert [p.name for p in alt] == [
        "2026-10-01_1200",
        "2026-10-02_1200",
        "2026-10-03_1200",
    ]


def test_die_liste_zeigt_die_neueste_zuerst(tmp_path: Path, monkeypatch) -> None:
    """Args:
    tmp_path: Das temporäre Verzeichnis.
    monkeypatch: Zum Umbiegen der Ablage.
    """
    ablage = tmp_path / "Sicherung"
    ablage.mkdir()

    for name in ("2026-10-01_1200", "2026-10-03_1200", "2026-10-02_1200"):
        (ablage / name).mkdir()

    monkeypatch.setattr(sichern, "ablage", lambda: ablage)

    zeilen = sichern.texte()

    assert zeilen[0].startswith("2026-10-03_1200")
    assert zeilen[-1].startswith("2026-10-01_1200")


def test_die_liste_sagt_welche_zum_wegwerfen_anstehen(
    tmp_path: Path, monkeypatch
) -> None:
    """Damit man weiss, was man loeschen kann, ohne alle zu loeschen.

    Es braucht mehr als die zehn Sicherungen, die das Programm von selbst
    behält — sonst steht da nichts zum Wegwerfen.

    Args:
        tmp_path: Das temporäre Verzeichnis.
        monkeypatch: Zum Umbiegen der Ablage.
    """
    ablage = tmp_path / "Sicherung"
    ablage.mkdir()

    # Zwoelf Sicherungen an zwölf Tagen, damit zwei anstehen.
    for tag in range(1, 13):
        (ablage / f"2026-10-{tag:02}_1200").mkdir()

    monkeypatch.setattr(sichern, "ablage", lambda: ablage)

    zeilen = sichern.texte()
    alt = [z for z in zeilen if "Wegwerfen" in z]

    assert len(alt) == 2
    assert "2026-10-12_1200" not in alt[0], "Die neueste bleibt immer"
    assert "2026-10-12_1200" in zeilen[0]


def test_geloescht_wird_nichts_ohne_ausdruecklichen_wunsch(
    tmp_path: Path, monkeypatch
) -> None:
    """``alte()`` sagt nur, was ansteht. Es loescht nichts.

    Wer die Sicherungen loescht, entscheidet das mit Absicht und nicht
    nebenbei beim Programmstart.

    Args:
        tmp_path: Das temporäre Verzeichnis.
        monkeypatch: Zum Umbiegen der Ablage.
    """
    ablage = tmp_path / "Sicherung"
    ablage.mkdir()

    for nummer in range(1, 6):
        (ablage / f"2026-10-0{nummer}_1200").mkdir()

    monkeypatch.setattr(sichern, "ablage", lambda: ablage)

    sichern.alte(grenze=1)

    assert len(list(ablage.iterdir())) == 5
