"""Welche Blöcke auf dem Dokument stehen.

Ein Dokument besteht aus mehreren Bausteinen: Firmenzeile, Anschrift,
Bankverbindung, Steuernummer, Fußzeile. Die kommen nicht alle auf jedes
Dokument, und nicht jeder will jede Zeile auf seiner Rechnung.

Deshalb gibt es hier eine Liste der Blöcke mit dem, was sie heute machen,
und eine Funktion, die aus den Einstellungen sagt, welche davon auf ein
Dokument gehören. Alles andere im Programm kennt nur noch diese Liste.

**Die Voreinstellung ist das heutige Dokument.** Sie steht in
:data:`VOREINSTELLUNG` und ist in ``tests/test_bloecke.py`` festgeschrieben:
Wer auf 0.5 geht, bekommt dieselben PDF wie vorher. Das ist der Grund, warum
hier überhaupt zwei Voreinstellungen stehen und nicht eine gemeinsame — eine
Rechnung braucht die Bankverbindung, ein Angebot nicht.

Die Rechnung ist absichtlich vollständig. Wer die Bankverbindung abschaltet,
hat eine Rechnung, auf der niemand zahlen kann.
"""

from __future__ import annotations

import sqlite3

#: Die Arten von Dokumenten, für die es eine Auswahl gibt.
ARTEN = ("angebot", "rechnung")

#: Die Kopfzeile links: Firmenname, Anschrift, Kontakt.
KOPF = "kopf"

#: Der Abschluss unter der Tabelle.
ABSCHLUSS = "abschluss"

#: Was auf jeder Seite unten steht.
FUSS = "fuss"


class Block:
    """Ein Baustein, der an oder ausgeschaltet werden kann.

    Attributes:
        name: Der Name, unter dem er in den Einstellungen steht.
        ort: Wo er auf dem Dokument steht.
        titel: Wie er im Menü heißt.
    """

    __slots__ = ("name", "ort", "titel")

    def __init__(self, name: str, ort: str, titel: str) -> None:
        """Legt den Block an.

        Args:
            name: Der Name, unter dem er in den Einstellungen steht.
            ort: Wo er auf dem Dokument steht.
            titel: Wie er im Menü heißt.
        """
        self.name = name
        self.ort = ort
        self.titel = titel

    def __repr__(self) -> str:
        """Nennt den Namen, damit Fehlermeldungen lesbar bleiben.

        Returns:
            Der Name des Blocks.
        """
        return f"Block({self.name!r})"


#: Alle Blöcke in der Reihenfolge, in der sie im Menü stehen.
BLOECKE = (
    Block("firma", KOPF, "Firmenname"),
    Block("zusatz", KOPF, "Zusatz zur Firma"),
    Block("anschrift", KOPF, "Anschrift"),
    Block("telefon", KOPF, "Telefon"),
    Block("email", KOPF, "E-Mail"),
    Block("webseite", KOPF, "Webseite"),
    Block("logo", KOPF, "Logo"),
    Block("zahlbar", ABSCHLUSS, "Zahlbar bis"),
    Block("bank", ABSCHLUSS, "Bank, IBAN, BIC"),
    Block("steuer", ABSCHLUSS, "Steuernummer"),
    Block("inhaber", ABSCHLUSS, "Inhaber"),
    Block("firmenzeile", FUSS, "Firmenzeile"),
    Block("seitenzahl", FUSS, "Seitenzahl"),
)

#: Die Namen aller Blöcke, so wie sie in den Einstellungen stehen.
NAMEN = tuple(block.name for block in BLOECKE)

#: Der Block, der zu einer Art gehört, oder ``None``.
ZUGEHOERIG: dict[str, dict[str, str]] = {
    "kopf": {},
    "abschluss": {},
    "fuss": {},
}
for _block in BLOECKE:
    ZUGEHOERIG[_block.ort][_block.name] = _block.titel
del _block

#: Was ohne jede Einstellung gilt. Es ist das Dokument von heute.
VOREINSTELLUNG = {
    # Auf einem Angebot stehen Bank, Steuernummer und Zahlhinweis nicht.
    # Das ist im Programm fest verdrahtet und bleibt es hier so.
    "angebot": (
        "firma",
        "zusatz",
        "anschrift",
        "telefon",
        "email",
        "logo",
        "inhaber",
        "firmenzeile",
        "seitenzahl",
    ),
    # Auf der Rechnung steht alles. Wer hier etwas abschaltet, weiß was er
    # tut.
    "rechnung": (
        "firma",
        "zusatz",
        "anschrift",
        "telefon",
        "email",
        "logo",
        "zahlbar",
        "bank",
        "steuer",
        "inhaber",
        "firmenzeile",
        "seitenzahl",
    ),
}

#: Die Webseite ist in keiner Voreinstellung an. Sie kam auf keinem Dokument
#: an, das es bisher gab. Wer sie einschaltet, holt sie zum ersten Mal auf die
#: PDF — das ist beabsichtigt und keine Nachlässigkeit.


def schluessel(art: str) -> str:
    """Nennt den Einstellungsschlüssel einer Dokumentart.

    Args:
        art: ``angebot`` oder ``rechnung``.

    Returns:
        Der Schlüssel, unter dem die Auswahl steht.
    """
    return f"ausgabe_{art.strip().lower()}"


def _zerlege(wert: str) -> list[str]:
    """Zerlegt den gespeicherten Wert in Namen.

    Args:
        wert: Die durch Komma getrennten Namen.

    Returns:
        Die Namen, ohne leere und ohne Doppelungen.
    """
    gesehen: list[str] = []

    for stueck in wert.split(","):
        name = stueck.strip()
        if name and name not in gesehen:
            gesehen.append(name)

    return gesehen


def voreinstellung(art: str) -> frozenset[str]:
    """Sagt, was ohne jede Einstellung auf das Dokument gehört.

    Args:
        art: ``angebot`` oder ``rechnung``.

    Returns:
        Die Namen der Blöcke.

    Raises:
        KeyError: Wenn die Art nicht bekannt ist.
    """
    if art not in VOREINSTELLUNG:
        raise KeyError(art)
    return frozenset(VOREINSTELLUNG[art])


def ausgabe(db: sqlite3.Connection, art: str) -> frozenset[str]:
    """Sagt, welche Blöcke auf ein Dokument gehören.

    Ein fehlender Schlüssel bedeutet Voreinstellung. Das ist der Fall bei
    jeder Datenbank, die vor dieser Funktion entstanden ist. Ein leerer
    Wert bedeutet dasselbe, nicht „nichts drucken": Wer die Auswahl leert,
    bekommt nicht plötzlich ein leeres Dokument, sondern das übliche.

    Namen, die es nicht gibt, werden stillschweigend überlesen. Eine
    Einstellung aus einer künftigen Version soll dieses Programm nicht
    lahmlegen.

    Args:
        db: Die Datenbankverbindung.
        art: ``angebot`` oder ``rechnung``.

    Returns:
        Die Namen der Blöcke, die auf das Dokument gehören.

    Raises:
        KeyError: Wenn die Art nicht bekannt ist.
    """
    from faktur import einstellungen

    roh = einstellungen.hole(db, schluessel(art)).strip()
    if not roh:
        return voreinstellung(art)

    bekannt = NAMEN
    return frozenset(name for name in _zerlege(roh) if name in bekannt)


def gehoert(db: sqlite3.Connection, art: str, name: str) -> bool:
    """Sagt, ob ein Block auf ein Dokument gehört.

    Args:
        db: Die Datenbankverbindung.
        art: ``angebot`` oder ``rechnung``.
        name: Der Name des Blocks.

    Returns:
        ``True``, wenn der Block erscheinen soll.
    """
    return name in ausgabe(db, art)


def speichere(db: sqlite3.Connection, art: str, namen: frozenset[str]) -> None:
    """Schreibt die Auswahl einer Dokumentart.

    Es wird in der Reihenfolge von :data:`BLOECKE` gespeichert, nicht in der
    Reihenfolge des Klickens. Sonst stünde in der Einstellung später etwas
    wie ``seitenzahl,firma,logo`` und niemand könnte es lesen.

    Args:
        db: Die Datenbankverbindung.
        art: ``angebot`` oder ``rechnung``.
        namen: Die Namen der Blöcke, die erscheinen sollen.

    Raises:
        KeyError: Wenn die Art nicht bekannt ist.
    """
    from faktur import einstellungen

    if art not in VOREINSTELLUNG:
        raise KeyError(art)

    geordnet = ",".join(name for name in NAMEN if name in namen)
    einstellungen.speichere(db, schluessel(art), geordnet)
