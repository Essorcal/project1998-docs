#!/usr/bin/env python3
"""Render the item-icon and mob sprite sheets for the database pages. LOCAL-ONLY: needs the 5.33
client's art (Item.epf/pal/tbl extracted into the game repo's re/, and Mon.dat in the client install),
which CI does not have — run this on a machine with the client and commit the four outputs:

    site/img/item-icons.png + item-icons.json      ({ItmIcon: [x, y]}, 24x24 cells)
    site/img/mob-sprites.png + mob-sprites.json    ({"look:0": [x, y, w, h]}, fit-48 cells)

Usage: python tools/local/render_sprites.py <game-repo> <client-dir>

Formats (all verified against the repo's own RE):
  Item.epf   TOC entry top,left(i16) pixOff,stencilOff(u32) — frame i's size is (left[i]-right[i-1]) x
             (top[i]-bottom[i-1]); frame N+1 == client item id N == ItmIcon N (re/render_items.py).
  MONSTER.DNA u32 count; per mob: u32 frameIndex, u8 chunkCount, u8 unk, u16 paletteIndex, then
             chunkCount * { u16 blockCount, blockCount * 9 bytes } (TKViewer DnaFileHandler).
  MONSTER.EPF u16 count,w,h, u16 pad, u32 tocOff; TOC 16B: top,left,bottom,right (i16), pix,sten (u32).
  *.pal      DLPalette blocks; Item.pal and Monster.pal colours both live at block+38 here.
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
    icons = sorted({int(r["ItmIcon"]) for r in csv.DictReader(io.open(os.path.join(GD, "Items.csv"), encoding="utf-8-sig"))
                    if r.get("ItmIcon", "").isdigit()})
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

    dna = open(os.path.join(RE, "monster.dna"), "rb").read()
    count, = struct.unpack_from("<I", dna, 0)
    pos, mobs = 4, []
    for _ in range(count):
        frame_index, = struct.unpack_from("<I", dna, pos)
        chunk_count = dna[pos + 4]
        palette, = struct.unpack_from("<H", dna, pos + 6)
        pos += 8
        for _c in range(chunk_count):
            block_count, = struct.unpack_from("<H", dna, pos)
            pos += 2 + block_count * 9
        mobs.append((frame_index, palette))

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

    # The rendered palette is the 0x07 COLOUR BYTE, not the DNA's palette field: mobs.csv MobLookColor
    # (4.95-tuned), overridden per look for the 5.33 client by game-data/Mob5xPalettes.csv — that file's
    # own header is the authority on this. Render one sprite per distinct (look, colour) pair in use.
    import csv
    def csvrows(name):
        lines = [l for l in io.open(os.path.join(GD, name), encoding="utf-8-sig") if not l.lstrip().startswith("#")]
        return list(csv.DictReader(lines))
    override = {int(r["Look"]): int(r["Palette"]) for r in csvrows("Mob5xPalettes.csv") if r.get("Look", "").isdigit()}
    pairs = sorted({(int(r["MobLook"]), int(r["MobLookColor"] or 0)) for r in csvrows("mobs.csv")
                    if r.get("MobLook", "").isdigit()})

    CELL, COLS = 48, 32
    rows = (len(pairs) + COLS - 1) // COLS
    sheet = Image.new("RGBA", (CELL * COLS, CELL * rows), (0, 0, 0, 0))
    coords, drawn = {}, 0
    for n, (look, color) in enumerate(pairs):
        if look >= len(mobs):
            continue
        res = frame(mobs[look][0])
        if not res:
            continue
        w, h, raw = res
        palidx = override.get(look, color)
        im = raw_to_rgba(w, h, raw, pals[palidx % len(pals)])
        if w > CELL or h > CELL:
            im.thumbnail((CELL, CELL), Image.NEAREST)
        x, y = (n % COLS) * CELL, (n // COLS) * CELL
        px, py = x + (CELL - im.width) // 2, y + (CELL - im.height) // 2
        sheet.paste(im, (px, py))
        coords[f"{look}:{color}"] = [px, py, im.width, im.height]
        drawn += 1
    sheet.save(os.path.join(IMG, "mob-sprites.png"), optimize=True)
    json.dump(coords, io.open(os.path.join(IMG, "mob-sprites.json"), "w", encoding="utf-8"), separators=(",", ":"))
    print(f"mob-sprites: {drawn}/{len(pairs)} (look,colour) pairs drawn from {len(pals)} palette blocks, sheet {sheet.size}")

if __name__ == "__main__":
    build_items()
    build_mobs()
