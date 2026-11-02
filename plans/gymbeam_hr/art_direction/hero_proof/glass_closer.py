"""Zero-cost: move the reconstructed glass (candidate_G) closer to the pouch by SHIFT gen px (18 = 12 final px). Writes candidate_G_closer.png; then
glass_edit.assemble() is run on it (real pouch laid back, headline). Glass pixels move per row from the glass's own left edge; the vacated frame-edge
strip is filled with the glass's mirrored texture; the gap side keeps the real dark backdrop/slate; 10 px feather at the new edge."""
import importlib.util, sys
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw, ImageFilter
ROOT = Path(__file__).resolve().parents[4]
spec = importlib.util.spec_from_file_location("ge", Path(__file__).with_name("glass_edit.py")); ge = importlib.util.module_from_spec(spec); spec.loader.exec_module(ge)
RUN = ge.RUN; SHIFT = 18; GW, GH = ge.GW, ge.GH
g = Image.open(RUN / "candidate_G.png").convert("RGB"); L = g.convert("L"); px = L.load()
edge = {}
for y in range(540, 1560):
    e = None
    for x in range(1345, 1450):
        if sum(px[x + i, y] for i in range(6)) / 6 > 42 and max(px[x + i, y] for i in range(6)) > 60:
            e = x; break
    edge[y] = e if e else 1380
ys = sorted(edge); sm = {y: sorted(edge[k] for k in ys[max(0, ys.index(y) - 25):ys.index(y) + 26])[len(ys[max(0, ys.index(y) - 25):ys.index(y) + 26]) // 2] for y in ys}
out = g.copy(); op = out.load(); gp = g.load()
F = 10
def row(y, e):
    for x in range(e - SHIFT - F, GW):
        sx = x + SHIFT
        src = gp[sx, y] if sx < GW else gp[2 * GW - 2 - sx, y]            # mirror at the frame edge
        if x < e - SHIFT:                                                 # feather
            a = (x - (e - SHIFT - F)) / F; d = gp[x, y]; src = tuple(int(src[k] * a + d[k] * (1 - a)) for k in range(3))
        op[x, y] = src
for y in range(500, GH):
    e = sm[y] if y in sm else (sm[1559] if y >= 1560 else sm[540])
    if y < 530: continue
    row(y, e if y < 1560 else e)
out.save(RUN / "candidate_G_closer.png"); print("written; edge sample", sm[600], sm[1000], sm[1500])
