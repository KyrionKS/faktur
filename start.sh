#!/usr/bin/env sh
# Startet Faktur. Alles andere steht in start.py, weil man es dort prüfen
# kann und in einer Schale nicht.
#
#     ./start.sh
#
# Beim ersten Mal wird die Umgebung angelegt und die Bibliotheken werden
# geholt. Das dauert eine Minute. Danach geht es sofort los.

set -e

# Ohne das findet das Skript sich selbst nicht, wenn es über einen anderen
# Weg aufgerufen wird.
PFAD=$(dirname -- "$0")
cd -- "$PFAD"

if ! command -v python3 > /dev/null 2>&1; then
    echo "Es gibt kein python3 auf diesem Rechner." >&2
    echo "" >&2
    echo "macOS:  brew install python@3.12" >&2
    echo "Ubuntu: sudo apt install python3-venv" >&2
    exit 1
fi

# exec, damit das Terminal nach dem Beenden nicht voller Rauschen ist und
# Strg+C direkt im Programm ankommt.
exec python3 start.py "$@"
