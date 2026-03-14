#!/usr/bin/env bash
# install.sh - Install Aion-dl dependencies and set up the application
set -euo pipefail

echo "==> Checking system dependencies..."

check_cmd() {
    command -v "$1" &>/dev/null && echo "  [OK] $1" || echo "  [MISSING] $1 — install it with your package manager"
}

check_cmd python3
check_cmd yt-dlp || echo "       → pip install yt-dlp  or  sudo pacman -S yt-dlp"

echo ""
echo "==> Checking Python GTK4 / Adwaita bindings..."

python3 -c "import gi; gi.require_version('Gtk','4.0'); from gi.repository import Gtk" \
    && echo "  [OK] PyGObject / GTK4" \
    || echo "  [MISSING] Install with: sudo pacman -S python-gobject  or  sudo apt install python3-gi"

python3 -c "import gi; gi.require_version('Adw','1'); from gi.repository import Adw" \
    && echo "  [OK] libadwaita" \
    || echo "  [MISSING] Install with: sudo pacman -S libadwaita  or  sudo apt install libadwaita-1-dev"

echo ""
echo "==> All checks done."
echo ""
echo "Run the application with:"
echo "  export PYTHONPATH=\$PYTHONPATH:\$(pwd)/src"
echo "  python3 -m aion_dl.main"
echo ""
echo "You can also pass a URL directly:"
echo "  python3 -m aion_dl.main 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'"
