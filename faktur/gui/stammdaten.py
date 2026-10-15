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
    QAbstractItemView,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    Qt,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from faktur.gui.seite import Seite

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

#: Was die Platzhalter bedeuten, fuer den Hinweis beim Darueberfahren.
_BEDEUTUNG = {
    "Kunde": "die Firma",
    "Kunde_Anrede": "die Anrede mit Namen, z. B. „Herr Mustermann“",
    "Ansprechpartner": "die Person in der Firma",
    "Nummer": "die Projektnummer",
    "Datum": "das Datum des Dokuments",
    "Faellig": "das Fälligkeitsdatum",
    "Gueltig_bis": "das Ablaufdatum eines Angebots",
    "Betrag": "die Summe, z. B. „3.290,00 €“",
    "Anzahl_Positionen": "die Zahl der Positionen",
    "EigeneFirma": "der Name der New Air Media Group",
    "EigeneFirma_voll": "der Name mit Zusatz",
    "Bank": "die Bank",
    "IBAN": "die IBAN",
}


def beschreibung_fuer(name: str, beispiel: str) -> str:
    """Baut den Hinweis fuer einen Platzhalter.

    Args:
        name: Der Name des Platzhalters, ohne Klammern.
        beispiel: Das, was im Beispiel eingesetzt wird.

    Returns:
        Der Text fuer den Tooltip.
    """
    was = _BEDEUTUNG.get(name, "siehe Anleitung")
    return f"{{{{{name}}}}} — {was}, im Beispiel „{beispiel}“"


class _Merker:
    """Weiss, in welchem Textfeld zuletzt getippt wurde.

    Attributes:
        feld: Das Textfeld, das zuletzt den Fokus hatte.
    """

    def __init__(self) -> None:
        """Legt den Merker an."""
        self.feld: object | None = None


class BriefFeld(QTextEdit):
    """Ein Textfeld, das sich meldet, wenn es in den Vordergrund kommt.

    Ohne das wüsste die Seite nicht, wohin ein Platzhalter gehört: Der
    Nutzer klickt in den Angebotstext, dann auf die Tabelle, und dann ist
    das Feld nicht mehr im Fokus — sein Cursor steht aber noch richtig.

    Attributes:
        merker: Wohin gemeldet wird.
    """

    def __init__(self, text: str = "") -> None:
        """Legt das Feld an.

        Args:
            text: Der Anfangstext.
        """
        super().__init__()
        self.setPlainText(text)
        self.merker: object | None = None

    def focusInEvent(self, ereignis: object) -> None:  # noqa: N802
        """Merkt sich, dass dieses Feld drank ist.

        Args:
            ereignis: Das Ereignis von Qt.

        Returns:
            Nichts.
        """
        if self.merker is not None:
            self.merker.feld = self  # type: ignore[attr-defined]
        super().focusInEvent(ereignis)  # type: ignore[arg-type]


class StammdatenSeite(Seite):
    """Die Seite mit Firma, Bank, Brieftexten und Aussehen.

    **Eine Seite, kein Blatt.** Bis 0.10 lag sie hinter *Einstellungen…*
    im Menü, und auf dem Mac war sie dort nicht zu finden: Qt schiebt
    einen Punkt mit der Rolle *Einstellungen* ins Programm-Menü, und das
    hieß noch *Python*, weil es kein Bündel gab. Man musste also etwas
    eingeben können und konnte es nicht — und das fiel erst auf, als
    jemand es benutzen wollte.

    Darum steht sie jetzt in der Seitenleiste, wo sie immer war. Der
    Menüpunkt bleibt, weil er auf dem Mac hingehört — er ist nur nicht
    mehr der einzige Weg.

    Attributes:
        db: Die Datenbankverbindung.
        felder: Die Eingabefelder, je Schlüssel.
        bausteine: Die Textfelder der Briefe, je Schlüssel.
    """

    def __init__(self, db: sqlite3.Connection) -> None:
        """Baut die Seite auf.

        Args:
            db: Die Datenbankverbindung.
        """
        super().__init__(db, "Stammdaten")
        self.ohne_suche()

        self.felder: dict[str, QLineEdit] = {}
        self.bausteine: dict[str, BriefFeld] = {}
        self._zuletzt = _Merker()

        self.reiter = QTabWidget()
        self.reiter.addTab(_in_rahmen(self._reiter_firma()), "Firma")
        self.reiter.addTab(_in_rahmen(self._reiter_bank()), "Bank")
        self.reiter.addTab(_in_rahmen(self._reiter_briefe()), "Brieftexte")
        self.reiter.addTab(_in_rahmen(self._reiter_aussehen()), "Aussehen")

        speichern = QPushButton("Speichern")
        speichern.setObjectName("haupt")
        speichern.clicked.connect(self.speichern)

        leiste = QHBoxLayout()
        leiste.addStretch(1)
        leiste.addWidget(speichern)

        self._koerper.addWidget(self.reiter, 1)
        self._koerper.addLayout(leiste)

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
        anordnung.setSpacing(8)

        for schluessel, beschriftung in _BRIEFTE:
            anordnung.addWidget(QLabel(f"<b>{beschriftung}</b>"))
            feld = BriefFeld(einstellungen.baustein(self.db, schluessel))
            feld.setObjectName("baustein")
            feld.merker = self._zuletzt
            self.bausteine[schluessel] = feld
            anordnung.addWidget(feld, 1)

        anordnung.addWidget(self._platzhalter())
        return kasten

    def _platzhalter(self) -> QWidget:
        """Baut die Liste der Platzhalter auf.

        **Als Tabelle mit den Klammern, wie sie in den Text gehören.**
        Vorher stand dort ein Fließtext aus Namen ohne Klammern, grau und
        klein. Man musste raten, wie man einen davon schreibt, und auf dem
        Mac ist „{{Kunde}}" nicht dasselbe wie „{ Kunde }".

        Doppelklick auf eine Zeile setzt sie an die Schreibmarke des
        Textfeldes, in dem man zuletzt war.

        Returns:
            Das Widget.
        """
        beschriftung = QLabel("Doppelklick setzt den Platzhalter an die Schreibmarke.")
        beschriftung.setObjectName("zweit")

        tabelle = QTableWidget(len(einstellungen.PLATZHALTER), 2)
        tabelle.setObjectName("tabelle")
        tabelle.setHorizontalHeaderLabels(["Platzhalter", "wird zu"])
        tabelle.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        tabelle.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        tabelle.setAlternatingRowColors(True)
        tabelle.verticalHeader().setVisible(False)
        tabelle.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        tabelle.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )

        for nummer, (name, beispiel) in enumerate(
            sorted(einstellungen.PLATZHALTER.items())
        ):
            feld = QTableWidgetItem(f"{{{{{name}}}}}")
            feld.setData(Qt.ItemDataRole.UserRole, name)
            feld.setToolTip(beschreibung_fuer(name, beispiel))
            tabelle.setItem(nummer, 0, feld)
            tabelle.setItem(nummer, 1, QTableWidgetItem(beispiel))

        tabelle.cellDoubleClicked.connect(self._platzhalter_eingesetzt)

        huelle = QWidget()
        anordnung = QVBoxLayout(huelle)
        anordnung.setContentsMargins(0, 0, 0, 0)
        anordnung.setSpacing(6)
        anordnung.addWidget(beschriftung)
        anordnung.addWidget(tabelle)
        self.platzhalter = tabelle
        return huelle

    def _platzhalter_eingesetzt(self, zeile: int, spalte: int) -> None:
        """Setzt einen Platzhalter an die Schreibmarke.

        Args:
            zeile: Die Zeile in der Tabelle.
            spalte: Die Spalte. Wird ignoriert, weil beide gleich sind.

        Returns:
            Nichts.
        """
        del spalte
        eintrag = self.platzhalter.item(zeile, 0)
        if eintrag is None:
            return
        self._einsetzen(str(eintrag.text()))

    def _einsetzen(self, platzhalter: str) -> None:
        """Schreibt einen Platzhalter in das zuletzt benutzte Textfeld.

        Args:
            platzhalter: Der Platzhalter mit Klammern.

        Returns:
            Nichts.
        """
        feld = self._zuletzt.feld
        if feld is None:
            self.melde("Erst in einen Brieftext klicken.")
            return
        feld.insertPlainText(platzhalter)
        feld.setFocus()

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

    def speichern(self) -> bool:
        """Schreibt alle Felder in die Datenbank.

        Returns:
            ``True``, wenn gespeichert wurde.
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

        self.erneut_laden()
        self.melde("Stammdaten gespeichert.")
        return True

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


__all__ = ["BriefFeld", "StammdatenSeite"]
