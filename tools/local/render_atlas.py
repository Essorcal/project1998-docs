#!/usr/bin/env python3
"""Render every served map into web-ready WebP for the atlas page. LOCAL-ONLY (needs the 5.33 client's
Tile.dat). Runs the game repo's own re/render_maps.py (the pixel-identical renderer) into a temp dir,
then converts each PNG to site/img/maps/TK<id>.webp at a 12px/tile cap (longest side also capped at
1600) and writes site/img/maps/index.json = {id: [xs, ys, imgW, imgH]}.

Usage: python tools/local/render_atlas.py <game-repo> <client-dir> [--only ids]
"""
import csv, io, json, os, shutil, subprocess, sys, tempfile
from PIL import Image

GAME = sys.argv[1] if len(sys.argv) > 1 else r"C:\Repo\NexusTK"
CLIENT = sys.argv[2] if len(sys.argv) > 2 else os.path.expandvars(r"%LOCALAPPDATA%\Project1998\clients\533\local\0")
ONLY = None
if "--only" in sys.argv:
    ONLY = sys.argv[sys.argv.index("--only") + 1]
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "site", "img", "maps")
os.makedirs(OUT, exist_ok=True)

PX_PER_TILE_CAP = 12   # layout readability, half the native 24 — halves file sizes for mid maps
LONGEST_CAP = 1600
QUALITY = 80

def main():
    tmp = tempfile.mkdtemp(prefix="p1998-atlas-")
    try:
        cmd = [sys.executable, os.path.join(GAME, "re", "render_maps.py"), "all", tmp,
               "--data", os.path.join(CLIENT, "Tile.dat"), "--mapcells"]  # match the live map (door swaps, patched cells)
        if ONLY:
            cmd += ["--only", ONLY]
        print("rendering:", " ".join(cmd))
        subprocess.run(cmd, cwd=GAME, check=True)

        dims = {int(r["id"]): (int(r["xs"]), int(r["ys"]))
                for r in csv.DictReader(io.open(os.path.join(GAME, "game-data", "map_index.csv"),
                                                encoding="utf-8-sig"))}
        index, total = {}, 0
        full = os.path.join(tmp, "full")
        for fn in sorted(os.listdir(full)):
            if not fn.endswith(".png"):
                continue
            mid = int(fn[2:-4])
            xs, ys = dims.get(mid, (0, 0))
            im = Image.open(os.path.join(full, fn))
            cap = min(LONGEST_CAP, max(xs, ys) * PX_PER_TILE_CAP) or LONGEST_CAP
            if max(im.size) > cap:
                im.thumbnail((cap, cap), Image.LANCZOS)
            dest = os.path.join(OUT, f"TK{mid}.webp")
            im.save(dest, "WEBP", quality=QUALITY, method=4)
            index[mid] = [xs, ys, im.width, im.height]
            total += os.path.getsize(dest)
        json.dump(index, io.open(os.path.join(OUT, "index.json"), "w", encoding="utf-8"),
                  separators=(",", ":"))
        print(f"atlas: {len(index)} maps, {total / 1e6:.0f} MB -> {OUT}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

if __name__ == "__main__":
    main()
