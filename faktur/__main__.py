"""Faktur — Angebote und Rechnungen für die New Air Media Group.

An diesem Punkt startet das Programm. ``--version`` sagt, welche es ist,
ohne das Menü zu öffnen. Das ist die erste Frage, die man einem Programm
stellt, wenn es sich weigert zu starten.
"""

from __future__ import annotations

import sys

from faktur import __version__
from faktur.app import main


def _version_gewuenscht(argumente: list[str]) -> bool:
    """Entscheidet, ob nur die Version ausgegeben werden soll.

    Args:
        argumente: Die Argumente hinter dem Programmnamen.

    Returns:
        ``True``, wenn die Version verlangt wurde.
    """
    return any(argument in {"-V", "--version", "--Version"} for argument in argumente)


if __name__ == "__main__":
    if _version_gewuenscht(sys.argv[1:]):
        print(f"Faktur {__version__}")  # noqa: T201
    else:
        main()
