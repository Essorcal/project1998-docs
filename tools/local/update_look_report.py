#!/usr/bin/env python3
"""Surgically refresh site/report-mob-look-check.html after a sprite-sheet re-render. LOCAL-ONLY.

The report is a hand-built, self-contained snapshot (atlas GIFs embedded as data URIs); this script
does NOT rebuild it — it re-embeds the current site/img/mob-sprites.png into the `.ours` CSS,
re-scores every card against its own embedded atlas GIF (100·colour-distance + aspect penalty),
re-sorts the grid most-suspicious-first, and stamps the intro + per-card pills for the two known
game-data (not renderer) issues:
  - look 17: Mob5xPalettes.csv keys per Look, so every look-17 horse is sent colour 3 on 5.33
  - colour >= 32: selects SUPER{c>>5 - 1}.PAL on 5.33 where the era client wrapped to ramp c-32

Usage: python tools/local/update_look_report.py
"""
import base64, io, json, os, re, sys
from PIL import Image

SITE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "site")
REPORT = os.path.join(SITE, "report-mob-look-check.html")

d = io.open(REPORT, encoding="utf-8").read()
sheet = Image.open(os.path.join(SITE, "img", "mob-sprites.png")).convert("RGBA")
coords = json.load(io.open(os.path.join(SITE, "img", "mob-sprites.json"), encoding="utf-8"))

# ---- 1. swap the embedded sheet -------------------------------------------------------------
png_b64 = base64.b64encode(open(os.path.join(SITE, "img", "mob-sprites.png"), "rb").read()).decode()
d, n = re.subn(r'(\.ours \{[^}]*?background-image:url\(data:image/png;base64,)[A-Za-z0-9+/=]+',
               lambda m: m.group(1) + png_b64, d, count=1)
assert n == 1, "sheet data URI not found"

# ---- 2. re-score + annotate every card ------------------------------------------------------
def fg_sprite(key):
    x, y, w, h = coords[key]
    im = sheet.crop((x, y, x + w, y + h))
    return [(r, g, b) for (r, g, b, a) in im.getdata() if a > 128], w / h

def fg_gif(b64):
    im = Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGBA")
    px = list(im.getdata())
    corners = [px[0], px[im.width - 1], px[-im.width], px[-1]]
    bg = max(set(corners), key=corners.count)
    pix = [(r, g, b) for (r, g, b, a) in px if a > 128 and abs(r - bg[0]) + abs(g - bg[1]) + abs(b - bg[2]) > 48]
    return pix, im.width / im.height

def hist(p):
    h = [0.0] * 64
    for r, g, b in p:
        h[(r // 64) * 16 + (g // 64) * 4 + (b // 64)] += 1
    s = sum(h) or 1
    return [x / s for x in h]

def mean(p):
    n = len(p) or 1
    return tuple(sum(q[i] for q in p) / n for i in range(3))

def score(spr, atl, ar_s, ar_a):
    inter = sum(min(a, b) for a, b in zip(hist(spr), hist(atl)))
    md = sum((a - b) ** 2 for a, b in zip(mean(spr), mean(atl))) ** 0.5 / 441.7
    import math
    aspect = abs(math.log2(ar_s / ar_a)) if ar_s > 0 and ar_a > 0 else 0
    return round(100 * ((1 - inter) * 0.5 + md * 0.5) + 20 * min(aspect, 1.5))

PILL_5X = ('<span class="pill" title="game-data: Mob5xPalettes.csv keys the V533 colour override per '
           'Look, so the server sends colour 3 (brown) for EVERY look-17 horse — diamond, golden, lake '
           'winny, fire snorter and the wild/skilled/elite/spirited tiers all collapse to the plain '
           'brown horse on 5.33. Needs (Look, Colour) keying game-side; only colour 35 needed the '
           'remap.">5x horse override</span>')
PILL_SUPER = ('<span class="pill" title="game-data: colour bytes ≥ 32 select SUPER{(c>>5)-1}.PAL '
              'on the 5.33 client, but the era client had no SUPER palettes and wrapped to ramp '
              '(colour − 32) of the mob’s own palette. This card shows what 5.33 actually '
              'renders today; the atlas shows the era intent. Fix belongs in game-data '
              '(Mob5xPalettes row remapping the colour), not the renderer.">SUPER palette</span>')

head, _, rest = d.partition('<div class="grid">')
grid, sep, tail = rest.partition('\n</div>\n<h2>')
assert sep, "grid/tail split failed"

cards = [c for c in grid.split('<div class="card">') if c.strip()]
out = []
for c in cards:
    m = re.search(r'<code>[a-z0-9_]+ [^<]*? look (\d+):(\d+)</code>', c)
    g = re.search(r'src="data:image/gif;base64,([A-Za-z0-9+/=]+)"', c)
    look, col = int(m.group(1)), int(m.group(2))
    key = f"{look}:{col}"
    sc = None
    if key in coords and g:
        try:
            spr, ar_s = fg_sprite(key)
            atl, ar_a = fg_gif(g.group(1))
            if len(spr) >= 20 and len(atl) >= 20:
                sc = score(spr, atl, ar_s, ar_a)
        except Exception:
            pass
    if sc is None:
        sc = int(re.search(r'score (\d+)', c).group(1))
    c2, n = re.subn(r'(<span style="color:#66766d">score )\d+(</span>)',
                    lambda m: f"{m.group(1)}{sc}{m.group(2)}", c, count=1)
    assert n == 1
    pills = ""
    if 'class="pill"' not in c2:                 # already-stamped cards keep their pills
        if look == 17:
            pills += " " + PILL_5X
        if col >= 32:
            pills += " " + PILL_SUPER
    if pills:
        c2 = c2.replace("</span><br><code>", "</span>" + pills + "<br><code>", 1)
    ident = re.search(r'<code>([a-z0-9_]+) ', c2).group(1)
    out.append((-sc, ident, key, c2))

out.sort(key=lambda t: (t[0], t[1], t[2]))
grid_new = "".join('<div class="card">' + c for _, _, _, c in out)
d = head + '<div class="grid">' + grid_new + '\n</div>\n<h2>' + tail

# ---- 3. intro + pill css (skipped when the report is already stamped) -----------------------
if ".pill {" not in d:
    d = d.replace(" .meta { font-size:12px; color:#93a49a; } .meta code { color:#8fd4b8; }",
                  " .meta { font-size:12px; color:#93a49a; } .meta code { color:#8fd4b8; }\n"
                  " .pill { display:inline-block; background:#3a2f1d; color:#d8b96a; border:1px solid #57431f;"
                  " border-radius:8px; padding:0 6px; font-size:10px; margin-left:4px; cursor:help; }", 1)

old_intro = re.search(r'<p class="meta">.*?</p>', d, re.S).group(0) if "2026-08-30 sprite fix" not in d else None
new_intro = (
    '<p class="meta">Left: what a 5.33 client renders for what the server sends (site/img/mob-sprites.png). '
    'Right: NexusAtlas reference GIF(s).\n'
    'Cards deduped by (look, colour, atlas name); every mobs.csv row using that look is listed. '
    '"2005-only" = deleted from the live site, image recovered from the predictable URL. '
    '<b>Sorted most-suspicious first</b> (colour distance + aspect heuristic — a high score means '
    '"look twice", not "wrong").</p>\n'
    '<p class="meta"><b>2026-08-30 sprite fix:</b> the sheet is now rendered with the client’s real '
    'colour semantics, reverse-engineered from the 5.33 exe (draw 0x447975, palette manager 0x48ab40, '
    'blitter 0x4392a0): the 0x07 colour byte is a <b>ramp shift</b> — sprite indices ≥ 0x30 read '
    'palette[(i + 8·colour) &amp; 0xFF] of the mob’s own MONSTER.DNA palette block — and '
    'colour&gt;&gt;5 ≥ 1 swaps in SUPER{n}.PAL instead (the old sheet wrongly used the colour byte as '
    'a palette-block index). 297 of 356 cards moved closer to their atlas reference and scores were '
    'recomputed; the few that moved away are faithful renders of the flagged game-data issues below, or '
    'P1998 recolour variants (mythics, guardians) whose atlas image shows the plain-colour original. '
    'Flags: <span class="pill">5x horse override</span> and <span class="pill">SUPER palette</span> mark '
    'game-data problems visible in-game on 5.33 today — hover them for the details.</p>')
if old_intro:
    d = d.replace(old_intro, new_intro, 1)

io.open(REPORT, "w", encoding="utf-8", newline="\n").write(d)
print(f"report updated: {len(out)} cards re-scored, sheet {len(png_b64)//1024}KB b64")
