#!/bin/bash
# Paytience: double-click to start (macOS). First run installs everything.
cd "$(dirname "$0")"
python3 start.py
read -p "Press Enter to close..."
