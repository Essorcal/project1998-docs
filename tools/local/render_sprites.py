#!/usr/bin/env python3
"""Render the item-icon and mob sprite sheets for the database pages. LOCAL-ONLY: needs the 5.33
client's art (Item.epf/pal/tbl extracted into the game repo's re/, and Mon.dat in the client install),
which CI does not have — run this on a machine with the client and commit the four outputs:

    site/img/item-icons.png + item-icons.json      ({ItmIcon: [x, y]}, 24x24 cells)
    site/img/mob-sprites.png + mob-sprites.json    ({"look:0": [x, y, w, h]}: 4 consecutive 48px
        cells per mob — standing pose facing front, left, back, right (rotation order, front first)
        — bottom-aligned; (x,y,w,h) frame the FRONT cell, the page animates x in −48 steps)

Usage: python tools/local/render_sprites.py <game-repo> <client-dir>

Formats (all verified against the repo's own RE):
  Item.epf   TOC entry top,left(i16) pixOff,stencilOff(u32) — frame i's size is (left[i]-right[i-1]) x
             (top[i]-bottom[i-1]); frame N+1 == client item id N == ItmIcon N (re/render_items.py).
  MONSTER.DNA u32 count; per mob: u32 frameIndex, u8 chunkCount, u8 unk, u16 paletteIndex, then
             chunkCount * { u16 blockCount, blockCount * 9 bytes } (TKViewer DnaFileHandler).
  MONSTER.EPF u16 count,w,h, u16 pad, u32 tocOff; TOC 16B: top,left,bottom,right (i16), pix,sten (u32).
  *.pal      DLPalette blocks; Item.pal and Monster.pal colours both live at block+38 here.
  SUPER0-6.PAL (NexusTK.dat) single-block palettes the 5.33 client uses for mob colour bytes >= 32
             (colour>>5 picks the file, see the ramp-shift note in build_mobs).
"""
import io, json, os, struct, sys
from PIL import Image

GAME = sys.argv[1] if len(sys.argv) > 1 else r"C:\Repo\NexusTK"
CLIENT = sys.argv[2] if len(sys.argv) > 2 else os.path.expandvars(r"%LOCALAPPDATA%\Project1998\clients\533\local\0")
RE = os.path.join(GAME, "re")
GD = os.path.join(GAME, "game-data")
IMG = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "site", "img")
os.makedirs(IMG, exist_ok=True)

# ---------------------------------------------------------------- PAK extraction (Nexon DAT)
def pak_entries(path):
    d = open(path, "rb").read()
    count, = struct.unpack_from("<I", d, 0)
    out = []
    prev = None
    for i in range(count):
        off, = struct.unpack_from("<I", d, 4 + i * 17)
        name = d[8 + i * 17:8 + i * 17 + 13].split(b"\0")[0].decode("latin1")
        if prev is not None:
            out.append((prev[1], off - prev[0], prev[0]))
        prev = (off, name)
    return {n.upper(): d[o:o + s] for n, s, o in out}

def ensure(fn, dat, entry):
    p = os.path.join(RE, fn)
    if not os.path.exists(p):
        blob = pak_entries(os.path.join(CLIENT, dat))[entry]
        open(p, "wb").write(blob)
        print(f"extracted {entry} -> re/{fn} ({len(blob)} bytes)")
    return p

def pal_blocks(path):
    d = open(path, "rb").read()
    offs, i = [], 0
    while True:
        j = d.find(b"DLPalette", i)
        if j < 0:
            break
        offs.append(j)
        i = j + 1
    blocks = []
    for k, off in enumerate(offs):
        end = offs[k + 1] if k + 1 < len(offs) else len(d)
        blk = d[off:end]
        # DLPalette header length VARIES between files (re/render_maps.py) — the 256 RGBA entries are
        # reliably the block's LAST 1024 bytes. A fixed +38 read tinted every later-block sprite.
        colors = blk[-1024:] if len(blk) >= 1024 else b"\0" * 1024
        blocks.append([tuple(colors[c * 4:c * 4 + 3]) for c in range(256)])
    return blocks

def raw_to_rgba(w, h, raw, pal):
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    px = im.load()
    for i in range(min(len(raw), w * h)):
        k = raw[i]
        if k:
            px[i % w, i // w] = (*pal[k], 255)
    return im

# ---------------------------------------------------------------- item icons
def build_items():
    epf = open(os.path.join(RE, "Item.epf"), "rb").read()
    blocks = pal_blocks(os.path.join(RE, "Item.pal"))
    tblpal = {}
    for line in io.open(os.path.join(RE, "Item.tbl"), encoding="latin1"):
        if line.startswith("ID "):
            parts = line.strip().rstrip(",").split(", ")
            idn = int(parts[0].split(" ")[1])
            for p in parts[1:]:
                k, _, v = p.rpartition(" ")
                if k.strip() == "Palette":
                    tblpal[idn] = int(v)

    fc, = struct.unpack_from("<H", epf, 0)
    toc, = struct.unpack_from("<I", epf, 8)

    def frame(fi):
        if fi < 1 or fi >= fc:
            return None
        top, left, pix, sten, _, _ = struct.unpack_from("<hhIIhh", epf, toc + fi * 16)
        _, _, _, _, pbot, pright = struct.unpack_from("<hhIIhh", epf, toc + (fi - 1) * 16)
        w, h = left - pright, top - pbot
        if w <= 0 or h <= 0 or w * h != sten - pix:
            return None
        return w, h, epf[12 + pix:12 + pix + w * h]

    import csv
    rws = [r for r in csv.DictReader(io.open(os.path.join(GD, "Items.csv"), encoding="utf-8-sig"))
           if r.get("ItmIcon", "").isdigit()]
    def n(r, k):
        try:
            return int(r.get(k) or 0)
        except ValueError:
            return 0
    # Mirror Content.ResolveIconColors: for the 4.95 colour runs, `icon + ItmIconColor` is a real separate
    # frame (sun/moon/star helms, the seasonal dress sets), unless it runs past the 4.95 art (1310 frames)
    # or lands on a frame some other row already claims as its own base icon. The page keys the sheet by
    # this FOLDED id (gen_db.py mirrors the same fold), so render the folded set — rendering base frames
    # only was the "everything is spring" bug on the docs page.
    RUNS = {89, 99, 120, 149, 159, 180, 265, 450}
    claimed = {n(r, "ItmIcon") for r in rws}
    def client_icon(r):
        ic, col = n(r, "ItmIcon"), n(r, "ItmIconColor")
        if col and ic in RUNS and ic + col < 1310 and ic + col not in claimed:
            return ic + col
        return ic
    icons = sorted({client_icon(r) for r in rws})
    CELL, COLS = 24, 64
    rows = (len(icons) + COLS - 1) // COLS
    sheet = Image.new("RGBA", (CELL * COLS, CELL * rows), (0, 0, 0, 0))
    coords, drawn = {}, 0
    for n, ic in enumerate(icons):
        res = frame(ic + 1)          # ItmIcon N -> Item.epf frame N+1
        if not res:
            continue
        w, h, raw = res
        im = raw_to_rgba(w, h, raw, blocks[tblpal.get(ic + 1, 0) % len(blocks)])
        if w > CELL or h > CELL:
            im.thumbnail((CELL, CELL), Image.NEAREST)
        x, y = (n % COLS) * CELL, (n // COLS) * CELL
        sheet.paste(im, (x + (CELL - im.width) // 2, y + (CELL - im.height) // 2))
        coords[ic] = [x, y]
        drawn += 1
    sheet.save(os.path.join(IMG, "item-icons.png"), optimize=True)
    json.dump(coords, io.open(os.path.join(IMG, "item-icons.json"), "w", encoding="utf-8"), separators=(",", ":"))
    print(f"item-icons: {drawn}/{len(icons)} icons drawn, sheet {sheet.size}")

# ---------------------------------------------------------------- mob sprites
def build_mobs():
    ensure("monster.dna", "Mon.dat", "MONSTER.DNA")
    ensure("monster.epf", "Mon.dat", "MONSTER.EPF")
    ensure("monster.pal", "Mon.dat", "MONSTER.PAL")
    for s in range(7):
        ensure(f"super{s}.pal", "NexusTK.dat", f"SUPER{s}.PAL")

    dna = open(os.path.join(RE, "monster.dna"), "rb").read()
    count, = struct.unpack_from("<I", dna, 0)
    pos, mobs = 4, []
    for _ in range(count):
        frame_index, = struct.unpack_from("<I", dna, pos)
        chunk_count = dna[pos + 4]
        palette, = struct.unpack_from("<H", dna, pos + 6)
        pos += 8
        chunks = []
        for _c in range(chunk_count):
            block_count, = struct.unpack_from("<H", dna, pos)
            pos += 2
            # block: u16 frame offset (relative to frame_index), u16 duration ms, rest flags
            chunks.append([struct.unpack_from("<H", dna, pos + b * 9)[0] for b in range(block_count)])
            pos += block_count * 9
        # chunks 1..4 hold the standing pose per direction: up(back), right, down(front), left —
        # offsets 0/3/6/9 of the 3-frames-per-direction walk block. Reorder to a rotation that
        # starts facing the camera: front, left, back, right (continuing the client's cyclic order).
        stand = [chunks[c][0] if c < len(chunks) and chunks[c] else 0 for c in (3, 4, 1, 2)]
        mobs.append((frame_index, palette, stand))

    epf = open(os.path.join(RE, "monster.epf"), "rb").read()
    fc, w0, h0 = struct.unpack_from("<HHH", epf, 0)
    toc = 12 + struct.unpack_from("<I", epf, 8)[0]

    def frame(fi):
        if fi < 0 or fi >= fc:
            return None
        top, left, bot, right, pix, sten = struct.unpack_from("<hhhhII", epf, toc + fi * 16)
        w, h = right - left, bot - top
        if w <= 0 or h <= 0 or sten - pix != w * h:
            return None
        return w, h, epf[12 + pix:12 + pix + w * h]

    pals = pal_blocks(os.path.join(RE, "monster.pal"))
    supers = [pal_blocks(os.path.join(RE, f"super{s}.pal"))[0] for s in range(7)]

    # The 0x07 colour byte is a RAMP SHIFT, not a palette-block index (RE'd from the 5.33 client:
    # draw 0x447975, palette manager 0x48ab40, blitter 0x4392a0). The client renders a mob as:
    #   s = colour >> 5; base = s == 0 ? MONSTER.PAL block[dna.paletteIndex % blockCount]
    #                               : SUPER{s-1}.PAL          (7 extra blocks in NexusTK.dat)
    #   pixel k stays put below 0x30 (outline/skin zone), else reads base[(k + 8*colour) & 0xFF]
    # — the 8-bit add wraps for free, so colour 35 lands on ramp 3 of SUPER0. The colour we shift by is
    # what the server actually sends a V533 client: mobs.csv MobLookColor remapped through
    # game-data/Mob5xPalettes.csv (mirrors Content.Palette5x / Session.SendCreatureList). The CSV is
    # keyed (Look, Colour) since Project1998 PR #16; the pre-PR per-Look shape (which collapsed every
    # look-17 horse to brown — a game-data bug the docs faithfully showed) still parses for old trees.
    # Render one sprite per distinct (look, colour) pair in use, keyed by the PRE-override pair.
    import csv
    def csvrows(name):
        lines = [l for l in io.open(os.path.join(GD, name), encoding="utf-8-sig") if not l.lstrip().startswith("#")]
        return list(csv.DictReader(lines))
    o_rows = [r for r in csvrows("Mob5xPalettes.csv") if r.get("Look", "").isdigit()]
    pair_keyed = any(r.get("Colour", "").isdigit() for r in o_rows)
    override = ({(int(r["Look"]), int(r["Colour"])): int(r["Palette"]) for r in o_rows if r.get("Colour", "").isdigit()}
                if pair_keyed else {int(r["Look"]): int(r["Palette"]) for r in o_rows})
    pairs = sorted({(int(r["MobLook"]), int(r["MobLookColor"] or 0)) for r in csvrows("mobs.csv")
                    if r.get("MobLook", "").isdigit()})

    def mob_rgba(look, colour, w, h, raw):
        # the byte a V533 client is actually sent
        sent = override.get((look, colour) if pair_keyed else look, colour)
        s = sent >> 5
        base = supers[s - 1] if 1 <= s <= 7 else pals[mobs[look][1] % len(pals)]
        shift = (sent * 8) & 0xFF
        im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        px = im.load()
        for i in range(min(len(raw), w * h)):
            k = raw[i]
            if k:
                e = k if k < 0x30 else (k + shift) & 0xFF
                px[i % w, i // w] = (*base[e], 255)
        return im

    CELL, DIRS, PAIRS_PER_ROW = 48, 4, 8
    rows = (len(pairs) + PAIRS_PER_ROW - 1) // PAIRS_PER_ROW
    sheet = Image.new("RGBA", (CELL * DIRS * PAIRS_PER_ROW, CELL * rows), (0, 0, 0, 0))
    coords, drawn = {}, 0
    for n, (look, color) in enumerate(pairs):
        if look >= len(mobs):
            continue
        base_fi, _, stand = mobs[look]
        # the four standing poses, front first; a bad frame falls back to the mob's base frame
        ims = []
        for off in stand:
            res = frame(base_fi + off) or frame(base_fi)
            if not res:
                break
            w, h, raw = res
            im = mob_rgba(look, color, w, h, raw)
            if im.width > CELL or im.height > CELL:
                im.thumbnail((CELL, CELL), Image.NEAREST)
            ims.append(im)
        if len(ims) < DIRS:
            continue
        x, y = (n % PAIRS_PER_ROW) * CELL * DIRS, (n // PAIRS_PER_ROW) * CELL
        hmax = max(im.height for im in ims)
        # bottom-aligned in each cell so the animation window ((x, y+CELL-hmax) 48xhmax, stepping
        # x by CELL) keeps every direction's feet on the same line
        for d, im in enumerate(ims):
            sheet.paste(im, (x + d * CELL + (CELL - im.width) // 2, y + CELL - im.height))
        coords[f"{look}:{color}"] = [x, y + CELL - hmax, CELL, hmax]
        drawn += 1
    sheet.save(os.path.join(IMG, "mob-sprites.png"), optimize=True)
    json.dump(coords, io.open(os.path.join(IMG, "mob-sprites.json"), "w", encoding="utf-8"), separators=(",", ":"))
    print(f"mob-sprites: {drawn}/{len(pairs)} (look,colour) pairs drawn from {len(pals)} palette blocks, sheet {sheet.size}")

if __name__ == "__main__":
    which = sys.argv[3] if len(sys.argv) > 3 else "all"
    if which in ("items", "all"):
        build_items()
    if which in ("mobs", "all"):
        build_mobs()
