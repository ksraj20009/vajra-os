#!/bin/bash
set -e
echo "◆ Vajra OS Setup Wizard"
if [[ $EUID -ne 0 ]]; then exec sudo "$0" "$@"; fi
if command -v calamares &>/dev/null; then
    echo "Launching graphical installer..."
    calamares -d
else
    echo "Please install calamares: sudo apt install calamares"
    exit 1
fi
