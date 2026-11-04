import argparse, copy, sys
from collections import deque
from pathlib import Path
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables import otTables as ot
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.misc.transform import Transform
from fontTools.ttLib.tables._g_l_y_f import Glyph

ROOT = Path(__file__).resolve().parent
OBEL_DIR = str(ROOT / "Obel/ttf")
HACK_DIR = str(ROOT / "Hack/ttf")

def walk(obj, seen=None):
    if seen is None:
        seen = set()
    if id(obj) in seen:
        return
    seen.add(id(obj))
    yield obj
    if isinstance(obj, (list, tuple)):
        for x in obj:
            yield from walk(x, seen)
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from walk(k, seen)
            yield from walk(v, seen)
    elif hasattr(obj, "__dict__"):
        for v in vars(obj).values():
            yield from walk(v, seen)

def ccmp_closure(g):
    feature = next(fr.Feature for fr in g.FeatureList.FeatureRecord if fr.FeatureTag == "ccmp")
    q = deque(feature.LookupListIndex)
    seen = set()
    while q:
        i = q.popleft()
        if i in seen:
            continue
        seen.add(i)
        lookup = g.LookupList.Lookup[i]
        for st in lookup.SubTable:
            for obj in walk(st):
                if isinstance(obj, ot.SubstLookupRecord):
                    q.append(obj.LookupListIndex)
    return sorted(seen)

def replace_names(obj, mapping):
    if isinstance(obj, str):
        return mapping.get(obj, obj)
    if isinstance(obj, list):
        return [replace_names(x, mapping) for x in obj]
    if isinstance(obj, tuple):
        return tuple(replace_names(x, mapping) for x in obj)
    if isinstance(obj, dict):
        return {replace_names(k, mapping): replace_names(v, mapping) for k, v in obj.items()}
    if hasattr(obj, "__dict__") and not isinstance(obj, (bytes, bytearray)):
        for k, v in list(vars(obj).items()):
            setattr(obj, k, replace_names(v, mapping))
        return obj
    return obj

def remap_lookups(obj, idxmap, offset):
    for o in walk(obj):
        if isinstance(o, ot.SubstLookupRecord):
            if o.LookupListIndex not in idxmap:
                raise RuntimeError(f"nested lookup {o.LookupListIndex} not in closure")
            o.LookupListIndex = offset + idxmap[o.LookupListIndex]

def all_referenced_strings(obj, glyphset):
    out = set()
    for o in walk(obj):
        if isinstance(o, str) and o in glyphset:
            out.add(o)
    return out

def unicode_name(cp):
    return f"uni{cp:04X}" if cp <= 0xFFFF else f"u{cp:05X}"

def resolve_base(name, obel_inv, hack_cmap):
    """Find the visible base glyph name for a note/derived glyph."""
    n = name
    if ".ductus" in n:
        n = n.split(".ductus")[0]
    for marker in (".sec", ".mask"):
        if marker in n:
            n = n.split(marker)[0]
    while n and n not in obel_inv and "." in n:
        n = n.rsplit(".", 1)[0]
    if n == ".notdef":
        return ".notdef"
    cp = obel_inv.get(n)
    if cp is not None:
        return hack_cmap.get(cp)
    return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--style", default="Regular")
    ap.add_argument("--out", default=None)
    ap.add_argument("--no-rename", action="store_true")
    args = ap.parse_args()

    style = args.style
    obel_path = f"{OBEL_DIR}/static/ObelMonoMasked-{style}.ttf"
    hack_path = f"{HACK_DIR}/Hack-{style}.ttf"
    out = args.out or f"build/HackMasked-{style}.ttf"

    obel = TTFont(obel_path)
    hack = TTFont(hack_path)

    hack_order = list(hack.getGlyphOrder())
    hack.setGlyphOrder(hack_order)
    hack["glyf"].glyphOrder = hack_order
    hack_glyphset = set(hack_order)
    hack_cmap = hack.getBestCmap()
    obel_cmap = obel.getBestCmap()
    obel_inv = {v: k for k, v in obel_cmap.items()}
    obel_glyphset = set(obel.getGlyphOrder())

    og = obel["GSUB"].table
    ccmp_feature = next(fr.Feature for fr in og.FeatureList.FeatureRecord if fr.FeatureTag == "ccmp")
    top_ids = list(ccmp_feature.LookupListIndex)
    lookup_ids = ccmp_closure(og)
    print(f"ccmp closure: {len(lookup_ids)} lookups")

    src_lookups = [copy.deepcopy(og.LookupList.Lookup[i]) for i in lookup_ids]
    idxmap = {old: i for i, old in enumerate(lookup_ids)}

    # glyph names referenced by the copied lookups
    refs = set()
    for l in src_lookups:
        refs |= all_referenced_strings(l, obel_glyphset)
    print(f"glyph names referenced: {len(refs)}")

    mapping = {}
    missing_encoded = []
    specials = []
    for name in sorted(refs):
        if name in hack_glyphset:
            mapping[name] = name
        else:
            cp = obel_inv.get(name)
            if cp is not None and cp in hack_cmap:
                mapping[name] = hack_cmap[cp]
            elif cp is not None:
                new = unicode_name(cp)
                mapping[name] = new
                if new not in hack_glyphset:
                    missing_encoded.append((name, new))
            else:
                mapping[name] = name
                specials.append(name)

    print(f"mapped to existing Hack glyph: {sum(1 for n in refs if mapping[n] in hack_glyphset)}")
    print(f"encoded but missing from Hack: {len(missing_encoded)} -> {missing_encoded}")
    print(f"special glyphs to add: {len(specials)}")

    # sanity: no special name collides with Hack
    for n in specials:
        if n in hack_glyphset:
            print("COLLISION", n, file=sys.stderr)
            sys.exit(1)

    # add empty glyphs for encoded names Hack lacks
    glyf = hack["glyf"]
    hmtx = hack["hmtx"]
    default_width = hmtx["uni0020"][0]
    for old, new in missing_encoded:
        if new in hack_glyphset:
            continue
        g = Glyph()
        g.numberOfContours = 0
        g.recalcBounds(glyf)
        glyf[new] = g
        hmtx[new] = (0, 0)
        hack_glyphset.add(new)
    hack.setGlyphOrder(glyf.glyphOrder)

    # dot from the matching Obel style
    obel_gs = obel.getGlyphSet()
    dot_glyph = obel_gs["secret.mask.alnum"]
    from fontTools.pens.boundsPen import BoundsPen
    bp = BoundsPen(obel_gs)
    dot_glyph.draw(bp)
    xmin, ymin, xmax, ymax = bp.bounds
    scale = hack["head"].unitsPerEm / obel["head"].unitsPerEm
    dx = default_width / 2 - ((xmin + xmax) / 2) * scale
    rec = DecomposingRecordingPen(obel_gs)
    dot_glyph.draw(rec)
    pen = TTGlyphPen(None)
    rec.replay(TransformPen(pen, Transform(scale, 0, 0, scale, dx, 0)))
    dot = pen.glyph()
    dot.recalcBounds(glyf)
    print(f"dot: obel bbox {bp.bounds} scale {scale:.4f} dx {dx:.1f} width {default_width}")

    # add specials
    added = 0
    for name in specials:
        if name.startswith("secret.mask"):
            glyf[name] = copy.deepcopy(dot)
            hmtx[name] = (default_width, dot.xMin)
        else:
            base = resolve_base(name, obel_inv, hack_cmap)
            if base is None or base not in glyf:
                # empty placeholder
                g = Glyph(); g.numberOfContours = 0
                g.recalcBounds(glyf)
                glyf[name] = g
                hmtx[name] = (0, 0)
                print(f"  WARN no base for {name}, empty")
            else:
                glyf[name] = copy.deepcopy(glyf[base])
                hmtx[name] = hmtx[base]
        hack_glyphset.add(name)
        added += 1
    hack.setGlyphOrder(glyf.glyphOrder)
    print(f"added {added} special glyphs")

    # rename and remap copied lookups
    base_lookup_count = len(hack["GSUB"].table.LookupList.Lookup)
    for l in src_lookups:
        replace_names(l, mapping)
        remap_lookups(l, idxmap, base_lookup_count)

    # Coverage tables must be sorted by glyph id
    glyph_id = {n: i for i, n in enumerate(hack.getGlyphOrder())}
    for l in src_lookups:
        for o in walk(l):
            if isinstance(o, ot.Coverage):
                o.glyphs.sort(key=lambda n: glyph_id[n])

    # verify all references resolve
    unresolved = set()
    for l in src_lookups:
        for o in walk(l):
            if isinstance(o, str) and o not in hack_glyphset:
                # strings that are not glyph names (tags) are ignored below
                if o in mapping.values() or o in obel_glyphset or "." in o or o.startswith("secret"):
                    unresolved.add(o)
    if unresolved:
        print("UNRESOLVED", sorted(unresolved), file=sys.stderr)
        sys.exit(1)

    # install lookups
    hg = hack["GSUB"].table
    hg.LookupList.Lookup.extend(src_lookups)
    hg.LookupList.LookupCount = len(hg.LookupList.Lookup)
    new_indices = [base_lookup_count + idxmap[i] for i in top_ids]

    # install feature
    feature = ot.Feature()
    feature.FeatureTag = "ccmp"
    feature.LookupListIndex = new_indices
    feature.FeatureParams = None
    record = ot.FeatureRecord()
    record.FeatureTag = "ccmp"
    record.Feature = feature
    feature_index = len(hg.FeatureList.FeatureRecord)
    hg.FeatureList.FeatureRecord.append(record)
    hg.FeatureList.FeatureCount = len(hg.FeatureList.FeatureRecord)

    # register feature in every default langsys and explicit langsys
    for sr in hg.ScriptList.ScriptRecord:
        if sr.Script.DefaultLangSys is not None:
            sr.Script.DefaultLangSys.FeatureIndex.append(feature_index)
            sr.Script.DefaultLangSys.FeatureCount = len(sr.Script.DefaultLangSys.FeatureIndex)
        for lr in sr.Script.LangSysRecord:
            lr.LangSys.FeatureIndex.append(feature_index)
            lr.LangSys.FeatureCount = len(lr.LangSys.FeatureIndex)

    # maxp / DSIG
    hack["maxp"].numGlyphs = len(hack_order)
    try:
        hack["maxp"].recalc(hack)
    except Exception as e:
        print("maxp recalc skipped:", e)
    if "DSIG" in hack:
        del hack["DSIG"]

    if not args.no_rename:
        # family naming
        names = hack["name"]
        style_name = {"Regular": "Regular", "Bold": "Bold", "Italic": "Italic", "BoldItalic": "Bold Italic"}[style]
        ps_style = {"Regular": "Regular", "Bold": "Bold", "Italic": "Italic", "BoldItalic": "BoldItalic"}[style]
        family = "Hack Masked"
        ofl_text = (ROOT / "Obel-OFL.txt").read_text(encoding="utf-8")
        for rec in names.names:
            if rec.nameID == 1:
                rec.string = family
            elif rec.nameID == 4:
                rec.string = f"{family} {style_name}"
            elif rec.nameID == 6:
                rec.string = f"HackMasked-{ps_style}"
            elif rec.nameID == 16:
                rec.string = family
            elif rec.nameID == 17:
                rec.string = style_name
            elif rec.nameID == 0:
                rec.string = ("Copyright (c) 2018 Source Foundry Authors / "
                              "Copyright (c) 2003 by Bitstream, Inc. All Rights Reserved. / "
                              "Copyright (c) 2026 The Obel Mono Project Authors.")
            elif rec.nameID == 3:
                rec.string = "Hack Masked 3.003; 2026; SIL Open Font License 1.1"
            elif rec.nameID == 8:
                rec.string = "Hack Masked contributors"
            elif rec.nameID == 9:
                rec.string = ("Hack: Source Foundry Authors; "
                              "Mask: The Obel Mono Project Authors")
            elif rec.nameID == 13:
                text = rec.toUnicode()
                if "SIL OPEN FONT LICENSE" not in text:
                    rec.string = text.rstrip() + "\n\n" + ofl_text
            elif rec.nameID == 14:
                rec.string = "https://github.com/mattrobenolt/Hack-Masked/blob/main/LICENSE"

    hack.save(out)
    print("wrote", out)

if __name__ == "__main__":
    main()
