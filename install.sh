#!/usr/bin/env bash
set -euo pipefail

if ! command -v apt-get >/dev/null 2>&1; then
  echo "This installer currently supports Debian-based systems such as Raspberry Pi OS."
  exit 1
fi

sudo apt-get update
sudo apt-get install -y tmux python3-psutil python3-rich

echo
echo "Dependencies installed."
echo "Launch the dashboard with:"
echo "  ./scripts/start-pi5cc"
