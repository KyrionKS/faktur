"""Farben und Schriften der PDF.

Eine einzige Akzentfarbe, aus dem Firmenlogo ausgelesen. Der Rest ist
Schwarz und Grau. Viel Weissraum und dünne Linien statt Kästen: ein Angebot
soll wie ein Brief aussehen, nicht wie ein Formular.

**Keine festen Zahlen, sondern Anteile.** Jeder Stil beschreibt sich als
Anteil der Grundgröße und als Anteil der eigenen Schriftgröße für den
Zeilenabstand. Wird der Fließtext größer, wächst alles Zusammengehörige
zwangsläufig mit. Fest verdrahtete Werte müsste man bei fünfzehn Stilen
von Hand nachziehen, und die meisten würden es vergessen — der Zeilenabstand
bliebe stehen, während die Schrift wächst, und die Zeilen klebten aneinander.

``tests/test_gestaltung.py`` hält fest, dass die Anteile bei der
Standardgröße genau die Zahlen ergeben, die vorher fest eingetragen waren.
"""

from __future__ import annotations

from dataclasses import dataclass

#: Die Akzentfarbe, aus dem Logo ausgelesen.
AKZENT = "#512E80"

#: Der Fliesstext. Fast Schwarz, aber nicht hart.
TEXT = "#1A1A1A"

#: Kleinzeilen wie Seitenzahl und Fusszeile.
SEKUNDAER = "#6B6B6B"

#: Linien unter und ueber Tabellen.
LINIE = "#E2E2E2"

#: Ein sehr heller Ton, etwa für die Fusszeile.
FLACKE = "#F7F7F8"

#: Die Größe des Fließtextes, auf die sich alle Anteile beziehen.
GRUND = 9.5

#: Die Familie für Fliesstext und Tabellen.
SCHRIFT = "Helvetica"

#: Die Familie für Beträge und Überschriften.
BETRAG_SCHRIFT = "Helvetica-Bold"

#: Die wählbaren Größen mit ihrem Anteil an :data:`GRUND`.
GRUESSEN = {
    "klein": 0.9,
    "normal": 1.0,
    "gross": 1.1,
}

#: Die Größe, die gilt, wenn keine eingestellt oder eine unbekannte ist.
STANDARD_GROESSE = "normal"

#: Links, mittig, rechts — die Zahlen, die reportlab erwartet.
LINKS = 0
MITTIG = 1
RECHTS = 2


def groesse_faktor(name: str) -> float:
    """Sucht den Anteil zu einer Größenangabe.

    Args:
        name: ``klein``, ``normal`` oder ``gross``.

    Returns:
        Der Anteil an :data:`GRUND`. Für alles andere die Standardgröße.
    """
    return GRUESSEN.get(name.strip(), GRUESSEN[STANDARD_GROESSE])


@dataclass(frozen=True)
class Stil:
    """Ein Absatzstil in Anteilen statt in festen Zahlen.

    Attributes:
        groesse: Die Schriftgröße als Anteil von :data:`GRUND`.
        zeilen: Der Zeilenabstand als Anteil der eigenen Schriftgröße.
        farbe: Der Name der Farbe aus :data:`FARBEN`.
        ausrichtung: 0, 1 oder 2.
        davor: Der Platz davor in Punkt.
        danach: Der Platz danach in Punkt.
    """

    groesse: float
    zeilen: float
    farbe: str = "text"
    ausrichtung: int = LINKS
    davor: float = 0.0
    danach: float = 0.0


#: Die Farben unter dem Namen, unter dem die Stile sie verlangen.
FARBEN = {
    "akzent": AKZENT,
    "text": TEXT,
    "sekundaer": SEKUNDAER,
}

#: Alle Stile, die die PDF benutzt.
STILE = {
    "firma": Stil(groesse=1.3684, zeilen=1.2308, farbe="akzent"),
    "empfaenger": Stil(groesse=1.0526, zeilen=1.4),
    "art": Stil(groesse=1.7895, zeilen=1.2353, farbe="akzent", danach=2.0),
    "kopf_daten": Stil(
        groesse=1.0, zeilen=1.3684, farbe="sekundaer", ausrichtung=RECHTS
    ),
    "absatz": Stil(groesse=1.0, zeilen=1.4737, danach=7.0),
    "anrede": Stil(groesse=1.0, zeilen=1.4737, danach=9.0),
    "tab_kopf": Stil(groesse=0.8421, zeilen=1.375, farbe="sekundaer"),
    "tab_text": Stil(groesse=1.0, zeilen=1.3684),
    "tab_zahl": Stil(groesse=1.0, zeilen=1.3684, ausrichtung=RECHTS),
    "tab_zahl_fett": Stil(groesse=1.0, zeilen=1.3684, ausrichtung=RECHTS),
    "summe": Stil(groesse=1.2632, zeilen=1.3333, farbe="akzent", ausrichtung=RECHTS),
    # Eine Rabattposition. Sie steht in der Akzentfarbe, damit man sie auf
    # Anhieb sieht, aber nicht so, dass die Tabelle bunt wirkt.
    "rabatt_text": Stil(groesse=1.0, zeilen=1.3684, farbe="akzent"),
    "rabatt_zahl": Stil(groesse=1.0, zeilen=1.3684, farbe="akzent", ausrichtung=RECHTS),
    "klein": Stil(groesse=0.7895, zeilen=1.3333, farbe="sekundaer"),
}

#: Die Stile, deren Schrift fett gesetzt wird.
FETT = frozenset({"firma", "art", "tab_kopf", "tab_zahl_fett", "summe"})

#: Die Schriftgröße der Fußzeile. Sie ist der Kleinststil und wächst mit ihm.
KLEIN_FAKTOR = STILE["klein"].groesse


def hex_rgb(wert: str) -> tuple[float, float, float]:
    """Wandelt ``#RRGGBB`` in die drei Anteile von 0 bis 1.

    Args:
        wert: Die Farbangabe mit führendem Rauten.

    Returns:
        Das Tripel für reportlab.
    """
    wert = wert.lstrip("#")
    return tuple(int(wert[i : i + 2], 16) / 255 for i in (0, 2, 4))  # type: ignore[return-value]


def groesse_von(name: str, faktor: float = 1.0) -> float:
    """Rechnet den Anteil einer Schriftgröße in Punkt um.

    Args:
        name: Der Name des Stils aus :data:`STILE`.
        faktor: Der Anteil der gewählten Größe an :data:`GRUND`.

    Returns:
        Die Schriftgröße in Punkt.

    Raises:
        KeyError: Wenn es den Stil nicht gibt.
    """
    return round(GRUND * STILE[name].groesse * faktor, 2)


def zeilen_von(name: str, faktor: float = 1.0) -> float:
    """Rechnet den Zeilenabstand eines Stils in Punkt um.

    Der Abstand ist ein Anteil der *eigenen* Schriftgröße, nicht der
    Grundgröße. Das ist so üblich und bleibt bei jeder Größe im richtigen
    Verhältnis zur Schrift.

    Args:
        name: Der Name des Stils aus :data:`STILE`.
        faktor: Der Anteil der gewählten Größe an :data:`GRUND`.

    Returns:
        Der Zeilenabstand in Punkt.

    Raises:
        KeyError: Wenn es den Stil nicht gibt.
    """
    return round(groesse_von(name, faktor) * STILE[name].zeilen, 2)


def stile(faktor: float = 1.0) -> dict[str, object]:
    """Baut die Absatzstile für reportlab.

    Args:
        faktor: Der Anteil der gewählten Größe an :data:`GRUND`. 1.0
            ergibt genau die Werte, die vor der Umstellung fest
            eingetragen waren.

    Returns:
        Ein Dictionary aus Stilnamen und ``ParagraphStyle``.
    """
    from reportlab.lib.styles import ParagraphStyle

    gebaut: dict[str, object] = {}

    for name, stil in STILE.items():
        gebaut[name] = ParagraphStyle(
            name,
            fontName=BETRAG_SCHRIFT if name in FETT else SCHRIFT,
            fontSize=groesse_von(name, faktor),
            leading=zeilen_von(name, faktor),
            textColor=hex_rgb(FARBEN[stil.farbe]),
            alignment=stil.ausrichtung,
            spaceBefore=round(stil.davor * faktor, 2),
            spaceAfter=round(stil.danach * faktor, 2),
        )

    return gebaut
