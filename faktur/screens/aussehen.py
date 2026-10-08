"""Der Bildschirm *Aussehen*.

Hier stehen die Größen der PDF und die Wahl, welche Stammdaten auf ein
Dokument kommen. Angebot und Rechnung werden getrennt eingestellt, weil sie
nicht dasselbe brauchen: Auf einem Angebot hat eine Bankverbindung nichts zu
suchen, auf einer Rechnung ist sie das Wichtigste überhaupt.

Der Bildschirm schreibt nichts aufs Papier. Erst ``F2`` schreibt das neueste
Dokument neu und öffnet den Ordner.

Das ist der ganze Bildschirm, kein Untermenü. Zwei Bildschirme wären mehr
Umweg als nötig: Wer eine Größe ändern will, muss sie nicht erst suchen.
"""

from __future__ import annotations

import sqlite3

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.widgets import Static

from faktur import bloecke, dateien, db, einstellungen, pdf
from faktur.basis import BasisScreen
from faktur.einstellungsliste import Einstellungen, Zeile, bauen

#: Der Einstellungsschlüssel zu jeder Größe, nach dem Titel im Bildschirm.
SCHLUESSEL = {
    "Logogröße": "logo_groesse",
    "Schriftgröße": "text_groesse",
}


class AussehenScreen(BasisScreen):
    """Logogröße, Schriftgröße und die Wahl der Bausteine.

    Attributes:
        art: Die gerade gezeigte Dokumentart.
        liste: Die bedienbare Liste.
    """

    BINDINGS = [
        Binding("f2", "anwenden", "Neu schreiben", show=True),
    ]

    def __init__(self, verbindung: sqlite3.Connection) -> None:
        """Legt den Bildschirm an.

        Args:
            verbindung: Die Datenbankverbindung.
        """
        super().__init__(verbindung)
        self.art = "angebot"
        self.liste: Einstellungen | None = None

    def inhalt(self) -> ComposeResult:
        """Baut die Liste.

        Yields:
            Die Kindelemente.
        """
        self.liste = Einstellungen(
            self._zeilen(), self._geaendert, self._art_gewechselt
        )

        with VerticalScroll():
            yield self.liste
            yield Static(
                "↑↓ bewegen   ←→ ändern   ␣ umschalten   F2 neu schreiben   esc zurück",
                classes="hinweis",
            )

    def _zeilen(self) -> list[Zeile]:
        """Baut die Liste aus den gespeicherten Einstellungen.

        Returns:
            Die Zeilen in der Reihenfolge der Anzeige.
        """
        return bauen(
            art=self.art,
            logo=pdf.logo_groesse(self.db),
            text=pdf.text_groesse(self.db),
            bloecke=[(b.name, b.ort, b.titel) for b in bloecke.BLOECKE],
            an=bloecke.ausgabe(self.db, self.art),
        )

    def start_fokus(self) -> None:
        """Setzt den Fokus auf die Liste."""
        if self.liste is not None:
            self.liste.focus()

    # ------------------------------------------------------------- Bedienung

    def _geaendert(self, zeile: Zeile) -> None:
        """Speichert die Zeile, die sich geändert hat.

        Args:
            zeile: Die Zeile aus dem Baustein.
        """
        if zeile.art == "groesse":
            schluessel = SCHLUESSEL.get(zeile.titel)
            if schluessel:
                einstellungen.speichere(self.db, schluessel, zeile.wert)
        elif zeile.art == "block":
            self._block_umgeschaltet(zeile)

    def _block_umgeschaltet(self, zeile: Zeile) -> None:
        """Schreibt die Auswahl der gerade gezeigten Dokumentart.

        Args:
            zeile: Die Zeile mit dem Block.
        """
        gewechselt = set(bloecke.ausgabe(self.db, self.art))

        if zeile.an:
            gewechselt.add(zeile.block)
        else:
            gewechselt.discard(zeile.block)

        bloecke.speichere(self.db, self.art, frozenset(gewechselt))

    def _art_gewechselt(self) -> None:
        """Wechselt zwischen Angebot und Rechnung.

        Die beiden Größen bleiben, weil sie für beide Arten gleich gelten.
        Sonst müsste man jedes Mal wieder nach oben navigieren, nur um die
        Schriftgröße zu ändern.
        """
        self.art = "rechnung" if self.art == "angebot" else "angebot"

        if self.liste is None:
            return

        alt = self.liste
        alt.setze_zeilen(
            bauen(
                art=self.art,
                logo=alt.zeilen[1].wert,
                text=alt.zeilen[2].wert,
                bloecke=[(b.name, b.ort, b.titel) for b in bloecke.BLOECKE],
                an=bloecke.ausgabe(self.db, self.art),
            )
        )

    def action_anwenden(self) -> None:
        """Schreibt das neueste Dokument neu und öffnet den Ordner."""
        from faktur import app as appmodul

        dokumente = dateien.dokumente(self.db)
        if not dokumente:
            self.meldung("Es gibt noch kein Dokument zum Neu-Schreiben.", gut=False)
            return

        voll = dateien.dokument_holen(self.db, dokumente[0]["id"])
        if voll is None:
            self.meldung("Das Dokument gibt es nicht mehr.", gut=False)
            return

        try:
            pfad = pdf.erzeugen(self.db, voll, db.DOKUMENTE / dateien.dateiname(voll))
        except Exception as grund:  # noqa: BLE001
            self.meldung(f"Konnte nicht schreiben: {grund}", gut=False)
            return

        self.meldung(f"Geschrieben: {pfad.name}", gut=True)

        fehler = appmodul.zeige_ausgabeordner()
        if fehler:
            self.meldung(fehler, gut=False)
