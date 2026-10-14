"""Eine Liste, in der man etwas suchen kann.

Auf der Kundenliste steht seit der ersten Fassung *Suchen* in der Fußzeile —
und die Taste tat nichts. Kein Test hat sie berührt, deshalb ist es niemandem
aufgefallen.

Die Suche ist jetzt da, und zwar so, wie man sie in einem Menüprogramm
braucht: tippen, und es wird gefiltert, während man tippt. Kein Dialog, kein
Enter nötig, weil bei zwanzig Kunden niemand einen Dialog möchte.

Suchen lässt sich nur sinnvoll auf einer Liste, die auch sonst da ist — nicht
nach etwas, das es nicht gibt. Deshalb gibt es hier eine einzige Liste, und
jede Seite, die eine hat, benutzt sie.

**Hier steht nur die Regel, keine Oberfläche.** Das Suchfeld selbst liegt in
:mod:`faktur.gui.suchen`. Diese Trennung ist Absicht: Die Regel *was passt
zusammen* lässt sich ohne Fenster prüfen, und der ganze Rest des Programms
prüft sie ohne Fenster.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TypeVar

#: Der Datensatz, zu dem eine Zeile gehoert. Ein Kunde, ein Dokument — was
#: auch immer die Liste gerade zeigt. Nur fuer die Typangabe, damit ein
#: Bildschirm nicht um ein cast() herumkommt.
D = TypeVar("D")


def passt(zeile: Sequence[str], begriff: str) -> bool:
    """Sagt, ob eine Zeile zum Suchbegriff gehört.

    Der Vergleich ist absichtlich einfach: gleiche Zeichen ohne Beachtung der
    Gross- und Kleinschreibung, und der Begriff darf auch mitten in einem
    Wort stehen. Wer *check* tippt und *Soundcheck GmbH* findet, will
    *check* finden.

    Args:
        zeile: Die Felder der Zeile.
        begriff: Was gesucht wird.

    Returns:
        ``True``, wenn etwas passt. Bei leerem Begriff passt alles.
    """
    if not begriff.strip():
        return True

    gesucht = begriff.strip().casefold()

    return any(gesucht in (feld or "").casefold() for feld in zeile)


def filtern(zeilen: Sequence[Sequence[str]], begriff: str) -> list[tuple[str, ...]]:
    """Hält nur die Zeilen, die zum Begriff passen.

    Nur für Bildschirme, die außer der Zeile nichts brauchen. Wer auf der
    Zeile einen Rücksprung in die Datenbank macht, nimmt :func:`sichtbar`.

    Args:
        zeilen: Alle Zeilen.
        begriff: Was gesucht wird.

    Returns:
        Die passenden Zeilen, in ihrer alten Reihenfolge.
    """
    if not begriff.strip():
        return [tuple(z) for z in zeilen]

    return [tuple(z) for z in zeilen if passt(z, begriff)]


def sichtbar(
    datensaetze: Sequence[D], zeilen: Sequence[Sequence[str]], begriff: str
) -> list[tuple[D, tuple[str, ...]]]:
    """Hält nur, was zum Begriff passt — Datensatz und Zeile zusammen.

    Die Liste zeigt Zeilen, und wenn man eine Zeile anklickt, braucht der
    Bildschirm den Datensatz dahinter. Beides muss sich nach dem Filtern
    noch an derselben Stelle befinden, sonst öffnet man den **falschen**.

    Genau das ist bis 0.8.2 auf der Kundenliste passiert: Dort wurden nur
    die Zeilen gefiltert, die Kundenliste selbst blieb ganz. Wer *Zeta
    Tonwerk* suchte, sah *Zeta Tonwerk*, öffnete *Alpha Klangstudio* — und
    konnte, mit derselben Tastendruckfolge, einen fremden Kunden samt
    Dokumenten löschen.

    Deshalb wird hier **über die Indizes** gefiltert und nicht über die
    Zeilenwerte. Zwei Kunden können denselben Namen haben, zwei Leistungen
    dieselbe Bezeichnung und denselben Preis. Ein Vergleich nach Werten
    käme bei zwei gleichen Zeilen nicht zu einem Ergebnis, und ein
    Rücksprung über eine Spalte — Kennung oder Nummer — wäre nur so lange
    richtig, wie diese Spalte eindeutig ist. Beides hat schon Fehler gemacht.

    Bei der Nummer kommt hinzu, dass sie seit 0.9.0 **gar nicht** eindeutig
    ist: Die Nummer ist eine Projektnummer, und Angebot und Rechnung eines
    Projekts tragen dieselbe. Ein Rücksprung über sie hätte hier nicht
    zufällig funktioniert, sondern immer danebengelegen.

    Args:
        datensaetze: Die Datensätze in ihrer alten Reihenfolge.
        zeilen: Die Textzeilen dazu, in derselben Reihenfolge.
        begriff: Was gesucht wird.

    Returns:
        Die passenden Paare aus Datensatz und Zeile, in alter Reihenfolge.

    Raises:
        ValueError: Wenn die beiden Listen nicht gleich lang sind. Sie
            müssen sich decken, sonst stimmt der Rücksprung nicht mehr.
    """
    if len(datensaetze) != len(zeilen):
        raise ValueError(
            f"Datensätze und Zeilen passen nicht zusammen: "
            f"{len(datensaetze)} gegen {len(zeilen)}"
        )

    return [
        (datensatz, tuple(zeile))
        for datensatz, zeile in zip(datensaetze, zeilen, strict=True)
        if passt(zeile, begriff)
    ]
