"""Eine Tabelle, in der nie der falsche Datensatz gemeint ist.

**Warum das eigens gebaut wird.** Bis 0.8.1 hat das Programm die Zeilen
einer Liste gefiltert, aber die Liste selbst ganz gelassen. Wer auf der
Kundenliste *Zeta Tonwerk* suchte, sah *Zeta Tonwerk* und bekam *Alpha
Klangstudio* — und konnte mit ``Entf`` einen fremden samt Dokumenten
löschen.

In Qt wäre das doppelt möglich: über einen Index in eine andere Liste, und
über einen ``QSortFilterProxyModel``, der beim Sortieren die Reihenfolge
vertauscht.

Deshalb wird hier **kein** Proxy benutzt. Das Modell hält Datensatz und
Anzeigezelle zusammen, und Sortieren wie Filtern passieren **vor** dem
Übergeben: Die Liste, die das Modell hält, ist exakt die Liste, die man
sieht. Es gibt keinen Index, der auf etwas anderes zeigen könnte.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable, Sequence
from functools import cmp_to_key

from faktur.gui.qt import QAbstractTableModel, QModelIndex, Qt

#: Ein Datensatz aus der Datenbank. Eine Zeile mit Namen, die man mit
#: ``datensatz["firma"]`` anspricht.
Datensatz = sqlite3.Row

#: Ein beliebiger Datensatz, wie ihn die Seiten liefern.
Eintrag = object

#: Wie eine Zelle gebaut wird: aus einem Datensatz eine Liste von Texten.
Zellen = Callable[[Eintrag], list[str]]

#: Wie zwei Zeilen verglichen werden: nimmt die Paare, gibt eine Zahl zurück.
Vergleich = Callable[[tuple[Eintrag, list[str]], tuple[Eintrag, list[str]]], int]


def nach_text(spalte: int) -> Vergleich:
    """Vergleicht zwei Zeilen nach dem Wort der Spalte.

    Args:
        spalte: Die Nummer der Spalte.

    Returns:
        Eine Vergleichsfunktion für :func:`sorted`.
    """

    def vergleiche(a: tuple[Eintrag, list[str]], b: tuple[Eintrag, list[str]]) -> int:
        """Stellt die Wörter zweier Zellen gegenüber.

        Args:
            a: Die eine Zeile.
            b: Die andere Zeile.

        Returns:
            Negativ, null oder positiv wie bei ``sorted``.
        """
        return (a[1][spalte] > b[1][spalte]) - (a[1][spalte] < b[1][spalte])

    return vergleiche


def nach_zahl(spalte: int) -> Vergleich:
    """Vergleicht zwei Zeilen nach der Zahl in der Spalte.

    Eine Betragsspalte, in der ``1.180,00`` vor ``980,00`` steht, läge
    sonst. Zellen ohne Zahl, etwa ``—``, stehen hinten.

    Args:
        spalte: Die Nummer der Spalte.

    Returns:
        Eine Vergleichsfunktion für :func:`sorted`.
    """

    def vergleiche(a: tuple[Eintrag, list[str]], b: tuple[Eintrag, list[str]]) -> int:
        """Stellt die Zahlen zweier Zellen gegenüber.

        Args:
            a: Die eine Zeile.
            b: Die andere Zeile.

        Returns:
            Negativ, null oder positiv wie bei ``sorted``.
        """
        xa, xb = zahl_aus(a[1][spalte]), zahl_aus(b[1][spalte])
        if xa == xb:
            return (a[1][spalte] > b[1][spalte]) - (a[1][spalte] < b[1][spalte])
        return (xa > xb) - (xa < xb)

    return vergleiche


def zahl_aus(text: str) -> float | None:
    """Liest die erste Zahl aus einer Zelle.

    Args:
        text: Der Zelltext, etwa ``1.180,00 €``.

    Returns:
        Die Zahl, oder ``None``, wenn keine drinsteht.
    """
    ziffern = ""
    for zeichen in text:
        if zeichen.isdigit() or zeichen == ",":
            ziffern += zeichen
        elif ziffern:
            break
    if not ziffern or ziffern == ",":
        return None
    try:
        return float(ziffern.replace(",", "."))
    except ValueError:
        return None


def _gueltig(parent: QModelIndex | None) -> bool:
    """Sagt, ob ein Elternindex wirklich auf eine Zeile zeigt.

    **Qt fragt nie mit ``None``**, sondern mit einer leer konstruierten
    ``QModelIndex``. Ein Test ``parent is not None`` ist deshalb immer
    wahr, das Modell meldet null Zeilen und null Spalten, und die Tabelle
    bleibt leer — ohne jeden Fehler.

    Args:
        parent: Der Elternindex aus Qt.

    Returns:
        ``True``, wenn es ein echter Elternindex ist.
    """
    return parent is not None and parent.isValid()


def _wert(rolle: object) -> int:
    """Macht aus einer Rolle oder Orientierung eine Zahl.

    Qt übergib seine eigenen Aufzählungen, und die sind je nach Version mal
    Zahlen und mal ein eigener Typ. ``.value`` gibt es bei beiden, bei
    nackten Zahlen eben nicht. ``int()`` dagegen versagt bei den
    Aufzählungen — deshalb wird es hier nirgends benutzt.

    Args:
        rolle: Die Rolle, Orientierung oder Sortierung aus Qt.

    Returns:
        Die Zahl dahinter.
    """
    return getattr(rolle, "value", rolle)  # type: ignore[arg-type]


#: Die drei Vergleiche, die das Modell braucht, einmal ausgerechnet.
_ANZEIGE = Qt.ItemDataRole.DisplayRole.value
_WAAGERECHT = Qt.Orientation.Horizontal.value
_ABSTEIGEND = Qt.SortOrder.DescendingOrder.value


class ZeilenModell(QAbstractTableModel):
    """Zeigt Datensätze an und gibt sie unbeschädigt zurück.

    Attributes:
        spalten: Die Spaltentitel.
        paare: Die angezeigten Zeilen: je ein Paar aus Datensatz und Zellen.
    """

    def __init__(
        self,
        spalten: Sequence[str],
        zellen: Zellen,
        vergleiche: dict[int, Vergleich] | None = None,
    ) -> None:
        """Legt das Modell an.

        Args:
            spalten: Die Spaltentitel in der Reihenfolge der Anzeige.
            zellen: Baut aus einem Datensatz die Zellen.
            vergleiche: Je Spaltennummer eine eigene Vergleichsfunktion.
                Fehlt eine, wird der Wort der Zelle verglichen.
        """
        super().__init__()
        self.spalten = list(spalten)
        self._zellen = zellen
        self._vergleiche = dict(vergleiche or {})
        self.paare: list[tuple[Eintrag, list[str]]] = []
        self._merke_spalte: int | None = None
        self._merke_auf: bool = True

    # -------------------------------------------------------------- Qt

    def rowCount(self, parent: QModelIndex | None = None) -> int:  # noqa: N802
        """Sagt, wie viele Zeilen es gibt.

        Args:
            parent: Der Elternindex. Qt fragt auch nach der Zahl der Kinder
                eines certain Index, dann ist er gültig.

        Returns:
            Die Zahl der Zeilen.
        """
        return 0 if _gueltig(parent) else len(self.paare)

    def columnCount(self, parent: QModelIndex | None = None) -> int:  # noqa: N802
        """Sagt, wie viele Spalten es gibt.

        Args:
            parent: Der Elternindex, wie bei :meth:`rowCount`.

        Returns:
            Die Zahl der Spalten.
        """
        return 0 if _gueltig(parent) else len(self.spalten)

    def data(self, index: QModelIndex, rolle: int = 0) -> object:
        """Gibt den Text einer Zelle zurück.

        **Für alles andere kommt ``None`` zurück, nicht ``""``.** Qt fragt
        auch nach Rollen wie ``SizeHintRole``, um Zeilen und Spalten zu
        messen. Ein Leerstring gilt ihm als *ein Wert*, den es nicht in
        eine Größe umrechnen kann — der Kopf der Tabelle bliebe dann null
        hoch, ohne jede Fehlermeldung.

        Args:
            index: Die Stelle in der Tabelle.
            rolle: Die Rolle, nach der gefragt wird.

        Returns:
            Der Text der Zelle, oder ``None``, wenn es keinen gibt.
        """
        if _wert(rolle) != _ANZEIGE:
            return None
        if not index.isValid():
            return None
        zeile, spalte = index.row(), index.column()
        if not (0 <= zeile < len(self.paare)):
            return None
        if not (0 <= spalte < len(self.paare[zeile][1])):
            return None
        return self.paare[zeile][1][spalte]

    def headerData(  # noqa: N802
        self, abschnitt: int, orientierung: int, rolle: int = 0
    ) -> object:
        """Gibt die Spaltentitel zurück.

        Args:
            abschnitt: Welche Zeile der Kopfzeile.
            orientierung: Waagerecht oder senkrecht.
            rolle: Die Rolle, nach der gefragt wird.

        Returns:
            Der Titel der Spalte, oder ``None``, wenn es keinen gibt.
        """
        if _wert(rolle) != _ANZEIGE:
            return None
        if _wert(orientierung) != _WAAGERECHT:
            return None
        if 0 <= abschnitt < len(self.spalten):
            return self.spalten[abschnitt]
        return None

    def sort(self, spalte: int, ordnung: int = 0) -> None:  # noqa: N802
        """Sortiert die Tabelle nach einer Spalte, wenn Qt das verlangt.

        Args:
            spalte: Die Nummer der Spalte.
            ordnung: ``0`` aufsteigend, ``1`` absteigend.

        Returns:
            Nichts.
        """
        self.sortiere(spalte, _wert(ordnung) != _ABSTEIGEND)

    # --------------------------------------------------------- eigener Teil

    def setze(self, datensaetze: Sequence[Eintrag]) -> None:
        """Legt eine neue Liste von Datensätzen in die Tabelle.

        Args:
            datensaetze: Die Datensätze in der Reihenfolge, in der sie
                erscheinen sollen.

        Returns:
            Nichts.
        """
        self.beginResetModel()
        self.paare = [(datensatz, self.zellen(datensatz)) for datensatz in datensaetze]
        self.endResetModel()
        if self._merke_spalte is not None and self.paare:
            self.sortiere(self._merke_spalte, self._merke_auf)

    def zellen(self, datensatz: Eintrag) -> list[str]:
        """Baut aus einem Datensatz die Texte seiner Zeile.

        **Es gibt nur diese eine Stelle.** Die Suche fragt hier dieselben
        Texte ab, mit denen danach gefiltert wird. Zwei Funktionen wären
        zwei Wahrheiten, und die dürften nicht auseinanderlaufen.

        Args:
            datensatz: Der Datensatz aus der Datenbank.

        Returns:
            Die Zellen der Zeile.
        """
        return self._zellen(datensatz)

    def datensatz(self, zeile: int) -> Eintrag | None:
        """Gibt den Datensatz hinter einer Zeile zurück.

        Args:
            zeile: Die Nummer der Zeile.

        Returns:
            Der Datensatz, oder ``None`` bei einer Zahl außerhalb der
            Liste. Damit fasst ein Klick ins Leere nichts an.
        """
        if 0 <= zeile < len(self.paare):
            return self.paare[zeile][0]
        return None

    def zeile(self, datensatz: Eintrag) -> int:
        """Sagt, in welcher Zeile ein Datensatz steht.

        Args:
            datensatz: Der gesuchte Datensatz.

        Returns:
            Die Zeilennummer, oder ``-1``, wenn er nicht in der Liste steht.
        """
        for nummer, (kandidat, _zellen) in enumerate(self.paare):
            if kandidat is datensatz:
                return nummer
        return -1

    def sortiere(self, spalte: int, aufsteigend: bool = True) -> None:
        """Sortiert die Tabelle nach einer Spalte.

        Sortiert wird die Liste der Paare, nicht die Anzeige. Damit bleibt
        der Datensatz bei seiner Zeile, und die Tabelle kann sich hinterher
        nicht mehr von der Liste unterscheiden.

        Args:
            spalte: Die Nummer der Spalte.
            aufsteigend: Aufsteigend oder absteigend.

        Returns:
            Nichts.
        """
        self._merke_spalte = spalte
        self._merke_auf = aufsteigend
        if not self.paare or not (0 <= spalte < len(self.spalten)):
            return

        vergleiche = self._vergleiche.get(spalte, nach_text(spalte))

        self.beginResetModel()
        self.paare.sort(key=cmp_to_key(vergleiche), reverse=not aufsteigend)
        self.endResetModel()

    def waert(self, zeile: int, spalte: int) -> str:
        """Gibt eine Zelle als Text zurück, ohne über Qt zu gehen.

        Args:
            zeile: Die Nummer der Zeile.
            spalte: Die Nummer der Spalte.

        Returns:
            Der Text, oder ``""``, wenn es die Zelle nicht gibt.
        """
        if not (0 <= zeile < len(self.paare)):
            return ""
        zellen = self.paare[zeile][1]
        if not (0 <= spalte < len(zellen)):
            return ""
        return zellen[spalte]
