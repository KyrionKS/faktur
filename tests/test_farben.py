"""Prüft die Kontraste der Terminalfarben.

Der Grund ist einfach: Das Violett aus dem Logo ist auf Papier hervorragend
lesbar und im Terminal unbrauchbar. Wer die Farbe nicht nachrechnet, nimmt
irgendwann den schönen Wert vom Papier und das Menü wird unlesbar. Dieser
Test ist die Bremse dafür.
"""

from __future__ import annotations

import pytest
from faktur import farben

#: Der Hintergrund, auf dem die App läuft. Ein dunkles Terminal.
TERMINAL = "#242F38"

#: Der Hintergrund der PDF.
PAPIER = "#FFFFFF"


def _helligkeit(farbe: str) -> float:
    """Rechnet die relative Helligkeit einer Farbe aus.

    Args:
        farbe: Die Farbangabe als ``#RRGGBB``.

    Returns:
        Die Helligkeit zwischen 0 und 1.
    """
    werte = []
    for stelle in (0, 2, 4):
        anteil = int(farbe.lstrip("#")[stelle : stelle + 2], 16) / 255
        if anteil <= 0.04045:
            werte.append(anteil / 12.92)
        else:
            werte.append(((anteil + 0.055) / 1.055) ** 2.4)
    return 0.2126 * werte[0] + 0.7152 * werte[1] + 0.0722 * werte[2]


def _kontrast(a: str, b: str) -> float:
    """Rechnet das Kontrastverhältnis zweier Farben aus.

    Args:
        a: Die erste Farbe.
        b: Die zweite Farbe.

    Returns:
        Das Verhältnis. 1.0 bedeutet, dass man nichts unterscheidet.
    """
    hell = _helligkeit(a)
    dunkel = _helligkeit(b)
    return (max(hell, dunkel) + 0.05) / (min(hell, dunkel) + 0.05)


@pytest.mark.parametrize(
    ("name", "grenze"),
    [
        ("AKZENT", 4.5),
        ("SEKUNDAER", 4.5),
        ("FEHLER", 4.5),
        ("HINWEIS", 4.5),
        ("RAHMEN", 3.0),
    ],
)
def test_terminalfarben_sind_lesbar(name: str, grenze: float) -> None:
    """Jede Terminalfarbe ist gegen den dunklen Grund lesbar.

    Args:
        name: Der Name der Farbe in :mod:`faktur.farben`.
        grenze: Das Mindestverhältnis. 4.5 für Text, 3.0 für Linien.
    """
    wert = getattr(farben, name)
    assert _kontrast(wert, TERMINAL) >= grenze, (
        f"{name} ({wert}) hat nur "
        f"{_kontrast(wert, TERMINAL):.2f}:1 im Terminal, nötig sind {grenze}:1"
    )


def test_druckfarbe_ist_auf_papier_lesbar() -> None:
    """Das Violett aus dem Logo taugt für die PDF."""
    assert _kontrast(farben.DRUCK, PAPIER) >= 4.5


def test_druckfarbe_taugt_nicht_als_terminalfarbe() -> None:
    """Die Farbe fürs Papier darf nicht im Terminal landen.

    Das ist der Fehler, den dieser Test verhindert. Wer beide Welten
    vermischt, hat 1.33:1 und merkt es erst, wenn es zu spät ist.
    """
    assert _kontrast(farben.DRUCK, TERMINAL) < 4.5


def test_terminalfarben_sind_unterscheidbar() -> None:
    """Haupt- und Nebenton heben sich voneinander ab."""
    assert farben.AKZENT != farben.SEKUNDAER
    assert _kontrast(farben.AKZENT, farben.SEKUNDAER) > 1.5
