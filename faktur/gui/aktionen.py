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

        # Doppelklick macht dasselbe wie *Ändern*. Das ist der Weg, den
        # man in Mail, Notizen und überall sonst erwartet, und man muss
        # ihn nicht suchen. Also geht er nicht nur über die Taste.
        seite.ansicht.doubleClicked.connect(self._doppelt)

    def _doppelt(self, index: object) -> None:
        """Öffnet das Blatt bei einem Doppelklick.

        Args:
            index: Die Zeile, auf die geklickt wurde. Geprüft wird sie,
                denn ein Doppelklick neben der Liste trifft keine Zeile.

        Returns:
            Nichts.
        """
        if index is not None and index.isValid():
            self.aendern()

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

        **Löscht aber nur, wenn nichts daran hängt.** :meth:`darf_loeschen`
        entscheidet das. Bei einem Kunden mit Rechnungen wird nicht
        gelöscht, sondern die Frage gestellt, ob statt dessen stillgelegt
        werden soll.

        Returns:
            ``True``, wenn gelöscht wurde.
        """
        datensatz = self.seite.gewaehlt()
        if datensatz is None:
            self.seite.melde("Erst einen Eintrag markieren.")
            return False

        erlaubt, erklaerung = self.darf_loeschen(datensatz)
        if not erlaubt:
            return self._stilllegen_statt_loeschen(datensatz, erklaerung)

        antwort = QMessageBox.question(
            self.seite,
            f"{self.einheit} löschen",
            self.frage(datensatz),
            QMessageBox.StandardButton.Cancel | QMessageBox.StandardButton.Yes,
            QMessageBox.StandardButton.Cancel,
        )
        if antwort != QMessageBox.StandardButton.Yes:
            return False

        self.seite.loesche(self.seite.kennung(datensatz))
        self.seite.melde(f"{self.einheit} gelöscht.")
        self.seite.erneut_laden()
        return True

    def darf_loeschen(self, datensatz: object) -> tuple[bool, str]:
        """Sagt, ob gelöscht werden darf — und warum nicht.

        Bei einer Leistung immer ja: :func:`faktur.dateien.leistung_loeschen`
        nimmt nur die Verknüpfung von den Positionen, Text und Preis bleiben
        auf den alten Belegen stehen. Es geht nichts verloren.

        Args:
            datensatz: Der gewählte Datensatz.

        Returns:
            Ob gelöscht werden darf, und im Zweifel der Text, der es
            erklärt.
        """
        return True, ""

    def _stilllegen_statt_loeschen(self, datensatz: object, erklaerung: str) -> bool:
        """Bietet das Stilllegen an, statt zu löschen.

        Returns:
            ``True``, wenn stillgelegt wurde.
        """
        kasten = QMessageBox(self.seite)
        kasten.setIcon(QMessageBox.Icon.Warning)
        kasten.setWindowTitle(f"{self.einheit} löschen geht nicht")
        kasten.setText(erklaerung)
        kasten.setInformativeText(
            "Stilllegen nimmt ihn nur aus den Listen. Seine Belege bleiben, "
            "und der Kunde ist wieder da, sobald du ihn zurückholst."
        )
        taste = kasten.addButton("Stilllegen", QMessageBox.ButtonRole.AcceptRole)
        kasten.addButton(QMessageBox.StandardButton.Cancel)
        kasten.setDefaultButton(QMessageBox.StandardButton.Cancel)
        kasten.exec()

        if kasten.clickedButton() is not taste:
            return False

        self.seite.stilllege(self.seite.kennung(datensatz), False)
        self.seite.melde(f"{self.einheit} stillgelegt, nicht gelöscht.")
        self.seite.erneut_laden()
        return False

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

    def darf_loeschen(self, datensatz: object) -> tuple[bool, str]:
        """Ein Kunde mit Belegen wird nicht gelöscht.

        :func:`faktur.dateien.kunde_loeschen` nimmt einem Kunden die
        Dokumente mit, damit die Rechnungen. Die PDF im Ausgangsordner
        bleiben zwar liegen, aber in keiner Buchhaltung taucht der Kunde
        danach noch auf — und es gibt keinen Papierkorb, in dem man ihn
        suchen könnte.

        Darum wird hier **nicht gelöscht**, sondern stillgelegt. Das ist die
        einzige Stelle im Programm, an der Daten unwiederbringlich weggehen
        könnten, und sie wird ab jetzt die einzige Stelle, an der es eine
        Rückfrage gibt.

        Args:
            datensatz: Der gewählte Kunde.

        Returns:
            ``False`` und ein Text, wenn Dokumente daran hängen.
        """
        anzahl = dateien.kundenzahl(self.seite.db, self.seite.kennung(datensatz))
        if anzahl == 0:
            return True, ""

        name = self.seite.als_daten(datensatz).get("firma", "")
        wort = "Dokument" if anzahl == 1 else "Dokumente"
        return (
            False,
            f"„{name}“ hat {anzahl} {wort}. Beim Löschen gehen sie mit — "
            "und der Kunde fehlt danach in keiner Buchhaltung mehr.",
        )

    def frage(self, datensatz: object) -> str:
        """Die Rückfrage, wenn gelöscht werden darf.

        Bis hierher kommt nur, was keine Dokumente hat — sonst hat
        :meth:`darf_loeschen` schon abgebrochen. Die Zahl der Dokumente
        steht deshalb nicht mehr in der Frage, sie steht im Grund dafür,
        dass gar nicht erst gefragt wird.

        Args:
            datensatz: Der gewählte Kunde aus der Datenbank.

        Returns:
            Der Text der Frage.
        """
        name = self.seite.als_daten(datensatz).get("firma", "")
        return f"„{name}“ löschen? Der Kunde hat keine Belege."


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
