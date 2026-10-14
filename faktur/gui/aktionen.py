"""Was man mit einem Datensatz machen kann: anlegen, ändern, löschen, stilllegen.

Diese Aktionen stehen an zwei Stellen: als Taste oben auf der Seite und im
Menü. Damit sie nicht zweimal dastehen, liegen sie hier — die Seite und das
Menü rufen dieselben vier Methoden auf.

**Löschen fragt nach, und die Frage zählt mit.** :func:`faktur.dateien.kunde_loeschen`
nimmt einem Kunden die Dokumente mit, und damit die Rechnungen. Bei einem
Kunden ohne Belege ist die Frage überflüssig und nur lästig — bei einem mit
fünf ist sie das Wichtigste, was das Programm tut.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from faktur import dateien
from faktur.gui.formular import BLOCK, PAAR, ZAHL, Feld, Formular
from faktur.gui.qt import QCheckBox, QMessageBox

if TYPE_CHECKING:  # pragma: no cover
    from faktur.gui.seite import ListenSeite

#: Die Felder eines Kunden.
KUNDENFELDER: tuple[Feld, ...] = (
    Feld("firma", "Firmenname", pflicht=True),
    Feld("ansprechpartner", "Ansprechpartner"),
    Feld("strasse", "Strasse"),
    Feld("plz", "PLZ", PAAR),
    Feld("ort", "Ort", PAAR),
    Feld("email", "E-Mail"),
    Feld("telefon", "Telefon"),
    Feld("notiz", "Notiz", BLOCK),
)

#: Die Felder einer Leistung.
LEISTUNGFELDER: tuple[Feld, ...] = (
    Feld("bezeichnung", "Bezeichnung", pflicht=True),
    Feld("einheit", "Einheit", hinweis="Stunde"),
    Feld("preis", "Preis", ZAHL, hinweis="0,00"),
    Feld("beschreibung", "Beschreibung", BLOCK),
)


class Bearbeitbar:
    """Die vier Aktionen, die jede geschäftliche Liste kann.

    Attributes:
        seite: Die Seite, zu der die Aktionen gehören.
        felder: Die Felder des Formulars.
        einheit: Der Singular, wie er in den Fragen steht.
        mehrzahl: Der Plural davon.
    """

    def __init__(
        self,
        seite: ListenSeite,
        felder: tuple[Feld, ...],
        einheit: str,
        mehrzahl: str,
    ) -> None:
        """Hängt die Aktionen an die Seite.

        Args:
            seite: Die Seite.
            felder: Die Felder des Formulars.
            einheit: Der Singular, etwa *Kunde*.
            mehrzahl: Der Plural davon, etwa *Kunden*.
        """
        self.seite = seite
        self.felder = felder
        self.einheit = einheit
        self.mehrzahl = mehrzahl

        seite.knopf("Neu", self.neu, "⌘N", spitz=True)
        seite.knopf("Ändern", self.aendern, "⌘E")
        seite.knopf("Löschen", self.loeschen, "⌫")
        seite.knopf("Stilllegen", self.stilllegen)

    # ------------------------------------------------------------------ neu

    def neu(self) -> None:
        """Öffnet ein leeres Blatt und speichert, was eingegeben wurde.

        Returns:
            Nichts.
        """
        blatt = Formular(
            self.seite.db,
            f"Neuer {self.einheit}",
            self.felder,
            {},
            self.seite,
        )
        if blatt.exec() != Formular.DialogCode.Accepted:
            return
        self.seite.speichere_neu(blatt.werte())
        self.seite.melde(f"{self.einheit} angelegt.")
        self.seite.erneut_laden()

    # -------------------------------------------------------------- ändern

    def aendern(self) -> bool:
        """Öffnet das Blatt mit dem gewählten Datensatz.

        Returns:
            ``True``, wenn etwas gespeichert wurde.
        """
        datensatz = self.seite.gewaehlt()
        if datensatz is None:
            self.seite.melde("Erst einen Eintrag markieren.")
            return False

        blatt = Formular(
            self.seite.db,
            f"{self.einheit} ändern",
            self.felder,
            self.seite.als_daten(datensatz),
            self.seite,
        )
        if blatt.exec() != Formular.DialogCode.Accepted:
            return False
        self.seite.speichere_alt(self.seite.kennung(datensatz), blatt.werte())
        self.seite.melde(f"{self.einheit} geändert.")
        self.seite.erneut_laden()
        return True

    # -------------------------------------------------------------- löschen

    def loeschen(self) -> bool:
        """Löscht den gewählten Datensatz — nach einer Rückfrage.

        Returns:
            ``True``, wenn gelöscht wurde.
        """
        datensatz = self.seite.gewaehlt()
        if datensatz is None:
            self.seite.melde("Erst einen Eintrag markieren.")
            return False

        warnung = self.frage(datensatz)
        if warnung is None:
            return False

        antwort = QMessageBox.question(
            self.seite,
            f"{self.einheit} löschen",
            warnung,
            QMessageBox.StandardButton.Cancel | QMessageBox.StandardButton.Yes,
            QMessageBox.StandardButton.Cancel,
        )
        if antwort != QMessageBox.StandardButton.Yes:
            return False

        self.seite.loesche(self.seite.kennung(datensatz))
        self.seite.melde(f"{self.einheit} gelöscht.")
        self.seite.erneut_laden()
        return True

    # ---------------------------------------------------------- stilllegen

    def stilllegen(self) -> bool:
        """Legt den gewählten Datensatz still oder holt ihn zurück.

        Returns:
            ``True``, wenn etwas geändert wurde.
        """
        datensatz = self.seite.gewaehlt()
        if datensatz is None:
            self.seite.melde("Erst einen Eintrag markieren.")
            return False

        war_aktiv = bool(datensatz["aktiv"])
        self.seite.stilllege(self.seite.kennung(datensatz), not war_aktiv)
        self.seite.melde(
            f"{self.einheit} wieder in der Liste."
            if war_aktiv
            else f"{self.einheit} stillgelegt."
        )
        self.seite.erneut_laden()
        return True

    # --------------------------------------------------------------- fragen

    def frage(self, daten: dict[str, str]) -> str | None:
        """Baut den Text, vor dem man nicht löschen sollte.

        Unterklassen überschreiben das.

        Args:
            daten: Die Werte des gewählten Datensatzes.

        Returns:
            Der Text der Frage, oder ``None``, wenn nicht gelöscht werden
            soll — etwa weil der Datensatz schon stillgelegt ist und
            nichts daran hängt.
        """
        name = self.seite.name(daten)
        return f"„{name}“ wirklich löschen? Das lässt sich nicht zurücknehmen."


class KundenAktionen(Bearbeitbar):
    """Die Aktionen auf der Kundenliste."""

    def frage(self, datensatz: object) -> str | None:
        """Warnt zusätzlich, wenn Dokumente daran hängen.

        Args:
            datensatz: Der gewählte Kunde aus der Datenbank.

        Returns:
            Der Text der Frage.
        """
        anzahl = dateien.kundenzahl(self.seite.db, self.seite.kennung(datensatz))
        name = self.seite.als_daten(datensatz).get("firma", "")

        if anzahl == 0:
            return f"„{name}“ löschen? Der Kunde hat keine Dokumente."

        return (
            f"„{name}“ hat {anzahl} Dokumente.\n\n"
            "Die gehen mit verloren, samt den PDF im Ausgangsordner.\n"
            "Wenn der Kunde nur nicht mehr gebraucht wird, ist "
            "**Stilllegen** die bessere Wahl."
        )


def kunden_haken(seite: ListenSeite) -> QCheckBox:
    """Setzt den Haken „auch stillgelegte“ unter die Liste.

    Args:
        seite: Die Kundenliste.

    Returns:
        Der Haken.
    """
    return _archiv_haken(seite, "auch stillgelegte")


def _archiv_haken(seite: ListenSeite, text: str) -> QCheckBox:
    """Baut den Haken, der die stillgelegten Datensätze hereinholt.

    Args:
        seite: Die Liste.
        text: Was auf dem Haken steht.

    Returns:
        Der Haken.
    """
    haken = QCheckBox(text)
    haken.setObjectName("zweit")
    haken.toggled.connect(seite.zeige_auch_archiv_setzen)
    seite.unten_add(haken)
    return haken


__all__ = [
    "KUNDENFELDER",
    "LEISTUNGFELDER",
    "Bearbeitbar",
    "KundenAktionen",
    "kunden_haken",
]
