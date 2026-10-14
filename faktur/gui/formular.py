"""Das Blatt zum Ausfüllen.

**Ein Blatt, kein Bildschirmstapel.** Alle Felder eines Datensatzes stehen
untereinander, man sieht sie auf einen Blick, und *Speichern* schreibt
alles auf einmal. Wer drei Felder ändert und dann abbricht, hat nichts
geändert.

Alle Formulare im Programm sind dasselbe Blatt mit anderen Feldern. Der
Kunde, die Leistung, später der Dokumentkopf und die Positionen — es ist
immer dieselbe Form, deshalb steht sie hier und nicht viermal im Code.

**Geprüft wird nur das Nötige.** Eine Firma muss einen Namen haben, ein
Preis darf nicht negativ sein. Eine E-Mail-Adresse wird nicht geprüft:
sie zu prüfen heißt, sie zu verbieten, und eine Adresse, die jemand
sonst nirgends nehmen würde, ist besser als gar keine.
"""

from __future__ import annotations

import sqlite3
from typing import NamedTuple

from faktur import betraege
from faktur.gui.qt import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

#: Feldarten, die es gibt.
ZEILE = "zeile"
BLOCK = "block"
HAKEN = "haken"
ZAHL = "zahl"
PAAR = "paar"


class Feld(NamedTuple):
    """Ein Feld auf dem Blatt.

    Attributes:
        schluessel: Womit das Feld in der Datenbank heißt.
        beschriftung: Was links daneben steht.
        art: ``zeile``, ``block``, ``haken``, ``zahl`` oder ``paar``.
            ``paar`` steht für ein schmales Feld, das sich den Platz mit
            dem nächsten Feld teilt — Postleitzahl und Ort etwa.
        pflicht: Ob ohne Inhalt nicht gespeichert wird.
        hinweis: Ein Satz darunter, zum Beispiel beim Preis.
    """

    schluessel: str
    beschriftung: str
    art: str = ZEILE
    pflicht: bool = False
    hinweis: str = ""


class Formular(QDialog):
    """Ein Blatt mit Feldern.

    Attributes:
        db: Die Datenbankverbindung.
        felder: Die Felder dieses Blattes.
        daten: Die Werte, wie sie in der Datenbank heißen.
    """

    def __init__(
        self,
        db: sqlite3.Connection,
        titel: str,
        felder: tuple[Feld, ...],
        daten: dict[str, str] | None = None,
        eltern: object = None,
        knopf: str = "Speichern",
    ) -> None:
        """Baut das Blatt auf.

        Args:
            db: Die Datenbankverbindung.
            titel: Der Titel in der Titelleiste.
            felder: Die Felder in der Reihenfolge, in der sie stehen.
            daten: Die vorhandenen Werte. Ohne Angabe ist das Blatt leer.
            eltern: Das Fenster, zu dem das Blatt gehört.
            knopf: Was auf der Haupt taste steht.
        """
        super().__init__(eltern)  # type: ignore[arg-type]
        self.db = db
        self.felder = felder
        self.setWindowTitle(titel)
        self.setModal(True)
        self.resize(520, 540)

        self.daten = dict(daten or {})
        self._eingaben: dict[str, object] = {}

        inhalt = self._blatt()
        kasten = QScrollArea()
        kasten.setWidgetResizable(True)
        kasten.setWidget(inhalt)
        kasten.setFrameShape(QScrollArea.Shape.NoFrame)

        knoepfe = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        knoepfe.button(QDialogButtonBox.StandardButton.Save).setText(knopf)
        knoepfe.button(QDialogButtonBox.StandardButton.Cancel).setText("Abbrechen")
        knoepfe.accepted.connect(self._gueltig)
        knoepfe.rejected.connect(self.reject)

        anordnung = QVBoxLayout(self)
        anordnung.setContentsMargins(16, 16, 16, 16)
        anordnung.setSpacing(12)
        anordnung.addWidget(kasten, 1)
        anordnung.addWidget(knoepfe)

        self._erstes()

    # ------------------------------------------------------------- aufbau

    def _blatt(self) -> QWidget:
        """Baut die Felder untereinander.

        Returns:
            Das Widget mit allen Feldern.
        """
        blatt = QWidget()
        anordnung = QVBoxLayout(blatt)
        anordnung.setContentsMargins(4, 4, 12, 4)
        anordnung.setSpacing(14)

        for gruppe in self._gruppen():
            if len(gruppe) == 1:
                anordnung.addLayout(self._reihe(gruppe[0]))
            else:
                anordnung.addLayout(self._zweispaltig(*gruppe))

        anordnung.addStretch(1)
        return blatt

    def _gruppen(self) -> list[tuple[Feld, ...]]:
        """Fasst die Felder zu Zeilen zusammen.

        **Zwei schmale Felder hintereinander gehören in eine Zeile** — Postleitzahl
        und Ort etwa. Zwei schmale Felder mit einem breiten dazwischen
        nicht: dann stünde die Postleitzahl neben dem Notizfeld.

        Args:
            Keine.

        Returns:
            Die Zeilen, jede mit einem oder zwei Feldern.
        """
        gruppen: list[tuple[Feld, ...]] = []
        wartende: list[Feld] = []

        for feld in self.felder:
            if feld.art != PAAR:
                if wartende:
                    gruppen.append((wartende.pop(0),))
                    wartende.clear()
                gruppen.append((feld,))
                continue
            wartende.append(feld)
            if len(wartende) == 2:
                gruppen.append((wartende[0], wartende[1]))
                wartende.clear()

        for feld in wartende:
            gruppen.append((feld,))

        return gruppen

    def _zweispaltig(self, links: Feld, rechts: Feld | None = None) -> object:
        """Baut eine Zeile aus zwei schmalen Feldern.

        Args:
            links: Das Feld links.
            rechts: Das Feld rechts.

        Returns:
            Das Layout der Zeile.
        """
        from faktur.gui.qt import QHBoxLayout

        anordnung = QHBoxLayout()
        anordnung.setSpacing(12)
        for nummer, feld in enumerate((links, rechts)):
            if feld is None:
                continue
            beschriftung = QLabel(f"{feld.beschriftung} *")
            feld_wert = QLineEdit(self._wert(feld))
            self._eingaben[feld.schluessel] = feld_wert
            spalte = QVBoxLayout()
            spalte.setSpacing(2)
            spalte.addWidget(beschriftung)
            spalte.addWidget(feld_wert)
            if nummer == 0:
                anordnung.addLayout(spalte, 1)
            else:
                anordnung.addLayout(spalte, 2)
        return anordnung

    def _reihe(self, feld: Feld) -> object:
        """Baut eine Feldzeile mit Beschriftung.

        Args:
            feld: Das Feld.

        Returns:
            Das Layout der Zeile.
        """
        from faktur.gui.qt import QHBoxLayout

        beschriftung = QLabel(feld.beschriftung)
        beschriftung.setMinimumWidth(140)
        if feld.pflicht:
            beschriftung.setText(f"{feld.beschriftung} *")

        if feld.art == HAKEN:
            anordnung = QHBoxLayout()
            anordnung.addWidget(beschriftung)
            kasten = QCheckBox()
            kasten.setChecked(self._wert(feld) not in ("", "0", "nein", "false"))
            self._eingaben[feld.schluessel] = kasten
            anordnung.addWidget(kasten)
            anordnung.addStretch(1)
            return anordnung

        if feld.art == BLOCK:
            anordnung = QHBoxLayout()
            anordnung.addWidget(beschriftung)
            feld_wert = QTextEdit()
            feld_wert.setPlainText(self._wert(feld))
            feld_wert.setFixedHeight(90)
            self._eingaben[feld.schluessel] = feld_wert
            anordnung.addWidget(feld_wert, 1)
            return anordnung

        if feld.art == ZAHL:
            anordnung = QFormLayout()
            anordnung.setLabelAlignment(_rechts())
            anordnung.setFieldGrowthPolicy(
                QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow
            )
            feld_wert = QLineEdit(self._wert(feld))
            if feld.hinweis:
                feld_wert.setPlaceholderText(feld.hinweis)
            self._eingaben[feld.schluessel] = feld_wert
            anordnung.addRow(beschriftung, feld_wert)
            return anordnung

        anordnung = QFormLayout()
        anordnung.setLabelAlignment(_rechts())
        anordnung.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow
        )
        feld_wert = QLineEdit(self._wert(feld))
        self._eingaben[feld.schluessel] = feld_wert
        anordnung.addRow(beschriftung, feld_wert)
        return anordnung

    def _wert(self, feld: Feld) -> str:
        """Holt den vorhandenen Wert eines Feldes.

        Args:
            feld: Das Feld.

        Returns:
            Der Wert als Text, oder ``""``.
        """
        return str(self.daten.get(feld.schluessel, "") or "")

    def _erstes(self) -> None:
        """Setzt den Fokus auf das erste Pflichtfeld.

        Returns:
            Nichts.
        """
        for feld in self.felder:
            if not feld.pflicht:
                continue
            widget = self._eingaben.get(feld.schluessel)
            if widget is not None and hasattr(widget, "setFocus"):
                widget.setFocus()
                widget.selectAll()
            return

    # -------------------------------------------------------------- inhalt

    def werte(self) -> dict[str, str]:
        """Liest alle Felder aus.

        Returns:
            Die Werte, wie sie in der Datenbank heißen. Ein leeres Feld
            kommt als ``""`` zurück, nicht als ``None`` — sonst schriebe
            ein leeres Textfeld den Platzhalter eines anderen.
        """
        ergebnis: dict[str, str] = {}

        for feld in self.felder:
            widget = self._eingaben.get(feld.schluessel)
            if widget is None:
                continue
            if feld.art == HAKEN:
                ergebnis[feld.schluessel] = "1" if _ist_an(widget, "isChecked") else "0"
            elif feld.art == BLOCK:
                ergebnis[feld.schluessel] = _ruft(widget, "toPlainText").strip()
            else:
                ergebnis[feld.schluessel] = _ruft(widget, "text").strip()

        return ergebnis

    # ------------------------------------------------------------ aktionen

    def _gueltig(self) -> None:
        """Prüft die Pflichtfelder und schließt das Blatt.

        Returns:
            Nichts.
        """
        werte = self.werte()

        for feld in self.felder:
            if feld.pflicht and not werte.get(feld.schluessel, ""):
                QMessageBox.warning(
                    self,
                    feld.beschriftung,
                    f"„{feld.beschriftung}“ darf nicht leer bleiben.",
                )
                widget = self._eingaben.get(feld.schluessel)
                if widget is not None:
                    widget.setFocus()
                return

        for feld in self.felder:
            if feld.art != ZAHL:
                continue
            text = werte.get(feld.schluessel, "")
            if not text:
                continue
            zahl = betraege.zahl(text)
            if zahl < 0:
                QMessageBox.warning(
                    self,
                    feld.beschriftung,
                    f"„{feld.beschriftung}“ kann nicht negativ sein.",
                )
                self._eingaben[feld.schluessel].setFocus()  # type: ignore[union-attr]
                return
            werte[feld.schluessel] = f"{zahl:.2f}"

        self.daten = werte
        self.accept()


def _ruft(widget: object, methode: str) -> str:
    """Ruft eine Textmethode eines Feldes auf.

    Args:
        widget: Das Feld, ein ``QLineEdit`` oder ein ``QTextEdit``.
        methode: ``text`` oder ``toPlainText``.

    Returns:
        Der Text des Feldes.
    """
    return str(getattr(widget, methode)())


def _ist_an(widget: object, methode: str) -> bool:
    """Fragt ein Feld, ob es angehakt ist.

    Args:
        widget: Das Feld, ein ``QCheckBox``.
        methode: ``isChecked``.

    Returns:
        ``True``, wenn der Haken sitzt.
    """
    return bool(getattr(widget, methode)())


def _rechts() -> object:
    """Gibt die Ausrichtung zurück, mit der Beschriftungen stehen.

    Returns:
        Die Ausrichtung.
    """
    from faktur.gui.qt import Qt

    return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter


__all__ = [
    "BLOCK",
    "HAKEN",
    "ZEILE",
    "PAAR",
    "ZAHL",
    "Feld",
    "Formular",
]
