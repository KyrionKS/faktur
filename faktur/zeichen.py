"""Das Logo als Text.

Ein Terminal kann keine PNG anzeigen. Was sich übertragen lässt, ist die
Form: ein Gitter aus Kreuzlinien und die sieben Rauten darauf. Das Raster
hier ist eine Nachzeichnung, nicht eine Pixelumwandlung — die Raute sitzt
auf dem Gitter, genau wie in der Vorlage.

Die Vorlage liegt in ``~/.faktur/logo.png`` und wird für die PDF benutzt.
"""

from __future__ import annotations

#: Das Gitter mit den Rauten, 32 Zeichen breit und 8 Zeilen hoch.
#:
#: ``◆`` steht für einen Rauten, ``╲`` und ``╱`` für die beiden
#: Diagonalen des Gitters.
RASTER = (
    "╲     ╲     ╲     ╲     ╲     ╲",
    " ╲   ╱ ╲   ╱ ╲   ╱ ╲   ╱ ╲   ╱ ╲",
    "  ╲ ╱   ╲ ╱   ╲ ╱   ╲ ◆   ╲ ╱  ",
    "   ╲     ╲     ◆     ╲     ◆   ",
    "  ╱ ╲   ╱ ◆   ╱ ╲   ╱ ◆   ╱ ╲  ",
    " ╱   ◆ ╱   ╲ ╱   ╲ ╱   ╲ ╱   ╲ ╱",
    "╲     ╲     ╲     ◆     ╲     ╲ ",
    " ╲   ╱ ╲   ╱ ╲   ╱ ╲   ╱ ╲   ╱ ╲",
)

#: Für mittlere Höhen die oberen sechs Zeilen, dort liegen fünf Rauten.
RASTER_KOMPAKT = RASTER[:6]

#: Die Kurzform. Der Firmenname allein, wenn kaum Platz ist.
KURZ = "◆ NEW AIR MEDIA GROUP"

#: Der obere Teil des Firmennamens, wie in der Vorlage.
NAME_OBEN = "NEW AIR"

#: Der untere Teil, in der Vorlage schmaler gesetzt.
NAME_UNTEN = "MEDIA GROUP"

#: Ab dieser Terminalhöhe kommt das volle Logo mit acht Zeilen.
HOCH = 28

#: Ab dieser Höhe das Gitter mit sechs Zeilen.
MITTEL = 21


def _mit_name(raster: tuple[str, ...]) -> str:
    """Setzt den Firmennamen an den rechten Rand des Gitters.

    Args:
        raster: Die Zeilen des Gitters.

    Returns:
        Der Text, Gitter links, Name rechts.
    """
    zeilen = [f"{raster[0]}  {NAME_OBEN:<10}", f"{raster[1]}  {NAME_UNTEN:<10}"]
    zeilen += list(raster[2:])
    return "\n".join(zeile.ljust(44) for zeile in zeilen)


def kopf_text(hoehe: int) -> str:
    """Baut den Logo-Kopf, abhängig von der Terminalhöhe.

    Auf einem hohen Terminal das ganze Gitter, auf einem mittleren ein
    Ausschnitt, sonst nur der Firmenname. Das Menü braucht neun Zeilen,
    deshalb wird dem Logo nicht mehr gegeben, als übrig bleibt.

    Args:
        hoehe: Die Höhe des Terminals in Zeilen.

    Returns:
        Der Text für den Kopf.
    """
    if hoehe >= HOCH:
        return _mit_name(RASTER)
    if hoehe >= MITTEL:
        return _mit_name(RASTER_KOMPAKT)
    return KURZ
