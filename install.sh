#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

src="dist"
if ! compgen -G "$src/HackMasked-*.ttf" > /dev/null; then
  src="build"
fi
if ! compgen -G "$src/HackMasked-*.ttf" > /dev/null; then
  echo "No built fonts found. Run ./build.sh first." >&2
  exit 1
fi

case "$(uname -s)" in
  Darwin)
    dest="${HOME}/Library/Fonts"
    mkdir -p "$dest"
    cp "$src"/HackMasked-*.ttf "$dest/"
    ;;
  Linux)
    dest="${HOME}/.local/share/fonts/hack-masked"
    mkdir -p "$dest"
    cp "$src"/HackMasked-*.ttf "$dest/"
    fc-cache -f "$dest" >/dev/null 2>&1 || true
    ;;
  *)
    echo "Unsupported operating system: $(uname -s)" >&2
    exit 1
    ;;
esac

echo "Installed Hack Masked in ${dest}"
echo "Select 'Hack Masked' in the terminal or editor font menu."
