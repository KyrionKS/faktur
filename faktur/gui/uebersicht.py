"""Die Übersicht: die erste Seite, die man sieht.

**Drei Zahlen und zwölf Monate.** Beim Öffnen will man wissen, was offen
ist, was dieses Jahr hereingekommen ist und was angeboten, aber noch nicht
in Rechnung gestellt wurde — und nicht erst in drei Bereichen suchen
müssen, um es zu finden.

**Jede Zahl geht irgendwohin.** *Offen* führt zu den offenen Forderungen,
*Angebote* zu den Projekten, *dieses Jahr* zu den Dokumenten. Eine Zahl,
die man nur ablesen kann, ist ein Bildschirmmuster; eine, hinter der
etwas liegt, ist eine Tür.

**Die Monatssumme ist die Rechnungssumme, nicht die Zahlung.** Gefragt ist,
was in einem Monat in Rechnung gestellt wurde. Wer wissen will, was
wirklich hereingekommen ist, findet das bei den offenen Forderungen —
dort steht jede Rechnung mit ihrem Zahlungsdatum.

**Sie sagt zuerst das, was fehlt.** Ein frisches Programm kennt weder
Firmenname noch IBAN, und die PDF kommen trotzdem heraus — ohne Absender,
ohne Bankverbindung, ohne Steuernummer. Man merkt es auf dem Papier, wenn
die Rechnung schon weg ist. :func:`faktur.einstellungen.vollstaendig` kann
das seit dem Anfang feststellen, und bis hierher hat es niemand gefragt.
Diese Seite fragt jetzt.
"""

from __future__ import annotations

import sqlite3

from faktur import betraege, dateien, einstellungen, offen
from faktur.gui.qt import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    Qt,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from faktur.gui.seite import Seite

#: Wie viele Monate die Übersicht zeigt.
MONATE = 12


class UebersichtSeite(Seite):
    """Die erste Seite des Fensters.

    Attributes:
        db: Die Datenbankverbindung.
        hinweis: Der Kasten über den fehlenden Stammdaten.
        monate: Die Tabelle mit den Monatssummen.
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

        self.kacheln = self._zahlen()
        self._koerper.addWidget(self.kacheln)

        self.monate = self._monatstabelle()
        self._koerper.addWidget(self.monate, 1)

    # ------------------------------------------------------------ die Zahlen

    def _zahlen(self) -> QWidget:
        """Baut die drei Kästen mit den Zahlen.

        **Drei, nicht mehr.** Jeder weitere ist ein vierter Grund, die
        Seite zu überlesen. Welche drei es sind, entscheidet die Frage
        *was muss ich heute wissen* — und nicht, was sich leicht aus der
        Datenbank holen lässt.

        *Überfällig* ist keine eigene Kachel, sondern der kleine Satz unter
        *Offen*: Es ist eine Teilmenge, und für sich genommen wäre es eine
        zweite Zahl, die dieselbe Sache in kleiner erzählt.

        Returns:
            Das Widget mit den drei Kästen.
        """
        gross: dict[str, QLabel] = {}
        klein: dict[str, QLabel] = {}

        huelle = QWidget()
        anordnung = QHBoxLayout(huelle)
        anordnung.setContentsMargins(0, 6, 0, 6)
        anordnung.setSpacing(12)

        gross["offen"], klein["offen"] = self._kachel(
            anordnung, "Offen", "Zu den Forderungen", "offen"
        )
        gross["jahr"], klein["jahr"] = self._kachel(
            anordnung, "Dieses Jahr", "Zu den Dokumenten", "dokumente"
        )
        gross["angebote"], klein["angebote"] = self._kachel(
            anordnung, "Angeboten, offen", "Zu den Projekten", "projekte"
        )
        anordnung.addStretch(1)

        self._gross = gross
        self._klein = klein
        return huelle

    def _kachel(
        self, reihe: QHBoxLayout, titel: str, tastentext: str, ziel: str
    ) -> tuple[QLabel, QLabel]:
        """Baut einen Kasten mit einer Zahl und einer Taste.

        Args:
            reihe: Das Raster, in das der Kasten kommt.
            titel: Was die Zahl bedeutet.
            tastentext: Was auf der Taste steht.
            ziel: Der Bereich der Seitenleiste, zu dem die Taste führt.

        Returns:
            Die grosse Zahl und der kleine Satz darunter.
        """
        kasten = QFrame()
        kasten.setObjectName("kachel")

        beschriftung = QLabel(f"<b>{titel}</b>")
        beschriftung.setObjectName("zweit")

        gross = QLabel("—")
        gross.setObjectName("zahl")
        gross.setMinimumWidth(150)

        klein = QLabel(" ")
        klein.setObjectName("zweit")

        taste = QPushButton(tastentext)
        # **Der Zielbereich steht im Namen.** Ueber den Text zu raten ist
        # eine zweite Wahrheit: Aendert jemand die Aufschrift, sucht der
        # Test plötzlich eine Taste, die es nicht mehr gibt, und faellt
        # ohne Grund um.
        taste.setObjectName(f"kachel_{ziel}")
        taste.clicked.connect(lambda: self._springe(ziel))

        innen = QVBoxLayout(kasten)
        innen.setContentsMargins(16, 12, 16, 12)
        innen.setSpacing(2)
        innen.addWidget(beschriftung)
        innen.addWidget(gross)
        innen.addWidget(klein)
        innen.addSpacing(6)
        innen.addWidget(taste)

        # **Gleich breit.** Ohne die Breitenangabe richtet sich jeder Kasten
        # nach seinem Text, und die Zahl steht in einer anderen Höhe als
        # ihre Nachbarn — drei Zahlen, die man nicht auf einer Linie
        # vergleichen kann.
        reihe.addWidget(kasten, 1)
        return gross, klein

    # ---------------------------------------------------------- die Monate

    def _monatstabelle(self) -> QWidget:
        """Baut die Tabelle mit den Monatssummen.

        Returns:
            Das Widget mit der Tabelle.
        """
        beschriftung = QLabel("<b>Rechnungen je Monat</b> — nach dem Rechnungsdatum")
        beschriftung.setWordWrap(True)

        tabelle = QTableWidget(0, 3)
        tabelle.setObjectName("tabelle")
        tabelle.setHorizontalHeaderLabels(["Monat", "Anzahl", "Summe"])
        tabelle.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        tabelle.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        tabelle.setAlternatingRowColors(True)
        tabelle.verticalHeader().setVisible(False)
        tabelle.horizontalHeader().setHighlightSections(False)
        # **Keine Spalte auf Fuellbreite.** Die Summe waere sonst so weit
        # vom Monat entfernt, dass man beim Lesen die Zeile verliert.
        # Lieber eine kurze Tabelle mit weissem Rand daneben.
        tabelle.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self._monats_tabelle = tabelle

        huelle = QWidget()
        anordnung = QVBoxLayout(huelle)
        anordnung.setContentsMargins(0, 10, 0, 0)
        anordnung.setSpacing(8)
        anordnung.addWidget(beschriftung)
        anordnung.addWidget(tabelle)
        return huelle

    # ------------------------------------------------------------- die Daten

    def lade(self) -> None:
        """Holt alle Zahlen neu.

        Returns:
            Nichts.
        """
        self.hinweis.setVisible(not einstellungen.vollstaendig(self.db))
        self._zahlen_fuellen()
        self._monate_fuellen()

    def _zahlen_fuellen(self) -> None:
        """Trägt die drei Zahlen ein.

        Returns:
            Nichts.
        """
        heute = betraege.heute()

        for_due = offen.offene(self.db)
        dringend = [d for d in for_due if offen.ist_faellig(d, heute)]
        self._gross["offen"].setText(betraege.euro(offen.summe_offen(self.db)))
        self._klein["offen"].setText(_mit_frist(for_due, dringend))

        anzahl, summe = dateien.jahreszahlen(self.db)
        self._gross["jahr"].setText(betraege.euro(summe))
        self._klein["jahr"].setText(
            f"{_stueck(anzahl, 'Rechnung', 'Rechnungen')} in {betraege.jahr()}"
        )

        angeboten = dateien.offene_angebote(self.db)
        self._gross["angebote"].setText(
            betraege.euro(sum(dateien.projektsumme(p) for p in angeboten))
        )
        self._klein["angebote"].setText(
            f"{_stueck(len(angeboten), 'Angebot', 'Angebote')} ohne Rechnung"
        )

    def _monate_fuellen(self) -> None:
        """Trägt die Monatssummen ein.

        Returns:
            Nichts.
        """
        summen = dateien.monatssummen(self.db, MONATE)
        tabelle = self._monats_tabelle
        tabelle.setRowCount(len(summen))

        for zeile, eintrag in enumerate(summen):
            _zelle(tabelle, zeile, 0, eintrag.monat)
            _zelle(tabelle, zeile, 1, str(eintrag.anzahl))
            _zelle(tabelle, zeile, 2, betraege.euro(eintrag.summe))

        # **Leere Monate bleiben stehen.** Zwölf Zeilen sind zwölf Zeilen;
        # eine Lücke im Raster sähe nach Datenverlust aus. Wer sie nicht
        # sehen will, scannt an ihnen vorbei.
        tabelle.resizeRowsToContents()

    # ------------------------------------------------------------ die Klicks

    def _springe(self, ziel: str) -> None:
        """Springt in einen Bereich der Seitenleiste.

        Args:
            ziel: Der Bereich aus :data:`BEREICHE`.

        Returns:
            Nichts.
        """
        fenster = self.hauptfenster()
        if fenster is not None:
            fenster.gehe(ziel)  # type: ignore[attr-defined]

    def _stammdaten_geoeffnet(self) -> None:
        """Springt zu den Stammdaten.

        Returns:
            Nichts.
        """
        self._springe("stammdaten")

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


def _stueck(anzahl: int, einzahl: str, mehrzahl: str) -> str:
    """Sagt, wie viele Dinge es sind.

    Args:
        anzahl: Die Zahl.
        einzahl: Das Wort für eines.
        mehrzahl: Das Wort für mehrere.

    Returns:
        Etwa *1 Rechnung* oder *4 Rechnungen*.
    """
    return f"{anzahl} {einzahl if anzahl == 1 else mehrzahl}"


def _mit_frist(offen_: list[object], dringend: list[object]) -> str:
    """Beschreibt die offenen Forderungen in einem Satz.

    Args:
        offen_: Alle offenen Rechnungen.
        dringend: Die davon, deren Frist abgelaufen ist.

    Returns:
        Der Satz unter der Zahl.
    """
    if not offen_:
        return "Alles bezahlt"
    n = len(dringend)
    if n == 0:
        return f"{_stueck(len(offen_), 'Rechnung', 'Rechnungen')}, keine überfällig"
    # **„davon" statt ein zweites „Rechnung".** Zwei Wiederholungen von
    # *Rechnung* in einem sechs Wörter langen Satz klingen nach zwei
    # verschiedenen Rechnungen, die man vergleichen soll.
    return (
        f"{_stueck(len(offen_), 'Rechnung', 'Rechnungen')}, "
        f"{_stueck(n, 'davon überfällig', 'davon überfällig')}"
    )


def _zelle(tabelle: QTableWidget, zeile: int, spalte: int, text: str) -> None:
    """Schreibt eine Zelle.

    Args:
        tabelle: Die Tabelle.
        zeile: Die Zeile.
        spalte: Die Spalte.
        text: Der Text.

    Returns:
        Nichts.
    """
    eintrag = QTableWidgetItem(text)
    if spalte == 2:
        eintrag.setTextAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
    tabelle.setItem(zeile, spalte, eintrag)


__all__ = ["MONATE", "UebersichtSeite"]
