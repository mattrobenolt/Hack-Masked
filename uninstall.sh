#!/usr/bin/env bash
set -euo pipefail

case "$(uname -s)" in
  Darwin) dest="${HOME}/Library/Fonts" ;;
  Linux) dest="${HOME}/.local/share/fonts/hack-masked" ;;
  *) echo "Unsupported operating system: $(uname -s)" >&2; exit 1 ;;
esac

rm -f "$dest"/HackMasked-*.ttf
echo "Removed Hack Masked from ${dest}"
