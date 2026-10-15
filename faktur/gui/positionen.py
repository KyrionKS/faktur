"""Die Positionen eines Dokuments, alle in einer Tabelle.

**Eine Tabelle, nicht drei.** Bis 0.9 standen die Positionen auf eigenen
Bildschirmen, und die Summe stand wieder für sich. Das Umrechnen, das
Umstellen und das Löschen kosteten jeweils einen Weg aus dem Bild heraus.
Hier ist alles eine Zeile: was drinsteht, steht drin, und die Summe unten
rechnet sich bei jedem Tastendruck mit.

**Die Summe steht unten und nicht in einer Spalte mit.** Sie ändert sich
mit jedem Zeichen, und eine Zahl, die bei jedem Tastendruck springt, ist
schwerer zu lesen als eine, die still steht. Sie steht deshalb gross
darunter, und nur die rechte Spalte rechnet mit.
"""

from __future__ import annotations

import sqlite3
from typing import Any

from PySide6.QtCore import Signal

from faktur import betraege
from faktur.gui.qt import QAbstractTableModel, QModelIndex, Qt

#: Die Spalten der Tabelle.
SPALTEN = ("Bezeichnung", "Menge", "Einheit", "Einzelpreis", "Summe")

#: Die Spalte, in der die Summe steht. Sie rechnet mit, lässt sich aber
#: nicht tippen.
SUMSPALTE = 4

#: Die Spalten, in denen man tippen darf.
BEARBEITBAR = frozenset({0, 1, 2, 3})

#: Die erste der drei Spalten, die eine Zahl aufnehmen.
ZAHLEN = frozenset({1, 3})


def _wert(rolle: object) -> int:
    """Macht aus einer Rolle eine Zahl.

    Args:
        rolle: Die Rolle aus Qt.

    Returns:
        Die Zahl dahinter.
    """
    return getattr(rolle, "value", rolle)  # type: ignore[arg-type]


_ANZEIGE = Qt.ItemDataRole.DisplayRole.value
_BEARBEITEN = Qt.ItemDataRole.EditRole.value
_WAAGERECHT = Qt.Orientation.Horizontal.value


class PositionenModell(QAbstractTableModel):
    """Die Positionen eines Dokuments, beschreibbar.

    Attributes:
        positionen: Die Positionen als Liste von Wörtern.
    """

    #: Wird gesendet, sobald sich die Summe geaendert hat. Das Fenster
    #: hoert darauf und setzt die grosse Zahl unter der Tabelle.
    summen_geaendert = Signal()

    def __init__(self, preise_genau: bool = True) -> None:
        """Legt das Modell an.

        Args:
            preise_genau: Ob Einzelpreise mit zwei Nachkommastellen
                kommen. Bei Angeboten stehen sie ohne — ein Angebotspreis
                ist eine Schätzung und wird nicht auf den Cent gerechnet.
        """
        super().__init__()
        self.preise_genau = preise_genau
        self.positionen: list[dict[str, Any]] = []

    # -------------------------------------------------------------- Qt

    def rowCount(self, parent: QModelIndex | None = None) -> int:  # noqa: N802
        """Sagt, wie viele Positionen es gibt.

        Args:
            parent: Der Elternindex.

        Returns:
            Die Zahl der Zeilen.
        """
        if parent is not None and parent.isValid():
            return 0
        return len(self.positionen)

    def columnCount(self, parent: QModelIndex | None = None) -> int:  # noqa: N802
        """Sagt, wie viele Spalten es gibt.

        Args:
            parent: Der Elternindex.

        Returns:
            Die Zahl der Spalten.
        """
        if parent is not None and parent.isValid():
            return 0
        return len(SPALTEN)

    def data(self, index: QModelIndex, rolle: int = 0) -> object:
        """Gibt den Inhalt einer Zelle zurück.

        Args:
            index: Die Stelle in der Tabelle.
            rolle: Die Rolle, nach der gefragt wird.

        Returns:
            Der Inhalt, oder ``None``, wenn es keinen gibt.
        """
        if _wert(rolle) not in (_ANZEIGE, _BEARBEITEN):
            return None
        if not index.isValid():
            return None

        zeile, spalte = index.row(), index.column()
        if not (0 <= zeile < len(self.positionen)):
            return None

        position = self.positionen[zeile]
        if not (0 <= spalte < len(SPALTEN)):
            return None

        if spalte == 0:
            return str(position.get("bezeichnung", ""))
        if spalte == 1:
            return betraege.menge(position.get("menge", 0.0))
        if spalte == 2:
            return str(position.get("einheit", ""))
        if spalte == 3:
            return self._preis(position.get("preis", 0.0))
        if spalte == SUMSPALTE:
            return self._preis(self._summe_einer(position))
        return None

    def headerData(  # noqa: N802
        self, abschnitt: int, orientierung: int, rolle: int = 0
    ) -> object:
        """Gibt die Spaltentitel zurück.

        Args:
            abschnitt: Welche Spalte.
            orientierung: Waagerecht oder senkrecht.
            rolle: Die Rolle.

        Returns:
            Der Titel, oder ``None``.
        """
        if _wert(rolle) != _ANZEIGE:
            return None
        if _wert(orientierung) != _WAAGERECHT:
            return None
        if 0 <= abschnitt < len(SPALTEN):
            return SPALTEN[abschnitt]
        return None

    def setData(self, index: QModelIndex, wert: object, rolle: int = 0) -> bool:  # noqa: N802
        """Nimmt einen getippten Wert an.

        Args:
            index: Die Stelle in der Tabelle.
            wert: Der neue Wert.
            rolle: Die Rolle.

        Returns:
            ``True``, wenn etwas übernommen wurde.
        """
        if _wert(rolle) != _BEARBEITEN:
            return False
        if not index.isValid():
            return False

        zeile, spalte = index.row(), index.column()
        if not (0 <= zeile < len(self.positionen)):
            return False
        if spalte not in BEARBEITBAR:
            return False

        text = "" if wert is None else str(wert)
        self.positionen[zeile][self._feld(spalte)] = (
            betraege.zahl(text) if spalte in ZAHLEN else text.strip()
        )

        # Die Summe rechts steht in derselben Zeile und haengt dran.
        if zeile < len(self.positionen):
            self.dataChanged.emit(
                self.index(zeile, SUMSPALTE),
                self.index(zeile, SUMSPALTE),
            )
        self.summen_geaendert.emit()
        return True

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        """Sagt, wo man tippen darf.

        Args:
            index: Die Stelle in der Tabelle.

        Returns:
            Die Rechte dieser Zelle.
        """
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        if index.column() in BEARBEITBAR:
            return (
                Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsEditable
            )
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

    # ------------------------------------------------------- eigener Teil

    def _feld(self, spalte: int) -> str:
        """Sagt, wie die Spalte in der Datenbank heisst.

        Args:
            spalte: Die Nummer der Spalte.

        Returns:
            Der Name des Feldes.
        """
        return ("bezeichnung", "menge", "einheit", "preis")[spalte]

    def _preis(self, wert: float) -> str:
        """Formt einen Betrag als Text.

        Args:
            wert: Der Betrag.

        Returns:
            Der Betrag. Bei einem Angebot ohne Nachkommastellen — ein
            Angebotspreis ist eine Schätzung, und ``850 €`` liest sich
            besser als ``850,00 €``.
        """
        if self.preise_genau:
            return betraege.euro(wert)
        return (
            f"{round(wert):,} €".replace(",", "§").replace(".", ",").replace("§", ".")
        )

    def _summe_einer(self, position: dict[str, Any]) -> float:
        """Rechnet eine Position aus.

        Args:
            position: Die Position.

        Returns:
            Menge mal Preis.
        """
        return betraege.zahl(position.get("menge", 0.0)) * betraege.zahl(
            position.get("preis", 0.0)
        )

    def setze(self, positionen: list[dict[str, Any]]) -> None:
        """Legt eine Liste von Positionen in die Tabelle.

        Args:
            positionen: Die Positionen, wie sie aus der Datenbank kommen
                oder aus der Preisliste.

        Returns:
            Nichts.
        """
        self.beginResetModel()
        self.positionen = [dict(position) for position in positionen]
        self.endResetModel()
        self.summen_geaendert.emit()

    def leeren(self) -> None:
        """Nimmt alle Positionen heraus.

        Returns:
            Nichts.
        """
        self.setze([])

    def summe(self) -> float:
        """Rechnet alle Positionen zusammen.

        Returns:
            Die Summe.
        """
        return sum(self._summe_einer(p) for p in self.positionen)

    def liste(self) -> list[dict[str, Any]]:
        """Gibt die Positionen so zurück, wie :func:`faktur.dateien.dokument_speichern`
        sie nimmt.

        Returns:
            Die Positionen.
        """
        return [dict(position) for position in self.positionen]

    def haenge_an(self, position: dict[str, Any]) -> None:
        """Setzt eine Position an das Ende.

        Args:
            position: Die Position.

        Returns:
            Nichts.
        """
        self.beginInsertRows(QModelIndex(), len(self.positionen), len(self.positionen))
        self.positionen.append(dict(position))
        self.endInsertRows()
        self.summen_geaendert.emit()

    def entferne(self, zeile: int) -> bool:
        """Nimmt eine Position heraus.

        Args:
            zeile: Die Nummer der Zeile.

        Returns:
            ``True``, wenn es die Zeile gab.
        """
        if not (0 <= zeile < len(self.positionen)):
            return False
        self.beginRemoveRows(QModelIndex(), zeile, zeile)
        del self.positionen[zeile]
        self.endRemoveRows()
        self.summen_geaendert.emit()
        return True

    def verschiebe(self, zeile: int, um: int) -> bool:
        """Verschiebt eine Position nach oben oder unten.

        Args:
            zeile: Die Nummer der Zeile.
            um: ``-1`` nach oben, ``1`` nach unten.

        Returns:
            ``True``, wenn sich etwas bewegt hat.
        """
        ziel = zeile + um
        if not (0 <= zeile < len(self.positionen)):
            return False
        if not (0 <= ziel < len(self.positionen)):
            return False

        self.beginResetModel()
        self.positionen[zeile], self.positionen[ziel] = (
            self.positionen[ziel],
            self.positionen[zeile],
        )
        self.endResetModel()
        self.summen_geaendert.emit()
        return True

    def leere_zeile(self) -> int:
        """Setzt eine leere Position an das Ende und gibt ihre Zeile zurück.

        Returns:
            Die Nummer der neuen Zeile.
        """
        self.haenge_an({"bezeichnung": "", "menge": 1.0, "einheit": "", "preis": 0.0})
        return len(self.positionen) - 1

    def aus_leistung(self, leistung: sqlite3.Row) -> None:
        """Setzt eine Leistung als Position an das Ende.

        Args:
            leistung: Die Leistung aus der Datenbank.

        Returns:
            Nichts.
        """
        self.haenge_an(
            {
                "leistung_id": leistung["id"],
                "bezeichnung": leistung["bezeichnung"],
                "menge": 1.0,
                "einheit": leistung["einheit"],
                "preis": leistung["preis"],
            }
        )


__all__ = ["BEARBEITBAR", "SPALTEN", "SUMSPALTE", "PositionenModell"]
