#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

for style in Regular Bold Italic BoldItalic; do
  nix develop --command python3 build_masked.py --style "$style"
done
