"""Die Listen im Fenster.

Sechs Bereiche, und fünf davon sehen gleich aus: Titel, Suchfeld, Tabelle.
Was sie unterscheidet, ist die Spalte, und die steht deshalb bei der Seite
und nicht im Rahmen.

**Hier wird nichts gerechnet.** Eine Summe, ein Status und ein Datum kommen
aus den Logikmodulen. Diese Datei baut nur Texte und reicht sie weiter.
"""

from __future__ import annotations

import sqlite3

from faktur import betraege, dateien, offen
from faktur.gui.aktionen import (
    KUNDENFELDER,
    LEISTUNGFELDER,
    Bearbeitbar,
    KundenAktionen,
    kunden_haken,
)
from faktur.gui.seite import ListenSeite
from faktur.gui.tabelle import Eintrag, Zellen, nach_zahl

# --------------------------------------------------------------------- Kunden


def kunden_zellen(kunde: sqlite3.Row) -> list[str]:
    """Baut eine Listenzeile aus einem Kunden.

    Args:
        kunde: Der Kunde aus der Datenbank.

    Returns:
        Die Zellen der Zeile.
    """
    kontakt = " · ".join(teil for teil in (kunde["email"], kunde["telefon"]) if teil)
    return [
        str(kunde["firma"]),
        str(kunde["ansprechpartner"] or ""),
        str(kunde["ort"] or ""),
        kontakt,
    ]


class KundenSeite(ListenSeite):
    """Alle Kunden, mit den Stillgelegten unter einem Haken."""

    def __init__(self, db: sqlite3.Connection) -> None:
        """Baut die Kundenliste.

        Args:
            db: Die Datenbankverbindung.
        """
        super().__init__(
            db,
            "Kunden",
            ("Firma", "Ansprechpartner", "Ort", "Kontakt"),
            kunden_zellen,
            "Kunden",
            "Kunde",
        )
        self.zeige_auch_archiv = False
        self.aktionen = KundenAktionen(self, KUNDENFELDER, "Kunde", "Kunden")
        kunden_haken(self)

    def hole(self) -> list[sqlite3.Row]:
        """Holt die Kunden.

        Returns:
            Die Kunden, aktive zuerst und innerhalb einer Gruppe nach Name.
        """
        kunden = dateien.kunden(self.db, nur_aktive=not self.zeige_auch_archiv)
        return sorted(
            kunden,
            key=lambda k: (not k["aktiv"], k["firma"].casefold()),
        )

    def als_daten(self, datensatz: Eintrag) -> dict[str, str]:
        """Macht aus einem Kunden die Werte für das Blatt.

        Args:
            datensatz: Der Kunde aus der Datenbank.

        Returns:
            Die Werte.
        """
        return {
            feld.schluessel: str(datensatz[feld.schluessel] or "")
            for feld in KUNDENFELDER
        }

    def kennung(self, datensatz: Eintrag) -> int:
        """Gibt die Nummer des Kunden zurück.

        Args:
            datensatz: Der Kunde aus der Datenbank.

        Returns:
            Seine Nummer.
        """
        return int(datensatz["id"])

    def speichere_neu(self, daten: dict[str, str]) -> None:
        """Legt einen Kunden an.

        Args:
            daten: Die Werte aus dem Blatt.

        Returns:
            Nichts.
        """
        dateien.kunde_speichern(self.db, daten)

    def speichere_alt(self, kennung: int, daten: dict[str, str]) -> None:
        """Ändert einen Kunden.

        Args:
            kennung: Seine Nummer.
            daten: Die Werte aus dem Blatt.

        Returns:
            Nichts.
        """
        dateien.kunde_speichern(self.db, daten, kennung)

    def loesche(self, kennung: int) -> None:
        """Löscht einen Kunden samt seiner Dokumente.

        Args:
            kennung: Seine Nummer.

        Returns:
            Nichts.
        """
        dateien.kunde_loeschen(self.db, kennung)

    def stilllege(self, kennung: int, aktiv: bool) -> None:
        """Legt einen Kunden still oder holt ihn zurück.

        Args:
            kennung: Seine Nummer.
            aktiv: Ob er in der Liste stehen soll.

        Returns:
            Nichts.
        """
        dateien.kunde_stilllegen(self.db, kennung, aktiv)


# ----------------------------------------------------------------- Leistungen


def leistung_zellen(leistung: sqlite3.Row) -> list[str]:
    """Baut eine Listenzeile aus einer Leistung.

    Args:
        leistung: Die Leistung aus der Datenbank.

    Returns:
        Die Zellen der Zeile.
    """
    return [
        str(leistung["bezeichnung"]),
        str(leistung["einheit"] or ""),
        betraege.euro(leistung["preis"]),
        str(leistung["beschreibung"] or ""),
    ]


class LeistungenSeite(ListenSeite):
    """Die Preisliste."""

    def __init__(self, db: sqlite3.Connection) -> None:
        """Baut die Leistungsliste.

        Args:
            db: Die Datenbankverbindung.
        """
        super().__init__(
            db,
            "Leistungen",
            ("Bezeichnung", "Einheit", "Preis", "Beschreibung"),
            leistung_zellen,
            "Leistungen",
            "Leistung",
            vergleiche={2: nach_zahl(2)},
        )
        self.zeige_auch_archiv = False
        self.aktionen = Bearbeitbar(self, LEISTUNGFELDER, "Leistung", "Leistungen")
        kunden_haken(self).setText("auch stillgelegte")

    def hole(self) -> list[sqlite3.Row]:
        """Holt die Leistungen.

        Returns:
            Die Leistungen, aktive zuerst und sonst nach Bezeichnung.
        """
        daten = dateien.leistungen(self.db, nur_aktive=not self.zeige_auch_archiv)
        return sorted(
            daten,
            key=lambda eine: (not eine["aktiv"], eine["bezeichnung"].casefold()),
        )

    def als_daten(self, datensatz: Eintrag) -> dict[str, str]:
        """Macht aus einer Leistung die Werte für das Blatt.

        Args:
            datensatz: Die Leistung aus der Datenbank.

        Returns:
            Die Werte.
        """
        return {
            feld.schluessel: str(datensatz[feld.schluessel] or "")
            for feld in LEISTUNGFELDER
        }

    def kennung(self, datensatz: Eintrag) -> int:
        """Gibt die Nummer der Leistung zurück.

        Args:
            datensatz: Die Leistung aus der Datenbank.

        Returns:
            Ihre Nummer.
        """
        return int(datensatz["id"])

    def speichere_neu(self, daten: dict[str, str]) -> None:
        """Legt eine Leistung an.

        Args:
            daten: Die Werte aus dem Blatt.

        Returns:
            Nichts.
        """
        dateien.leistung_speichern(self.db, daten)

    def speichere_alt(self, kennung: int, daten: dict[str, str]) -> None:
        """Ändert eine Leistung.

        Args:
            kennung: Ihre Nummer.
            daten: Die Werte aus dem Blatt.

        Returns:
            Nichts.
        """
        dateien.leistung_speichern(self.db, daten, kennung)

    def loesche(self, kennung: int) -> None:
        """Nimmt eine Leistung aus der Preisliste.

        Args:
            kennung: Ihre Nummer.

        Returns:
            Nichts.
        """
        dateien.leistung_loeschen(self.db, kennung)

    def stilllege(self, kennung: int, aktiv: bool) -> None:
        """Legt eine Leistung still oder holt sie zurück.

        Args:
            kennung: Ihre Nummer.
            aktiv: Ob sie in der Liste stehen soll.

        Returns:
            Nichts.
        """
        dateien.leistung_stilllegen(self.db, kennung, aktiv)


# ------------------------------------------------------------------ Dokumente


def dokument_zellen(db: sqlite3.Connection) -> Zellen:
    """Baut eine Funktion, die aus einem Dokument eine Zeile macht.

    Die Summe steht nicht im Dokument, sie liegt in den Positionen. Darum
    braucht die Funktion die Datenbank.

    Args:
        db: Die Datenbankverbindung.

    Returns:
        Eine Funktion aus einem Dokument in eine Liste von Texten.
    """

    def zellen(dokument: sqlite3.Row) -> list[str]:
        """Baut die Zeile eines Dokuments.

        Args:
            dokument: Das Dokument aus der Datenbank.

        Returns:
            Die Zellen der Zeile.
        """
        return [
            str(dokument["nummer"]),
            _kurz_datum(dokument["datum"]),
            str(dokument["firma"]),
            _art(dokument["art"]),
            betraege.euro(dateien.summe_von(db, dokument["id"])),
            _status(dokument),
        ]

    return zellen


def _art(art: str) -> str:
    """Sagt, ob ein Dokument Angebot oder Rechnung ist.

    Args:
        art: Die Art aus der Datenbank.

    Returns:
        Das Wort, das in der Liste steht.
    """
    return "Rechnung" if art == "rechnung" else "Angebot"


def _status(dokument: sqlite3.Row) -> str:
    """Sagt, wo ein Dokument steht.

    Args:
        dokument: Das Dokument aus der Datenbank.

    Returns:
        Das Wort, das in der Liste steht.
    """
    if dokument["art"] == "angebot":
        if dokument["gueltig_bis"] and dokument["gueltig_bis"] < betraege.heute():
            return "abgelaufen"
        return "angeboten"
    if offen.ist_bezahlt(dokument):
        return "bezahlt"
    if offen.ist_faellig(dokument, betraege.heute()):
        return "überfällig"
    return "offen"


def _kurz_datum(wert: str) -> str:
    """Kürzt ein Datum auf Tag und Monat.

    Args:
        wert: Das Datum aus der Datenbank, oder ``""``.

    Returns:
        Das kurze Datum, oder ``""``.
    """
    if len(wert) == 10:
        return f"{wert[8:10]}.{wert[5:7]}.{wert[2:4]}"
    return ""


class DokumenteSeite(ListenSeite):
    """Alle Angebote und Rechnungen, neueste zuerst."""

    def __init__(self, db: sqlite3.Connection) -> None:
        """Baut die Dokumentenliste.

        Args:
            db: Die Datenbankverbindung.
        """
        self.nur_rechnungen = False
        self.geoeffnet = None
        super().__init__(
            db,
            "Dokumente",
            ("Nummer", "Datum", "Kunde", "Art", "Summe", "Status"),
            dokument_zellen(db),
            "Dokumente",
            "Dokument",
            vergleiche={4: nach_zahl(4)},
        )
        self.ansicht.doubleClicked.connect(self._doppelt)

    def _doppelt(self, index: object) -> None:
        """Meldet dem Fenster, dass ein Dokument geoeffnet werden soll.

        Args:
            index: Die Zeile, auf die geklickt wurde.

        Returns:
            Nichts.
        """
        if index is not None and index.isValid() and self.geoeffnet is not None:
            self.ansicht.setCurrentIndex(index)
            self.geoeffnet()
        self.ansicht.setSortingEnabled(True)

    def hole(self) -> list[sqlite3.Row]:
        """Holt die Dokumente.

        Returns:
            Die Dokumente, neueste zuerst.
        """
        art = "rechnung" if self.nur_rechnungen else None
        return dateien.dokumente(self.db, art)


# ---------------------------------------------------------------- Offene Rechn.


class OffeneSeite(ListenSeite):
    """Die Rechnungen, auf die noch Geld fehlt.

    Steht hier eine Rechnung drin, die überfällig ist, steht sie in
    :mod:`faktur.offen` an erster Stelle, mit den Tagen.
    """

    def __init__(self, db: sqlite3.Connection) -> None:
        """Baut die Liste der offenen Forderungen.

        Args:
            db: Die Datenbankverbindung.
        """
        super().__init__(
            db,
            "Offene Forderungen",
            ("Nummer", "Kunde", "Fällig am", "Summe", "Tage"),
            self._zellen,
            "Forderungen",
            "Forderung",
            vergleiche={3: nach_zahl(3), 4: nach_zahl(4)},
        )

    def hole(self) -> list[sqlite3.Row]:
        """Holt die offenen Rechnungen.

        Returns:
            Die offenen Rechnungen, die überfälligsten zuerst.
        """
        return offen.offene(self.db)

    def _zellen(self, dokument: sqlite3.Row) -> list[str]:
        """Baut die Zeile einer offenen Rechnung.

        Args:
            dokument: Die Rechnung aus der Datenbank.

        Returns:
            Die Zellen der Zeile.
        """
        tage = _tage_danach(dokument["faellig"])
        return [
            str(dokument["nummer"]),
            str(dokument["firma"]),
            _kurz_datum(dokument["faellig"]),
            betraege.euro(dateien.summe_von(self.db, dokument["id"])),
            str(tage) if tage > 0 else "",
        ]


def _tage_danach(faellig: str) -> int:
    """Zählt, wie viele Tage eine Rechnung überfällig ist.

    Args:
        faellig: Das Fälligkeitsdatum aus der Datenbank, oder ``""``.

    Returns:
        Die Zahl der Tage. Ohne Datum oder vor dem Datum: ``0``.
    """
    if not faellig:
        return 0
    datum = betraege.lies_datum(faellig)
    if datum is None:
        return 0
    heute = betraege.lies_datum(betraege.heute())
    if heute is None:
        return 0
    return (heute - datum).days


__all__ = [
    "DokumenteSeite",
    "KundenSeite",
    "LeistungenSeite",
    "OffeneSeite",
    "kunden_zellen",
    "leistung_zellen",
]
