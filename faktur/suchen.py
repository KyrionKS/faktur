"""Eine Liste, in der man etwas suchen kann.

Auf der Kundenliste steht seit der ersten Fassung *Suchen* in der Fußzeile —
und die Taste tat nichts. Kein Test hat sie berührt, deshalb ist es niemandem
aufgefallen.

Die Suche ist jetzt da, und zwar so, wie man sie in einem Menüprogramm
braucht: tippen, und es wird gefiltert, während man tippt. Kein Dialog, kein
Enter nötig, weil bei zwanzig Kunden niemand einen Dialog möchte.

Suchen lässt sich nur sinnvoll auf einer Liste, die auch sonst da ist — nicht
nach etwas, das es nicht gibt. Deshalb gibt es hier eine einzige Liste, und
jeder Bildschirm, der eine hat, benutzt sie.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import TypeVar

from textual.binding import Binding
from textual.widgets import Input, Static

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


class Suchfeld(Input):
    """Ein Eingabefeld, das sofort filtert.

    Es meldet jede Änderung an die Liste, ohne dass man etwas bestätigen
    muss. Bei zwanzig Kunden ist ein Dialog lästig; bei zweihundert ist die
    Liste ohne Suchfeld unbrauchbar.

    Attributes:
        geaendert: Wird mit dem aktuellen Begriff gerufen.
    """

    BINDINGS = [Binding("escape", "leeren", "Suche leeren", show=False)]

    def __init__(
        self, geaendert: Callable[[str], None], platzhalter: str = "suchen"
    ) -> None:
        """Legt das Feld an.

        Args:
            geaendert: Wird gerufen, sobald sich der Text ändert.
            platzhalter: Der Text, solange nichts getippt ist.
        """
        super().__init__(placeholder=platzhalter, id="suche")
        self.geaendert = geaendert
        self.add_class("suchfeld")

    def on_input_changed(self, event: Input.Changed) -> None:
        """Sucht weiter, während getippt wird.

        Args:
            event: Die Nachricht des Eingabefeldes.
        """
        event.stop()
        self.geaendert(event.value)

    def action_leeren(self) -> None:
        """Leert das Feld und sucht wieder alles."""
        self.value = ""
        self.geaendert("")


class SuchZeile(Static):
    """Die Zeile, die sagt, wie viele Zeilen übrig sind."""

    def zeige(
        self,
        gefunden: int,
        gesamt: int,
        begriff: str,
        einheit: str = "Einträge",
        einzeln: str = "Eintrag",
    ) -> None:
        """Sagt an, wie viel die Suche übrig gelassen hat.

        Ohne Suchbegriff steht dort einfach, wie viele es gibt. Bei null
        Treffern steht das ausdrücklich da — eine leere Liste sieht sonst
        aus, als sei das Programm kaputt.

        Args:
            gefunden: Wie viele Zeilen passen.
            gesamt: Wie viele es insgesamt gab.
            begriff: Was gesucht wurde.
            einheit: Die Pluralform, zum Beispiel *Dokumente*.
            einzeln: Die Singularform, zum Beispiel *Dokument*.
        """
        if not begriff.strip():
            self.update(f"{gesamt} {einzeln if gesamt == 1 else einheit}.")
            self.set_class(False, "leer")
            return

        if gefunden == 0:
            self.update(f"{gesamt} gefunden. Nichts passt zu „{begriff}“.")
            self.set_class(True, "leer")
        elif gefunden < gesamt:
            self.update(f"{gefunden} von {gesamt} passen zu „{begriff}“.")
            self.set_class(False, "leer")
        else:
            self.update(f"Alle {gesamt} passen zu „{begriff}“.")
            self.set_class(False, "leer")
