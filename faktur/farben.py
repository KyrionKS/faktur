"""Die Farben der App, an einer Stelle.

Es sind zwei Farben mit demselben Farbton, aber für zwei verschiedene
Untergründe. Das Original aus dem Logo ist `#512E80`. Auf Papier ist es
einwandfrei, im Terminal auf dunklem Grund dagegen unbrauchbar — 1.33:1
Kontrast, man sieht es kaum noch.

Darum gilt die Regel:

* ``DRUCK`` nur für die PDF. Dort ist der Untergrund weiß.
* ``AKZENT`` und ``SEKUNDAER`` nur für das Terminal.

Die Zahlen sind das WCAG-Kontrastverhältnis gegen einen dunklen Terminalgrund
(``#242f38``). Vier Komma fünf ist die Grenze für normalen Text, sieben für
Uberschriften.

    DRUCK      #512E80   10.23:1 auf Papier,  1.33:1 im Terminal
    AKZENT     #C9B5E3    7.28:1 im Terminal
    SEKUNDAER  #A88CD4    4.79:1 im Terminal

Wer die Terminalfarben dunkler macht, weil das Violett auf Papier so gut
aussah, zerstört die Lesbarkeit. Die beiden Welten getrennt zu halten ist
der ganze Witz dieser Datei.
"""

from __future__ import annotations

#: Die Akzentfarbe aus dem Logo. Nur für die PDF.
DRUCK = "#512E80"

#: Dieselbe Farbe, hell genug für ein dunkles Terminal. 7.28:1.
AKZENT = "#C9B5E3"

#: Etwas zurückhaltender, für Spaltenköpfe und Nummern. 4.79:1.
SEKUNDAER = "#A88CD4"

#: Der Rahmen um Eingabefelder. Eine Linie, dafür reicht 3:1. 3.22:1.
RAHMEN = "#8A76A5"

#: Der Fehlerton, kräftig genug gegen dunklen Grund. 5.48:1.
FEHLER = "#E88A8A"

#: Der Hinweiston, ruhiger als der Fehlerton. 6.96:1.
HINWEIS = "#A8C0A0"
