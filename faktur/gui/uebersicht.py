"""Die Übersicht: die erste Seite, die man sieht.

**Sie sagt zuerst das, was fehlt.** Ein frisches Programm kennt weder
Firmenname noch IBAN, und die PDF kommen trotzdem heraus — ohne Absender,
ohne Bankverbindung, ohne Steuernummer. Man merkt es auf dem Papier, wenn
die Rechnung schon weg ist.

:func:`faktur.einstellungen.vollstaendig` kann das seit dem Anfang
feststellen, und bis hierher hat es niemand gefragt. Diese Seite fragt
jetzt.

Die Zahlen der Seite — was abgerechnet wurde, was offen ist, was je Monat
kam — kommen in einem späteren Schritt. Sie stehen hier noch nicht, und
das ist Absicht: Die Seite trägt jetzt nur das, was beim ersten Öffnen
fehlt, und sonst nichts, was nach leerem Rahmen aussieht.
"""

from __future__ import annotations

import sqlite3

from faktur import einstellungen
from faktur.gui.qt import QFrame, QHBoxLayout, QLabel, QPushButton, Qt, QVBoxLayout
from faktur.gui.seite import Seite


class UebersichtSeite(Seite):
    """Die erste Seite des Fensters.

    Attributes:
        db: Die Datenbankverbindung.
    """

    def __init__(self, db: sqlite3.Connection) -> None:
        """Baut die Seite auf.

        Args:
            db: Die Datenbankverbindung.
        """
        super().__init__(db, "Übersicht")
        self.ohne_suche()

        self.hinweis = self._hinweis()
        self._koerper.addWidget(self.hinweis)
        self._koerper.addStretch(1)

    def _hinweis(self) -> QFrame:
        """Baut den Kasten, der auf fehlende Stammdaten aufmerksam macht.

        Returns:
            Der Kasten. Unsichtbar, solange nichts fehlt.
        """
        kasten = QFrame()
        kasten.setObjectName("hinweis")

        text = QLabel(
            "<b>Die Stammdaten sind noch unvollständig.</b><br>"
            "Ohne Firmenname und IBAN kommen die PDF ohne Absender und ohne "
            "Bankverbindung heraus."
        )
        text.setWordWrap(True)

        knopf = QPushButton("Stammdaten ausfüllen")
        knopf.setObjectName("haupt")
        knopf.clicked.connect(self._stammdaten_geoeffnet)

        # Text und Taste in **einer** Zeile, ohne den Leerraum dazwischen.
        # Mit Leerraum steht die Taste am rechten Rand der Seite und der
        # Satz liest sich als zwei getrennte Dinge.
        leiste = QHBoxLayout()
        leiste.setSpacing(16)
        leiste.addWidget(text, 1)
        leiste.addWidget(knopf, 0, Qt.AlignmentFlag.AlignTop)

        anordnung = QVBoxLayout(kasten)
        anordnung.setContentsMargins(18, 16, 18, 16)
        anordnung.setSpacing(0)
        anordnung.addLayout(leiste)

        return kasten

    def _stammdaten_geoeffnet(self) -> None:
        """Springt zu den Stammdaten.

        Returns:
            Nichts.
        """
        fenster = self.hauptfenster()
        if fenster is not None:
            fenster.gehe("stammdaten")  # type: ignore[attr-defined]

    def lade(self) -> None:
        """Prüft, ob die Stammdaten vollständig sind.

        Returns:
            Nichts.
        """
        self.hinweis.setVisible(not einstellungen.vollstaendig(self.db))


__all__ = ["UebersichtSeite"]
