"""Sichern.

``daten/`` ist der ganze Bestand: Kunden, Leistungen, jedes Angebot, jede
Rechnung und die PDF dazu. Auf einer Platte, ohne Kopie. Fällt die Platte
aus, ist alles weg — und bei einem Angebot, das schon beim Kunden liegt,
gibt es kein Zurück: Die Nummer steht gedruckt auf einem Dokument, das
niemandem mehr gehört.

Eine Sicherung ist hier deshalb billig und trotzdem die billigste Versicherung
im ganzen Programm. Sie kopiert den Ordner mit dem Datum in die Ablage.

Bewusst kopiert und nicht verschoben: Der Ordner bleibt, wo er ist, und die
Kopie ist etwas, das man jederzeit wegwerfen kann.
"""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

from faktur import orte


class Fehler(Exception):  # noqa: N818 - deutscher Name, wie alles andere hier
    """Die Sicherung hat nicht geklappt.

    Steht als eigener Fehler, damit die Meldung oben im Klartext
    erscheint und nicht als Spur von einem Absturz.
    """


def ablage() -> Path:
    """Nennt den Ordner, in den die Sicherungen kommen.

    Returns:
        Der Ablageordner neben dem Programm.
    """
    return orte.datenordner().parent / "Sicherung"


def stempel(wann: datetime | None = None) -> str:
    """Baut den Namensbestandteil einer Sicherung.

    Sekunden, weil man an einem Tag zweimal sichern können muss, ohne
    dass die erste überschrieben wird.

    Args:
        wann: Der Zeitpunkt. Ohne Angabe jetzt.

    Returns:
        Der Stempel, etwa ``2026-10-08_1432``.
    """
    return (wann or datetime.now()).strftime("%Y-%m-%d_%H%M")


def sichere(ziel: Path | None = None) -> Path:
    """Kopiert den Datenordner in die Ablage.

    Args:
        ziel: Wohin kopiert wird. Ohne Angabe in :func:`ablage` mit
            aktuellem Stempel.

    Returns:
        Der neue Ordner.

    Raises:
        Fehler: Wenn der Datenordner fehlt oder nicht kopierbar ist.
    """
    quelle = orte.datenordner()

    if not quelle.is_dir():
        raise Fehler(
            f"Es gibt keinen Datenordner unter {quelle}. Das Programm hat "
            "noch nie gelaufen, es gibt also nichts zu sichern."
        )

    ordner = ziel if ziel is not None else ablage() / stempel()

    # In den Ordner selbst kopieren, nicht seinen Inhalt hinein: Sonst
    # lägen die Dateien eine Ebene zu tief und der Ordner sähe nach einem
    # Datenordner aus, wäre aber keiner.
    try:
        shutil.copytree(quelle, ordner, dirs_exist_ok=True)
    except OSError as grund:
        raise Fehler(
            f"Die Sicherung nach {ordner} ist nicht geglückt: {grund}"
        ) from grund

    return ordner


def alte(grenze: int = 10) -> list[Path]:
    """Sucht die Sicherungen, die man wegwerfen könnte.

    Nicht das Löschen selbst — das ist eine Entscheidung, die jemand
    treffen muss. Diese Funktion sagt nur, welche zur Löschung anstehen.

    Args:
        grenze: Wie viele die neuesten bleiben.

    Returns:
        Die älteren Ordner, der älteste zuerst.
    """
    ordner = ablage()

    if not ordner.is_dir():
        return []

    alle = sorted(
        (pfad for pfad in ordner.iterdir() if pfad.is_dir()),
        key=lambda p: p.name,
        reverse=True,
    )

    # Der älteste zuerst: So loescht man in der Reihenfolge, in der man
    # sie findet, und die juengste steht immer noch, solange man sie braucht.
    return list(reversed(alle[grenze:]))


def groesse(pfad: Path) -> str:
    """Rechnet die Größe eines Ordners zusammen.

    Args:
        pfad: Der Ordner.

    Returns:
        Der Text, etwa ``12,4 MB``. Wird es unlesbar, ein Fragezeichen.
    """
    try:
        bytes_ = sum(f.stat().st_size for f in pfad.rglob("*") if f.is_file())
    except OSError:  # pragma: no cover - nur bei einem Rechteproblem
        return "?"

    # Die Zahl braucht das deutsche Komma. Mit ``:,.1f`` kommt ein Punkt
    # und ein Komma als Tausendertrennzeichen; beides wird hier vertauscht,
    # ohne dass eine Zahl mit Tausendern verloren ginge.
    roh = f"{bytes_ / 1048576:.1f}".replace(".", ",")
    return f"{roh} MB"


def texte() -> list[str]:
    """Baut die Zeilen für den Bildschirm.

    Returns:
        Je eine Zeile pro Sicherung, die neueste zuerst, mit einem Hinweis
        auf die, die zur Löschung anstehen.
    """
    ordner = ablage()
    if not ordner.is_dir():
        return ["Noch keine Sicherung."]

    alle = sorted(
        (pfad for pfad in ordner.iterdir() if pfad.is_dir()),
        key=lambda p: p.name,
        reverse=True,
    )
    # Der Vergleich muss auf den Pfaden passen, nicht auf den Namen: Ein Name
    # ist Text, alte() gibt Pfade zurueck, und ein Name in einer Menge von
    # Pfaden stimmt nie.
    alt = set(alte())

    zeilen = []
    for pfad in alle:
        zusatz = "  ·  wäre die nächste zum Wegwerfen" if pfad in alt else ""
        zeilen.append(f"{pfad.name}   {groesse(pfad)}{zusatz}")

    return zeilen
