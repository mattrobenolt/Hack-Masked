# Hack Masked

Hack 3.003 with the secret-masking OpenType rules from Obel Mono Masked 1.000.

Source: https://github.com/mattrobenolt/Hack-Masked

## Result

The font replaces a detected secret with a mask dot. Four characters after the
secret marker stay visible. The text buffer does not change. Copy and paste
returns the real secret. The mask is visual only.

`preview.png` shows the result.

## Install

From a clone:

1. Run `./install.sh`.
2. Open the font menu in the terminal or editor.
3. Select `Hack Masked`.

The family contains Regular, Bold, Italic, and Bold Italic. The four TTFs are
also in `dist/`. On macOS, double-click each file to install it.

## Use

Set `Hack Masked` as the font. Run this command:

```sh
printf 'GITHUB_TOKEN=xY7kQ2pLm9ZtR4vB\n'
```

The terminal shows `GITHUB_TOKEN=xY7k` followed by mask dots.

If iTerm2 does not apply the rules, enable `Use ligatures`. Some applications
disable OpenType layout when ligatures are off.

## How it works

A font can run a small program during shaping. Obel Mono Masked stores the
secret rules in the OpenType `ccmp` feature. The rules use chained contextual
substitutions with a backtrack context. A note glyph marks the start of a
secret. A second rule replaces each character after four visible characters
with a mask dot. Each dot depends on the glyphs behind it.

The build script does four steps:

1. It reads the `ccmp` closure from Obel Mono Masked. The closure has 108
   lookups and 700 glyph names.
2. It maps each Obel glyph name to the Hack glyph name for the same Unicode
   code point.
3. It adds 275 to 279 note glyphs to Hack. Each note glyph copies the outline
   of its visible base glyph. It also adds the 20 mask glyphs from Obel and
   scales them from 2000 to 2048 units per em.
4. It appends the lookups to the Hack GSUB table and registers a `ccmp`
   feature.

The script then renames the family to `Hack Masked`.

## Test

`compare.py` shapes 520 strings with HarfBuzz in both fonts and compares the
results. The current build reports 0 differences. `render.swift` draws the
installed font with CoreText. It produced `preview.png`.

## Rebuild

1. Run `./build.sh`.
2. Run `./install.sh`.

The build needs Nix. The flake supplies Python, fontTools, and HarfBuzz. The
`Hack/ttf` and `Obel/ttf` folders contain the input fonts.

## Limits

- The mask changes pixels only. It does not change the text buffer.
- An application that does not shape text shows the real characters.
  Alacritty is one example.
- A key that wraps to a second line shows on that line.
- The font does not protect against a process that reads the text.

## Licenses

The font files are distributed under the SIL Open Font License 1.1 because
they include the Obel Mono mask glyph and masking rules. The Hack components
remain under the MIT License and the Bitstream Vera License. The build scripts
are MIT licensed. See `LICENSE`, `Hack-LICENSE.md`, and `Obel-OFL.txt`.

Hack Masked is an unofficial modification. It is not affiliated with or
endorsed by Source Foundry or the Obel Mono Project.
