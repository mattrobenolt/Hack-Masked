import subprocess, random, string, sys
from pathlib import Path
from fontTools.ttLib import TTFont

from tests.fixtures import tests

ROOT = Path(__file__).resolve().parent
OBEL = str(ROOT / "Obel/ttf/static/ObelMonoMasked-Regular.ttf")
HACK = str(ROOT / "build/HackMasked-Regular.ttf")

obel = TTFont(OBEL)
hack = TTFont(HACK)
ocmap = obel.getBestCmap(); hcmap = hack.getBestCmap()
oinv = {v:k for k,v in ocmap.items()}
hset = set(hack.getGlyphOrder())

def map_name(n):
    if n in hset: return n
    cp = oinv.get(n)
    if cp in hcmap: return hcmap[cp]
    return n

def shape(font, s):
    r = subprocess.run(["hb-shape", font, "--no-clusters", "--no-positions", "--", s],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr)
    out = r.stdout.strip()
    if out.startswith("[") and out.endswith("]"):
        return out[1:-1].split("|") if out != "[]" else []
    return []

tests = list(tests)

# fuzz around contexts
random.seed(1)
alphabet = string.ascii_letters + string.digits + "_-./+="
contexts = ["ghp_", "sk-ant-", "AKIA", "GITHUB_TOKEN=", "API_KEY=", "password", '"token": "', "--api-key=", "Authorization: Bearer "]
for c in contexts:
    for _ in range(40):
        tests.append(c + "".join(random.choice(alphabet) for _ in range(random.randint(0, 30))))

bad = 0
for s in tests:
    a = shape(OBEL, s)
    b = shape(HACK, s)
    am = [map_name(x) for x in a]
    if am != b:
        bad += 1
        print("DIFF", repr(s))
        print("  obel", am)
        print("  hack", b)
        if bad >= 20:
            break
print(f"{len(tests)} tests, {bad} differences")
