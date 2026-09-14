#!/bin/bash
export DISPLAY=:0
if command -v notify-send &>/dev/null; then
    notify-send -u normal -t 0 "Welcome to Vajra OS!" "India's Privacy-First, AI-Powered OS.\n\nType 'buddhi' in terminal for AI assistant\nSay 'Buddhi' for voice commands\nDouble-click Install Vajra OS to install"
fi
echo "◆ Welcome to Vajra OS 1.0 (वज्र OS)"
echo "  धर्मो रक्षति रक्षितः"
