"""Die Aktionen des Fensters — jede genau einmal.

**Eine Aktion, zwei Plätze.** Menü und Werkzeugleiste zeigen dieselben
Befehle, und das geht nur, wenn es *ein* QAction gibt, das an beiden
hängt. Zwei eigene Aktionen mit demselben Kürzel sind ein Fehler, den Qt
nur mit einer Warnung quittiert — und dann feuert das Kürzel manchmal
zweimal.

Deshalb stehen hier alle Befehle an einer Stelle, und die Menüs sowie der
Balken zeigen nur noch darauf. Ein neuer Befehl kommt hierhin und nowhere
sonst hinein.

**Die Bilder.** Für drei Befehle gibt es ein passendes Standardbild von
Qt, und das nimmt die Farben des Systems an — es bleibt auf hellen wie auf
dunklen Balken lesbar. Für *Neuer Kunde* gibt es keins: Qt kennt kein
Menschenbild. Das wird gezeichnet, wie es Velox mit *Play* und *Stop*
auch macht, und zwar in der Textfarbe, damit es auf jedem Balken steht.
"""

from __future__ import annotations

from collections.abc import Callable

from faktur.gui.qt import (
    QAction,
    QIcon,
    QMainWindow,
    QPainter,
    QPixmap,
    QStyle,
    Qt,
)

__all__ = ["Befehle", "glyphe"]


def glyphe(fenster: QMainWindow, form: str) -> QIcon:
    """Zeichnet ein Bild in der Textfarbe des Fensters.

    Qt hat kein Bild für einen Menschen. Die Alternative wäre, für
    *Neuer Kunde* das gleiche Blatt zu nehmen wie für *Neues Angebot* —
    und zwei Befehle mit demselben Bild sind auf einem Balken nicht mehr
    auseinanderzuhalten.

    Gezeichnet wird in der Textfarbe, nicht in einer festen: Eine schwarze
    Figur auf einem dunklen Balken verschwindet. Velox macht es mit *Play*
    und *Stop* genauso und zeichnet bei jedem Wechsel der Erscheinung neu.

    Args:
        fenster: Das Fenster, dessen Farbe gilt.
        form: ``person`` für einen Menschen, ``plus`` für ein Blatt mit
            Kreuz.

    Returns:
        Das Bild in drei Größen.
    """
    farbe = fenster.palette().color(fenster.palette().ColorRole.WindowText)
    bild = QIcon()

    for groesse in (16, 32, 64):
        flaeche = QPixmap(groesse, groesse)
        flaeche.fill(Qt.GlobalColor.transparent)
        maler = QPainter(flaeche)
        maler.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        maler.setPen(Qt.PenStyle.NoPen)
        maler.setBrush(farbe)

        if form == "person":
            _mal_person(maler, groesse)
        else:
            _mal_plus(maler, groesse)

        maler.end()
        bild.addPixmap(flaeche)

    return bild


def _mal_person(maler: QPainter, groesse: int) -> None:
    """Zeichnet Kopf und Schultern.

    Args:
        maler: Der Maler.
        groesse: Die Kantenlänge in Pixeln.

    Returns:
        Nichts.
    """
    kopf = groesse * 0.22
    maler.drawEllipse(
        int(groesse / 2 - kopf / 2),
        int(groesse * 0.12),
        int(kopf),
        int(kopf),
    )
    breite = groesse * 0.56
    maler.drawRoundedRect(
        int(groesse / 2 - breite / 2),
        int(groesse * 0.48),
        int(breite),
        int(groesse * 0.42),
        groesse * 0.12,
        groesse * 0.12,
    )


def _mal_plus(maler: QPainter, groesse: int) -> None:
    """Zeichnet ein Blatt mit einem Kreuz darauf.

    Args:
        maler: Der Maler.
        groesse: Die Kantenlänge in Pixeln.

    Returns:
        Nichts.
    """
    rand = groesse * 0.16
    maler.drawRoundedRect(
        int(rand),
        int(rand * 0.7),
        int(groesse - 2 * rand),
        int(groesse - rand * 1.6),
        groesse * 0.06,
        groesse * 0.06,
    )


class Befehle:
    """Sammelt die Befehle des Fensters.

    Attributes:
        kunde: Neuen Kunden anlegen.
        oeffnen: Ein Dokument zum Ändern öffnen.
        angebot: Ein neues Angebot anfangen.
        abrechnen: Aus einem Angebot eine Rechnung machen.
        aendern: Den markierten Eintrag ändern.
        loeschen: Den markierten Eintrag löschen.
        stilllegen: Den markierten Eintrag stilllegen.
        suchen: Ins Suchfeld springen.
        exportieren: Für den Steuerberater ausgeben.
    """

    def __init__(self, fenster: QMainWindow) -> None:
        """Baut alle Befehle auf.

        Args:
            fenster: Das Fenster, zu dem sie gehören.
        """
        self.fenster = fenster
        stile = fenster.style()

        self.kunde = self._bau(
            fenster,
            glyphe(fenster, "person"),
            "Neuer Kunde",
            "Ctrl+Shift+K",
            fenster,
            "Einen Kunden anlegen",
        )
        self.oeffnen = self._bau(
            fenster,
            stile.standardIcon(QStyle.StandardPixmap.SP_DialogOpenButton),
            "Dokument öffnen",
            "Ctrl+O",
            fenster,
            "Ein Angebot oder eine Rechnung zum Ändern öffnen",
        )
        self.angebot = self._bau(
            fenster,
            glyphe(fenster, "plus"),
            "Neues Angebot",
            "Ctrl+N",
            fenster,
            "Ein Angebot in einem eigenen Fenster beginnen",
        )
        self.abrechnen = self._bau(
            fenster,
            stile.standardIcon(QStyle.StandardPixmap.SP_ArrowRight),
            "Aus Angebot abrechnen",
            "Ctrl+Shift+R",
            fenster,
            "Aus dem markierten Angebot eine Rechnung machen",
        )
        self.aendern = self._bau(
            fenster,
            stile.standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView),
            "Ändern",
            "Ctrl+E",
            fenster,
            "Den markierten Eintrag ändern",
        )
        self.loeschen = self._bau(
            fenster,
            stile.standardIcon(QStyle.StandardPixmap.SP_TrashIcon),
            "Löschen",
            "Backspace",
            fenster,
            "Den markierten Eintrag löschen",
        )
        self.stilllegen = self._bau(
            fenster,
            stile.standardIcon(QStyle.StandardPixmap.SP_DialogDiscardButton),
            "Stilllegen",
            "",
            fenster,
            "Den markierten Eintrag aus den Listen nehmen",
        )
        self.suchen = self._bau(
            fenster,
            stile.standardIcon(QStyle.StandardPixmap.SP_FileDialogContentsView),
            "Suchen",
            "Ctrl+F",
            fenster,
            "Ins Suchfeld der aktuellen Seite springen",
        )
        self.exportieren = self._bau(
            fenster,
            stile.standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon),
            "Exportieren…",
            "Ctrl+Shift+E",
            fenster,
            "Die Daten für den Steuerberater ausgeben",
        )

    def _bau(
        self,
        fenster: QMainWindow,
        bild: QIcon,
        text: str,
        kuerzel: str,
        eltern: object,
        hinweis: str,
    ) -> QAction:
        """Baut einen Befehl.

        Args:
            fenster: Das Fenster, zu dem der Befehl gehört.
            bild: Das Bild auf dem Balken.
            text: Was im Menü steht.
            kuerzel: Das Tastenkürzel. Leer für keinen.
            eltern: Das Objekt, an das gehängt wird.
            hinweis: Der Text, wenn man mit der Maus auf dem Balken
                stehen bleibt.

        Returns:
            Der Befehl.
        """
        aktion = QAction(bild, text, fenster)
        aktion.setToolTip(hinweis)
        if kuerzel:
            aktion.setShortcut(kuerzel)
        return aktion

    def verbinde(self, aktion: QAction, was: Callable[[], None]) -> QAction:
        """Hängt einen Befehl an seinen Zweck.

        Args:
            aktion: Der Befehl.
            was: Was bei ihm passiert.

        Returns:
            Derselbe Befehl, damit es sich hintereinander lesen lässt.
        """
        aktion.triggered.connect(was)  # type: ignore[arg-type]
        return aktion

    def zeichne_neu(self) -> None:
        """Zeichnet die eigenen Bilder neu.

        Wird gebraucht, wenn das Fenster hell oder dunkel wird. Die
        Standardbilder von Qt kümmern sich selbst darum; die beiden
        gezeichneten nicht.

        Returns:
            Nichts.
        """
        self.kunde.setIcon(glyphe(self.fenster, "person"))
        self.angebot.setIcon(glyphe(self.fenster, "plus"))
