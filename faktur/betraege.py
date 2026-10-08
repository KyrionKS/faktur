"""Geldbeträge, Datumsangaben und Zahlen für Anzeige und PDF.

Alle Beträge endpreise. Es gibt keine Steuerausweisung, weil die App als
Werkzeug für Kleinunternehmer gedacht ist; wer umsatzsteuerpflichtig ist,
trägt den Betrag inklusive Steuer als Endpreis ein.
"""

from __future__ import annotations

import datetime
from decimal import ROUND_HALF_UP, Decimal

#: Das Zeichen hinter dem Betrag, wie es in Deutschland steht.
EUER = "€"


def zahl(wert: str | float | int | None) -> float:
    """Liest eine Zahl aus einer Eingabe.

    Akzeptiert Komma und Punkt als Trenner, toleriert Tausenderpunkte und
    ein Eurozeichen. Leer bedeutet ``0``.

    Args:
        wert: Die Eingabe, etwa ``"1.234,50"``.

    Returns:
        Die Zahl. ``0.0``, wenn nichts Brauchbares drinsteht.
    """
    if wert is None:
        return 0.0

    if isinstance(wert, (int, float)):
        return float(wert)

    text = str(wert).strip().replace("€", "").replace(" ", "")
    if not text:
        return 0.0

    # "1.234,56" -> "1234.56". Der letzte Trenner ist der Dezimalpunkt.
    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        text = text.replace(",", ".")
    elif text.count(".") == 1 and len(text.split(".")[1]) == 3:
        # "1.234" ist Tausenderpunkt, "1.23" ist Dezimalpunkt.
        text = text.replace(".", "")
    elif text.count(".") > 1:
        text = text.replace(".", "")

    try:
        return float(text)
    except ValueError:
        return 0.0


def _runden(wert: float) -> Decimal:
    """Rundet kaufmännisch auf zwei Stellen.

    Args:
        wert: Der zu rundende Betrag.

    Returns:
        Der gerundete Betrag als ``Decimal``.
    """
    return Decimal(str(wert)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def euro(wert: float) -> str:
    """Formatiert einen Betrag als deutsche Geldbetrag.

    Punkt als Tausendertrenner, Komma als Dezimaltrenner, immer zwei
    Nachkommastellen. Ein Geldbetrag ohne Nachkommastellen sieht auf einer
    Rechnung unvollständig aus, deshalb wird nicht gekürzt.

    Das Vorzeichen bleibt stehen. Eine Rabattposition trägt einen negativen
    Betrag, und ``-300,00 €`` gehört auf die Rechnung, nicht ``300,00 €``.
    Sonst sähe es aus, als würde die Summe steigen.

    Args:
        wert: Der Betrag.

    Returns:
        Der Text, etwa ``3.290,00 €`` oder ``−300,00 €``.
    """
    gerundet = _runden(wert)
    text = f"{gerundet:,.2f}"
    ganz, _, nachkomma = text.partition(".")
    return f"{ganz.replace(',', '.')},{nachkomma} {EUER}"


def menge(wert: float) -> str:
    """Formatiert eine Menge für die PDF.

    Ganze Zahlen ohne Nachkommastellen, sonst so viele, wie nötig sind.
    Auf einer Rechnung steht lieber ``2,5`` als ``2,50``. Die deutsche
    Schreibweise ist dabei dieselbe wie beim Geld.

    Args:
        wert: Die Menge.

    Returns:
        Der Text, etwa ``2,5``.
    """
    if wert == int(wert):
        return str(int(wert))

    text = f"{wert:.2f}".rstrip("0").rstrip(".")
    return text.replace(".", ",")


def prozent(wert: float, stellen: int = 1) -> str:
    """Formatiert einen Prozentsatz.

    Args:
        wert: Der Anteil, etwa ``19.0`` für 19 Prozent.
        stellen: Wie viele Nachkommastellen.

    Returns:
        Der Text, etwa ``19,0 %``.
    """
    text = f"{wert:.{stellen}f}"
    return f"{text.replace('.', ',')} %"


def _heute() -> datetime.date:
    """Gibt das heutige Datum zurück."""
    return datetime.date.today()


def lies_datum(text: str) -> datetime.date | None:
    """Liest ein Datum in irgendeiner gangbaren Schreibweise.

    Öffentlich, weil :mod:`faktur.nummer` daraus die Jahreszahl holt.

    Args:
        text: Das Datum, wie es in der Datenbank steht.

    Returns:
        Das Datum, oder ``None``, wenn keines erkannt wurde.
    """
    return _parse(text)


def _parse(text: str) -> datetime.date | None:
    """Liest ein Datum in deutscher oder englischer Schreibweise.

    Args:
        text: Die Eingabe, etwa ``"06.10.2026"`` oder ``"2026-10-06"``.

    Returns:
        Das Datum, oder ``None``, wenn es keines ist.
    """
    text = str(text or "").strip()
    if not text:
        return None

    for muster in ("%d.%m.%Y", "%d.%m.%y", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.datetime.strptime(text, muster).date()
        except ValueError:
            continue
    return None


def datum(wert: str | datetime.date) -> str:
    """Formatiert ein Datum deutsch.

    Args:
        wert: Ein ``date`` oder eine Eingabe in irgendeiner Schreibweise.

    Returns:
        Der Text ``06.10.2026``, oder leer, wenn kein Datum erkannt wurde.
    """
    if isinstance(wert, datetime.date):
        return wert.strftime("%d.%m.%Y")
    gefunden = _parse(wert)
    return gefunden.strftime("%d.%m.%Y") if gefunden else ""


def heute() -> str:
    """Das heutige Datum als Anzeigetext.

    Returns:
        Der Text ``06.10.2026``.
    """
    return _heute().strftime("%d.%m.%Y")


def jahr() -> str:
    """Das laufende Jahr als vierstellige Zahl.

    Returns:
        Der Text ``2026``.
    """
    return _heute().strftime("%Y")


def plus_tage(anzahl: int, von: datetime.date | None = None) -> str:
    """Rechnet ein Datum um Tage weiter.

    Args:
        anzahl: Wie viele Tage nach vorne, negative Werte gehen zurück.
        von: Der Ausgangstag. Standard ist heute.

    Returns:
        Das neue Datum als Anzeigetext.
    """
    start = von or _heute()
    return (start + datetime.timedelta(days=anzahl)).strftime("%d.%m.%Y")
