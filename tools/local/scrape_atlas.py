#!/usr/bin/env python3
"""Scrape the live NexusAtlas weapon/armor/item category pages into tools/data/atlas_items.csv.

LOCAL-ONLY, run once (like render_sprites.py): CI never touches the network — the generator merely
reads the committed CSV. Re-run only to refresh the snapshot.

    python tools/local/scrape_atlas.py            # fetch (cached) + parse + write CSV + match report
    python tools/local/scrape_atlas.py --gifs     # also download icon gifs for matched items that
                                                  # lack client art, and build site/img/item-icons-atlas.png/.json

Page anatomy (same markup the game repo's re/atlas_special_info.py mined from the 2023 mirror, verified
against the live site 2026-08-30): each item is one <table width="98%">; the name sits in <b> inside a
bgcolor="#B1300D" header cell; the first photo/... <img> is the item's ground/icon gif; "Special Info",
"How to Obtain" and "Detailed Information" follow as free text.

The live Atlas reflects MODERN NexusTK (a superset of the 4.95 era), so: absent from the Atlas =>
likely an RTK/private-server invention; present does NOT imply era-correct. The per-section Extinct
pages are included — an extinct item is by definition old, which is era evidence in itself.

Politeness: sequential fetches, 2s apart, cached on disk so re-runs never refetch.
"""
import csv, io, json, os, re, sys, time, urllib.request

DOCS = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(DOCS, "tools", "data", "atlas_items.csv")
CACHE = os.environ.get("ATLAS_CACHE") or os.path.join(
    os.environ.get("LOCALAPPDATA", "."), "Project1998", "atlas_cache")
GAME = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else r"C:\Repo\NexusTK"

BASE = "https://www.nexusatlas.com"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) p1998-docs-crossref"}

# Category pages per section, from each section's own index.php nav (fetched 2026-08-30).
PAGES = {
    "weapons": ["axes", "bows", "carnageprize", "clubs", "enchanted", "extinct", "fans", "spears", "swords"],
    "armor": ["magearmor", "poetarmor", "roguearmor", "warriorarmor", "peasantarmor", "handitems",
              "headitems", "shields", "coataccessory", "subaccessory", "extinct",
              "vortexarmor", "vortexhand", "vortexitems"],
    "items": ["arrows", "bombs", "crafts", "drops", "events", "keys", "mana", "potions", "quests",
              "rocks", "scrolls", "shop", "spells", "vita", "woodlandsitems", "extinct", "other"],
}

def fetch(section, page):
    os.makedirs(CACHE, exist_ok=True)
    p = os.path.join(CACHE, f"{section}_{page}.html")
    if not os.path.exists(p):
        url = f"{BASE}/{section}/{page}.php"
        req = urllib.request.Request(url, headers=UA)
        data = urllib.request.urlopen(req, timeout=30).read()
        open(p, "wb").write(data)
        print(f"fetched {url} ({len(data):,} bytes)")
        time.sleep(2)
    return io.open(p, encoding="latin1").read()

def flat(h):
    h = re.sub(r"<(script|style).*?</\1>", " ", h, flags=re.S | re.I)
    h = re.sub(r"<br\s*/?>", " \n", h, flags=re.I)
    h = re.sub(r"<[^>]+>", " ", h)
    for a, b in (("&nbsp;", " "), ("&amp;", "&"), ("&quot;", '"'), ("&#039;", "'"), ("&#39;", "'")):
        h = h.replace(a, b)
    return re.sub(r"[ \t]+", " ", h)

_TAIL = (r"(?:Detailed Info|How to Obtain|Casts|NPC Sells|NPC Buys|Market Pri|Merchant sugg|Price NPC"
         r"|Comments|Shop prices|Effect|Crafts|Other Uses|$)")

def _rec(section, page, name, gif, text):
    def field(label):
        f = re.search(label + r"\s*[:\-]?\s*(.*?)" + _TAIL, text, flags=re.S | re.I)
        return re.sub(r"\s+", " ", f.group(1)).strip()[:200] if f else ""
    return {
        "name": name, "section": section, "category": page,
        "extinct": "1" if page == "extinct" else "0",
        "gif": (gif or "").lstrip("/"),
        "special": field(r"Special Info"),
        "obtain": field(r"How to Obtain") or field(r"Where to Obtain"),
    }

def parse(html, section, page):
    """The Atlas has three page layouts; try each and keep the best yield.
    A) weapons/armor + items/crafts: one <table width="98%"> per item, name <b> in a #B1300D cell;
    B) most of the items section: ONE table for the whole page, one #B1300D name cell per item;
    C) items/woodlandsitems: bordered 98% tables, one row per item, name = first <b>, no #B1300D."""
    def named_chunks(chunks):
        out = []
        for blk in chunks:
            m = re.search(r'bgcolor="#B1300D".*?<b>\s*(.*?)\s*</b>', blk, flags=re.S | re.I)
            if m:
                out.append((m.group(1), blk))
        return out

    cands = [named_chunks(re.split(r'(?=<table width="9[78]%")', html)),
             named_chunks(re.split(r'(?=<td[^>]*bgcolor="#B1300D")', html))]
    rows_c = []
    for blk in re.split(r'(?=<table width="9[78]%"[^>]*border="1")', html)[1:]:
        m = re.search(r"<b>\s*(.*?)\s*</b>", blk, flags=re.S | re.I)
        if m:
            rows_c.append((m.group(1), blk))
    cands.append(rows_c)

    best = max(cands, key=len)
    out = []
    for raw_name, blk in best:
        name = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", raw_name)).strip()
        if not name or len(name) > 60 or name.lower() in ("name", "image", "information"):
            continue
        gif = re.search(r'src="(?:https?://www\.nexusatlas\.com)?(/?photo/[^"]+)"', blk, re.I)
        out.append(_rec(section, page, name, gif.group(1) if gif else "", flat(blk)))
    return out

# Name matching \u2014 a COPY of gen_db.py's _atlas_norm/_atlas_folds (edit both). Known one-word typos on
# either side, then successively looser folds tried level-for-level, strictest first.
_NAME_FIX = {"serpant": "serpent", "simitar": "scimitar", "conjuror": "conjurer",
             "pwdrd": "powdered", "dreses": "dress", "roast": "roasted"}

def norm(s):
    s = (s or "").lower().replace("\u2019", "'").replace("\\'", "'").replace("\\", "")
    s = re.sub(r"'s\b", "s", s)
    s = re.sub(r"[^a-z0-9]+", " ", s).strip()
    return " ".join(_NAME_FIX.get(w, w) for w in s.split())

def folds(s):
    l1 = norm(s)
    l3 = " ".join(w[:-1] if w.endswith("s") and len(w) > 3 else w for w in l1.split())
    return [l1, l1.replace(" ", ""), l3, l3.replace(" ", "")]

def scrape():
    recs = []
    for section, pages in PAGES.items():
        for page in pages:
            rows = parse(fetch(section, page), section, page)
            print(f"{section}/{page}: {len(rows)} items")
            recs += rows
    # One row per (normalized name); keep every page it appears on, first gif wins, longest special wins.
    merged = {}
    for r in sorted(recs, key=lambda r: (r["section"], r["category"], r["name"].lower())):
        k = norm(r["name"])
        if k not in merged:
            merged[k] = dict(r, pages=f"{r['section']}/{r['category']}")
        else:
            m = merged[k]
            m["pages"] += f"|{r['section']}/{r['category']}"
            m["extinct"] = "1" if (m["extinct"] == "1" or r["extinct"] == "1") else "0"
            if len(r["special"]) > len(m["special"]):
                m["special"] = r["special"]
            if not m["gif"]:
                m["gif"] = r["gif"]
    rows = sorted(merged.values(), key=lambda r: r["name"].lower())
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, ["name", "pages", "extinct", "gif", "special", "obtain"],
                           extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"\nwrote {OUT}: {len(rows)} distinct items from {sum(len(p) for p in PAGES.values())} pages")
    return rows

def registry_items():
    lines = [l for l in io.open(os.path.join(GAME, "game-data", "Items.csv"), encoding="utf-8-sig")
             if not l.lstrip().startswith("#")]
    return [(r["ItmIdentifier"], r["ItmDescription"].replace("\\", ""))
            for r in csv.DictReader(lines)
            if r["ItmIdentifier"] and not r["ItmIdentifier"].startswith("=")]

def match_all(atlas_rows):
    """(matched {key: atlas row}, unmatched [(key, name)]) via the fold ladder."""
    idx = {}
    for a in atlas_rows:
        for i, f in enumerate(folds(a["name"])):
            idx.setdefault((i, f), a)
    matched, unmatched = {}, []
    for k, n in registry_items():
        hit = next((idx[(i, f)] for i, f in enumerate(folds(n)) if (i, f) in idx), None)
        if hit is not None:
            matched[k] = hit
        else:
            unmatched.append((k, n))
    return matched, unmatched

def report(atlas_rows):
    """Match rate against the registry, both directions."""
    matched, unmatched = match_all(atlas_rows)
    total = len(matched) + len(unmatched)
    reg_folds = {f for _, n in registry_items() for f in folds(n)}
    atlas_only = sorted(a["name"] for a in atlas_rows if not any(f in reg_folds for f in folds(a["name"])))
    print(f"\nregistry items matched on the Atlas: {len(matched)}/{total} ({100 * len(matched) / total:.1f}%)")
    print(f"registry items NOT on the Atlas (likely RTK-added): {len(unmatched)}")
    print(f"Atlas items NOT in the registry: {len(atlas_only)}")
    rep = os.path.join(CACHE, "match_report.json")
    json.dump({"matched": len(matched), "total": total,
               "unmatched_registry": unmatched, "atlas_only": atlas_only},
              io.open(rep, "w", encoding="utf-8"), indent=1)
    print(f"full lists -> {rep}")

def build_gif_sheet(atlas_rows):
    """Download every matched item's Atlas icon gif (cached) and pack a 24x24 sprite sheet keyed by
    registry ITEM KEY -> site/img/item-icons-atlas.png/.json. The page uses it only where the client
    sheet has no frame."""
    from PIL import Image
    matched, _ = match_all(atlas_rows)
    pairs = sorted((k, a["gif"]) for k, a in matched.items() if a.get("gif"))
    gdir = os.path.join(CACHE, "gifs")
    os.makedirs(gdir, exist_ok=True)
    fetched = 0
    for _, gif in sorted({(os.path.basename(g), g) for _, g in pairs}):
        p = os.path.join(gdir, gif.replace("/", "_"))
        if os.path.exists(p):
            continue
        try:
            req = urllib.request.Request(f"{BASE}/{gif}", headers=UA)
            open(p, "wb").write(urllib.request.urlopen(req, timeout=30).read())
            fetched += 1
            time.sleep(0.5)
        except Exception as e:
            print(f"  gif fetch failed {gif}: {e}")
    print(f"gifs: {len(pairs)} matched items with art, {fetched} newly fetched")

    CELL, COLS = 24, 64
    rows_n = (len(pairs) + COLS - 1) // COLS
    sheet = Image.new("RGBA", (CELL * COLS, CELL * max(1, rows_n)), (0, 0, 0, 0))
    coords, drawn = {}, 0
    for i, (key, gif) in enumerate(pairs):
        p = os.path.join(gdir, gif.replace("/", "_"))
        if not os.path.exists(p):
            continue
        try:
            im = Image.open(p).convert("RGBA")
        except Exception:
            continue
        if im.width > CELL or im.height > CELL:
            im.thumbnail((CELL, CELL), Image.LANCZOS)
        x, y = (i % COLS) * CELL, (i // COLS) * CELL
        sheet.paste(im, (x + (CELL - im.width) // 2, y + (CELL - im.height) // 2))
        coords[key] = [x, y]
        drawn += 1
    img = os.path.join(DOCS, "site", "img")
    sheet.save(os.path.join(img, "item-icons-atlas.png"), optimize=True)
    json.dump(coords, io.open(os.path.join(img, "item-icons-atlas.json"), "w", encoding="utf-8"),
              separators=(",", ":"), sort_keys=True)
    print(f"item-icons-atlas: {drawn}/{len(pairs)} drawn, sheet {sheet.size}")

if __name__ == "__main__":
    rows = scrape()
    report(rows)
    if "--gifs" in sys.argv:
        build_gif_sheet(rows)
