"""Einstiegspunkt für den gebauten Programm.

Aus dem Quelltext startet das Programm mit ``python -m faktur``. Ein gebautes
Programm braucht eine Datei, die man dem Packer geben kann — das ist diese.

Sie macht nichts weiter, als die App zu starten. Alles andere liegt in
:mod:`faktur.app`.
"""

from __future__ import annotations

from faktur.app import main

if __name__ == "__main__":
    main()
