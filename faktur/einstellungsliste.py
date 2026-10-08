"""Einstellungen, die eine Liste von Werten haben.

Der Bildschirm *Aussehen* hat drei Sorten von Zeilen: eine zum Wechseln der
Dokumentart, zwei mit einer Größe, und dreizehn Blöcke, die man ein- und
ausschaltet. Alle stehen untereinander, und die Tasten müssen bei jeder Sorte
etwas anderes tun.

Dafür stehen die Entscheidungen in zwei reinen Funktionen ohne jede
Oberfläche: :func:`naechster_wert` und :func:`schaltet_um`. Der Bildschirm
zeichnet nur noch. Das ist derselbe Weg, den das ganze Programm geht —
Bildschirme beschreiben, wie etwas aussieht, die Regeln stehen woanders.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Literal

from rich.text import Text
from textual.binding import Binding
from textual.widgets import Static

from faktur.farben import AKZENT, SEKUNDAER

#: Der Pfeil vor der bewegten Zeile.
PFEIL = "▶"

#: Der Platz, den der Pfeil einnimmt, damit die Spalten nicht springen.
PFEIL_RAUM = "  "

#: Ein angeschalteter Block.
#:
#: Bewusst ``●`` und nicht ``☑``: Beide stehen im Block Geometric Shapes,
#: in dem auch der Pfeil der Auswahlliste steht. Der ist in jedem Terminal
#: zu sehen, in dem dieses Programm überhaupt läuft. ``☑`` steht in einem
#: anderen Block und fehlt in manchen Schriften.
AN = "●"

#: Ein abgeschalteter Block.
AUS = "○"

#: Wie ein Wert im Bildschirm heißt, abweichend von dem, was gespeichert
#: wird. Technische Bezeichner liest niemand gern.
ANZEIGE = {
    "angebot": "Angebot",
    "rechnung": "Rechnung",
}

#: Die Pfeile um einen Wert herum.
RAUF = "◀"
RUNTER = "▸"

#: Wie breit die Titelspalte wird.
SPALTE_TITEL = 20

#: Wie die Gruppen heißen, in denen die Blöcke stehen.
GRUPPEN = {
    "kopf": "Absender",
    "abschluss": "Abschluss",
    "fuss": "Fußzeile",
}


def naechster_wert(werte: Sequence[str], jetzt: str, richtung: int) -> str:
    """Sucht den Wert neben dem jetzigen.

    An den Enden wird nicht gewickelt. Wer dreimal nach rechts drückt,
    bleibt stehen, statt unerwartet wieder bei *klein* zu landen.

    Args:
        werte: Alle möglichen Werte in ihrer Reihenfolge.
        jetzt: Der jetzige Wert.
        richtung: ``1`` für vorwärts, ``-1`` für zurück.

    Returns:
        Der neue Wert. Ohne Richtung oder bei einem unbekannten ``jetzt``
        kommt der erste Wert zurück.
    """
    if not werte:
        return jetzt

    if jetzt not in werte:
        return werte[0]

    if richtung not in (1, -1):
        return jetzt

    nummer = werte.index(jetzt) + richtung
    return werte[max(0, min(nummer, len(werte) - 1))]


def schaltet_um(an: frozenset[str], block: str) -> frozenset[str]:
    """Schaltet einen Block um.

    Args:
        an: Die Namen der eingeschalteten Blöcke.
        block: Der Name des Blocks.

    Returns:
        Die neue Menge.
    """
    if block in an:
        return an - {block}
    return an | {block}


Arten = Literal["art", "groesse", "block"]


@dataclass
class Zeile:
    """Eine bedienbare Zeile im Bildschirm.

    Attributes:
        art: Was für eine Zeile das ist.
        titel: Der Name, wie er im Bildschirm steht.
        werte: Die möglichen Werte, bei einer Größe.
        wert: Der jetzige Wert.
        an: Bei einem Block, ob er eingeschaltet ist.
        block: Bei einem Block, sein Name.
        gruppe: Nur bei der ersten Zeile einer Gruppe gesetzt.
    """

    art: Arten
    titel: str = ""
    werte: tuple[str, ...] = ()
    wert: str = ""
    an: bool = False
    block: str = ""
    gruppe: str = ""


def bauen(
    art: str,
    logo: str,
    text: str,
    bloecke: Sequence[tuple[str, str, str]],
    an: frozenset[str],
) -> list[Zeile]:
    """Baut alle Zeilen in der Reihenfolge der Anzeige.

    Args:
        art: Die gerade gezeigte Dokumentart.
        logo: Der Name der Logogröße.
        text: Der Name der Textgröße.
        bloecke: Name, Ort und Titel der Blöcke in ihrer Reihenfolge.
        an: Die Namen der eingeschalteten Blöcke.

    Returns:
        Die Zeilen des Bildschirms.
    """
    zeilen: list[Zeile] = [
        Zeile(
            art="art",
            titel="Dokumentart",
            werte=("angebot", "rechnung"),
            wert=art,
        ),
        Zeile(
            art="groesse",
            titel="Logogröße",
            werte=("klein", "mittel", "gross"),
            wert=logo,
        ),
        Zeile(
            art="groesse",
            titel="Schriftgröße",
            werte=("klein", "normal", "gross"),
            wert=text,
        ),
    ]

    vorige_gruppe = ""
    for name, ort, titel in bloecke:
        gruppe = GRUPPEN.get(ort, "")

        zeilen.append(
            Zeile(
                art="block",
                titel=titel,
                block=name,
                an=name in an,
                # Die Überschrift steht nur auf der ersten Zeile einer
                # Gruppe. Sonst stünde „Absender" siebenmal im Bild.
                gruppe="" if gruppe == vorige_gruppe else gruppe,
            )
        )
        vorige_gruppe = gruppe

    return zeilen


class Einstellungen(Static):
    """Eine Liste aus Schaltern und Werten.

    ``↑`` und ``↓`` bewegen sich. Auf einer Zeile mit Werten ändern ``←``
    und ``→`` den Wert, auf einer Zeile mit einem Block schaltet
    ``Leertaste``. Auf der obersten Zeile wechseln ``←`` und ``→`` die
    Dokumentart.

    Attributes:
        zeilen: Die Zeilen in der Reihenfolge der Anzeige.
        index: Der Index der bewegten Zeile.
        geaendert: Wird mit der geänderten Zeile gerufen.
        art_gewechselt: Wird gerufen, wenn die Dokumentart wechselt.
    """

    BINDINGS = [
        Binding("up", "hoch", "Hoch", show=False),
        Binding("down", "runter", "Runter", show=False),
        Binding("left", "links", "Weniger", show=False),
        Binding("right", "rechts", "Mehr", show=False),
        Binding("space,enter", "umschalten", "Umschalten", show=True),
    ]

    can_focus = True

    def __init__(
        self,
        zeilen: list[Zeile],
        geaendert: Callable[[Zeile], None],
        art_gewechselt: Callable[[], None],
    ) -> None:
        """Legt die Liste an.

        Args:
            zeilen: Die Zeilen in der Reihenfolge der Anzeige.
            geaendert: Wird mit der Zeile gerufen, die sich geändert hat.
                Welche es war, steht in der Zeile. Sonst müsste der
                Bildschirm raten, was sich geändert hat.
            art_gewechselt: Wird gerufen, wenn die Dokumentart wechselt.
        """
        super().__init__()
        self.zeilen = zeilen
        self.index = 0
        self.geaendert = geaendert
        self.art_gewechselt = art_gewechselt
        self.add_class("auswahl")

    def aktuelle(self) -> Zeile | None:
        """Nennt die Zeile, auf der der Cursor steht.

        Returns:
            Die Zeile, oder ``None``, wenn die Liste leer ist.
        """
        if not self.zeilen:
            return None
        return self.zeilen[max(0, min(self.index, len(self.zeilen) - 1))]

    def an(self) -> frozenset[str]:
        """Nennt die gerade eingeschalteten Blöcke.

        Returns:
            Die Namen der Blöcke.
        """
        return frozenset(zeile.block for zeile in self.zeilen if zeile.an)

    def setze_zeilen(self, zeilen: list[Zeile]) -> None:
        """Nimmt eine neue Liste und behält die Position.

        Args:
            zeilen: Die neuen Zeilen.
        """
        self.zeilen = zeilen
        self.index = max(0, min(self.index, len(zeilen) - 1))
        self.refresh()

    def render(self) -> Text:
        """Zeichnet die Liste.

        Returns:
            Der Text für die Anzeige.
        """
        text = Text()

        for nummer, zeile in enumerate(self.zeilen):
            if zeile.gruppe:
                text.append(f"  {zeile.gruppe}\n", style=f"dim {SEKUNDAER}")

            bewegt = nummer == self.index
            raus = Text()

            raus.append(
                f"{PFEIL} " if bewegt else PFEIL_RAUM,
                style=f"bold {AKZENT}" if bewegt else "",
            )
            raus.append(
                f"{zeile.titel:<{SPALTE_TITEL}}",
                style=f"bold {AKZENT}" if bewegt else "",
            )

            if zeile.art in ("art", "groesse"):
                raus.append(
                    f" {RAUF} {ANZEIGE.get(zeile.wert, zeile.wert):<8} {RUNTER}",
                    style=f"bold {AKZENT}" if bewegt else f"dim {SEKUNDAER}",
                )
            elif zeile.art == "block":
                raus.append(
                    f" {AN if zeile.an else AUS}",
                    style=("bold " if bewegt else "")
                    + (AKZENT if zeile.an else SEKUNDAER),
                )

            raus.append("\n")
            text.append(raus)

        return text

    def action_hoch(self) -> None:
        """Geht eine Zeile nach oben."""
        self._bewege(-1)

    def action_runter(self) -> None:
        """Geht eine Zeile nach unten."""
        self._bewege(1)

    def _bewege(self, schritt: int) -> None:
        """Bewegt den Cursor, ohne über die Enden hinaus.

        Args:
            schritt: Wie viele Plätze vor oder zurück.
        """
        if not self.zeilen:
            return
        self.index = max(0, min(self.index + schritt, len(self.zeilen) - 1))
        self.refresh()

    def action_links(self) -> None:
        """Nimmt den Wert davor."""
        self._wechsle_wert(-1)

    def action_rechts(self) -> None:
        """Nimmt den Wert danach."""
        self._wechsle_wert(1)

    def action_umschalten(self) -> None:
        """Schaltet den Block um, der gerade dran ist."""
        zeile = self.aktuelle()
        if zeile is None or zeile.art != "block":
            return

        zeile.an = not zeile.an
        self.refresh()
        self.geaendert(zeile)

    def _wechsle_wert(self, richtung: int) -> None:
        """Ändert die Zeile, auf der der Cursor steht.

        Args:
            richtung: ``1`` für vorwärts, ``-1`` für zurück.
        """
        zeile = self.aktuelle()
        if zeile is None:
            return

        if zeile.art == "art":
            self.art_gewechselt()
            return

        if zeile.art != "groesse" or not zeile.werte:
            return

        zeile.wert = naechster_wert(zeile.werte, zeile.wert, richtung)
        self.refresh()
        self.geaendert(zeile)

