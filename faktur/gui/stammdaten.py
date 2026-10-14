"""Die Einstellungen.

Ein Blatt mit vier Reitern: **Firma**, **Bank**, **Brieftexte** und
**Aussehen**. Alles, was bisher über eine Liste von Feldern im Terminal
erledigt wurde, steht hier nebeneinander — und lässt sich in einem Zug
sehen, was schon da ist.

**Gespeichert wird in einem Zug.** Wer drei Felder ändert und dann auf
*Abbrechen* klickt, hat nichts verändert. Das ist der Unterschied zwischen
einem Blatt und einem Bildschirm, auf dem man Feld für Feld geht.
"""

from __future__ import annotations

import sqlite3

from faktur import einstellungen, gestaltung
from faktur.gui.qt import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

#: Die Felder der Firma. Schlüssel, Beschriftung, Zeile, Spalte.
_FIRMA: tuple[tuple[str, str, int, int], ...] = (
    ("firma", "Firmenname", 0, 1),
    ("zusatz", "Zusatz zur Firma", 1, 1),
    ("strasse", "Strasse", 0, 2),
    ("plz", "PLZ", 0, 3),
    ("ort", "Ort", 0, 4),
    ("telefon", "Telefon", 1, 3),
    ("email", "E-Mail", 1, 4),
    ("webseite", "Webseite", 2, 3),
)

#: Die Felder der Bank.
_BANK: tuple[tuple[str, str, int, int], ...] = (
    ("bank", "Bank", 0, 1),
    ("iban", "IBAN", 1, 1),
    ("bic", "BIC", 1, 2),
    ("steuernummer", "Steuernummer", 2, 1),
    ("inhaber", "Kontoinhaber", 2, 2),
)

#: Die Textbausteine, die man selbst schreiben kann.
_BRIEFTE: tuple[tuple[str, str], ...] = (
    ("text_angebot", "Beim Angebot"),
    ("text_rechnung", "Bei der Rechnung"),
)

#: Die Schriftgrößen, wie sie heißen statt wie sie gerechnet werden.
#:
#: In :data:`faktur.gestaltung.GRUESSEN` stehen die Faktoren 0.9 bis 1.1.
#: Wer einstellt, sieht aber Wörter, keine Faktoren.
_GROESSEN = {"klein": "Klein", "normal": "Normal", "gross": "Groß"}


class StammdatenDialog(QDialog):
    """Das Blatt mit den Einstellungen.

    Attributes:
        db: Die Datenbankverbindung.
        felder: Die Eingabefelder, je Schlüssel.
        bausteine: Die Textfelder der Briefe, je Schlüssel.
    """

    def __init__(self, db: sqlite3.Connection, eltern: QWidget | None = None) -> None:
        """Baut das Blatt auf.

        Args:
            db: Die Datenbankverbindung.
            eltern: Das Fenster, zu dem das Blatt gehört.
        """
        super().__init__(eltern)
        self.db = db
        self.setWindowTitle("Einstellungen")
        self.setModal(True)
        self.resize(720, 560)

        self.felder: dict[str, QLineEdit] = {}
        self.bausteine: dict[str, QTextEdit] = {}

        reiter = QTabWidget()
        reiter.addTab(_in_rahmen(self._reiter_firma()), "Firma")
        reiter.addTab(_in_rahmen(self._reiter_bank()), "Bank")
        reiter.addTab(_in_rahmen(self._reiter_briefe()), "Brieftexte")
        reiter.addTab(_in_rahmen(self._reiter_aussehen()), "Aussehen")

        knoepfe = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        knoepfe.button(QDialogButtonBox.StandardButton.Save).setText("Speichern")
        knoepfe.button(QDialogButtonBox.StandardButton.Cancel).setText("Abbrechen")
        knoepfe.accepted.connect(self._speichern)
        knoepfe.rejected.connect(self.reject)

        anordnung = QVBoxLayout(self)
        anordnung.setContentsMargins(16, 16, 16, 16)
        anordnung.setSpacing(12)
        anordnung.addWidget(reiter, 1)
        anordnung.addWidget(knoepfe)

        self._fuellen()

    # ------------------------------------------------------------- reiter

    def _reiter_firma(self) -> QWidget:
        """Baut den Reiter *Firma*.

        Returns:
            Das Widget des Reiters.
        """
        return self._raster(_FIRMA, "Wie die PDF oben absender steht.")

    def _reiter_bank(self) -> QWidget:
        """Baut den Reiter *Bank*.

        Returns:
            Das Widget des Reiters.
        """
        return self._raster(_BANK, "Der Fuß jeder Rechnung.")

    def _raster(
        self, felder: tuple[tuple[str, str, int, int], ...], hinweis: str
    ) -> QWidget:
        """Baut ein Raster aus beschrifteten Feldern.

        Args:
            felder: Je Schlüssel, Beschriftung, Zeile und Spalte.
            hinweis: Der Satz unter dem Raster.

        Returns:
            Das Widget.
        """
        kasten = QGroupBox(hinweis)
        anordnung = QFormLayout(kasten)
        anordnung.setLabelAlignment(_rechts())
        anordnung.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow
        )

        for schluessel, beschriftung, _zeile, _spalte in felder:
            feld = QLineEdit(einstellungen.hole(self.db, schluessel))
            feld.setObjectName("einstellung")
            self.felder[schluessel] = feld
            anordnung.addRow(beschriftung, feld)

        return kasten

    def _reiter_briefe(self) -> QWidget:
        """Baut den Reiter *Brieftexte*.

        Returns:
            Das Widget des Reiters.
        """
        kasten = QGroupBox(
            "Was oben auf dem Dokument steht. Platzhalter in doppelten "
            "geschweiften Klammern werden ersetzt."
        )
        anordnung = QVBoxLayout(kasten)
        anordnung.setSpacing(10)

        for schluessel, beschriftung in _BRIEFTE:
            anordnung.addWidget(QLabel(f"<b>{beschriftung}</b>"))
            feld = QTextEdit(einstellungen.baustein(self.db, schluessel))
            feld.setObjectName("baustein")
            self.bausteine[schluessel] = feld
            anordnung.addWidget(feld, 1)

        anordnung.addWidget(self._platzhalter())
        return kasten

    def _platzhalter(self) -> QWidget:
        """Baut die Liste der Platzhalter auf.

        Returns:
            Das Widget.
        """
        beschriftung = QLabel(
            "Ersetzt werden: " + ", ".join(sorted(einstellungen.PLATZHALTER))
        )
        beschriftung.setObjectName("zweit")
        beschriftung.setWordWrap(True)
        huelle = QWidget()
        anordnung = QVBoxLayout(huelle)
        anordnung.setContentsMargins(0, 0, 0, 0)
        anordnung.addWidget(beschriftung)
        return huelle

    def _reiter_aussehen(self) -> QWidget:
        """Baut den Reiter *Aussehen*.

        Returns:
            Das Widget des Reiters.
        """
        kasten = QGroupBox("Wie die PDF aussehen.")
        anordnung = QFormLayout(kasten)
        anordnung.setLabelAlignment(_rechts())

        self.groesse = QComboBox()
        for schluessel, beschriftung in _GROESSEN.items():
            self.groesse.addItem(beschriftung, schluessel)
        gespeichert = einstellungen.hole(
            self.db, "groesse", gestaltung.STANDARD_GROESSE
        )
        self.groesse.setCurrentIndex(max(0, self.groesse.findData(gespeichert)))
        anordnung.addRow("Schriftgröße", self.groesse)

        self.logo = QLineEdit(einstellungen.hole(self.db, "logo"))
        self.logo.setObjectName("einstellung")
        anordnung.addRow("Logo", self.logo)

        wahler = QPushButton("Wählen …")
        wahler.clicked.connect(self._logo_gewahlt)
        anordnung.addRow("", wahler)

        return kasten

    # ------------------------------------------------------------- fuellen

    def _fuellen(self) -> None:
        """Füllt alle Felder aus der Datenbank.

        Returns:
            Nichts.
        """
        for schluessel, feld in self.felder.items():
            feld.setText(einstellungen.hole(self.db, schluessel))
        for schluessel, feld in self.bausteine.items():
            feld.setPlainText(einstellungen.baustein(self.db, schluessel))

    # ------------------------------------------------------------ aktionen

    def _logo_gewahlt(self) -> None:
        """Lässt eine Bilddatei auswählen.

        Returns:
            Nichts.
        """
        pfad, _ = QFileDialog.getOpenFileName(
            self,
            "Logo auswählen",
            str(einstellungen.logo_pfad(self.db) or ""),
            "Bilder (*.png *.jpg *.jpeg)",
        )
        if pfad:
            self.logo.setText(pfad)

    def _speichern(self) -> None:
        """Schreibt alle Felder in die Datenbank.

        Returns:
            Nichts.
        """
        for schluessel, feld in self.felder.items():
            einstellungen.speichere(self.db, schluessel, feld.text().strip())
        for schluessel, feld in self.bausteine.items():
            einstellungen.speichere(self.db, schluessel, feld.toPlainText())

        groesse = self.groesse.currentData()
        if groesse:
            einstellungen.speichere(self.db, "groesse", str(groesse))

        pfad = self.logo.text().strip()
        einstellungen.speichere(self.db, "logo", pfad)
        if pfad:
            self._logo_uebernehmen(pfad)

        self.accept()

    def _logo_uebernehmen(self, pfad: str) -> None:
        """Kopiert das gewählte Logo an seinen Platz.

        Das Ziel wird **ausdrücklich genannt**. Ohne diese Angabe nimmt
        :func:`faktur.einstellungen.logo_uebernehmen` den echten Datenordner
        des Benutzers — und das hat zweimal die echten Daten überschrieben,
        weil ein Test genau das aufrief.

        Args:
            pfad: Der Pfad zur gewählten Bilddatei.

        Returns:
            Nichts.
        """
        from pathlib import Path

        from faktur import orte

        try:
            einstellungen.logo_uebernehmen(
                self.db, Path(pfad), ziel_ordner=orte.datenordner()
            )
        except (OSError, FileNotFoundError) as fehler:
            QMessageBox.warning(
                self,
                "Logo",
                f"Das Logo konnte nicht kopiert werden:\n\n{fehler}",
            )


def _in_rahmen(inhalt: QWidget) -> QScrollArea:
    """Legt ein Feld in eine Bildlaufleiste.

    Ein Blatt, das nicht in die Fensterhöhe passt, braucht keinen Schieber
    nach unten und schon gar keinen, der die Knöpfe unten verdeckt. Der
    Rahmen schiebt nur die Seite, die Knöpfe bleiben stehen.

    Args:
        inhalt: Das Widget.

    Returns:
        Die Bildlaufleiste.
    """
    rahmen = QScrollArea()
    rahmen.setWidgetResizable(True)
    rahmen.setWidget(inhalt)
    rahmen.setFrameShape(QScrollArea.Shape.NoFrame)
    return rahmen


def _rechts() -> object:
    """Gibt die Ausrichtung zurück, mit der Beschriftungen stehen.

    Qt reicht sie als ``Qt.AlignmentFlag`` zurück; weiter oben wird sie
    mit ``|`` verknüpft, und genau das erwartet Qt auch.

    Returns:
        Die Ausrichtung.
    """
    from faktur.gui.qt import Qt

    return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter


__all__ = ["StammdatenDialog"]
