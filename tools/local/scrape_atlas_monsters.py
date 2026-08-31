#!/usr/bin/env python3
"""Scrape the live NexusAtlas monsters section into tools/data/atlas_monsters.csv. LOCAL-ONLY,
run ONCE (CI never touches the network): the generator merely reads the committed CSV.

The monsters index (https://www.nexusatlas.com/monsters/index.php) is split into ~44 category
pages (regions, kingdoms, hunts). Each page lists monsters as identical table blocks:
name, experience, common/rare/unconfirmed drops, two ../photo/monster60/<img>.gif stills,
and a Creature Type footer. Mod_Security rejects bare clients, so requests carry ordinary
browser headers. Raw pages are cached in --cache (default: alongside the output) so a rerun
is a no-op offline parse.

Caveat recorded in the CSV header: the live Atlas documents MODERN NexusTK — a superset of
the 4.95 era. A mob absent here is likely RTK-added; presence does NOT prove era-correctness.

Usage: python tools/local/scrape_atlas_monsters.py [--cache DIR]
"""
import csv, io, os, re, sys, time, urllib.request

BASE = "https://www.nexusatlas.com/monsters/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nexusatlas.com/monsters/index.php",
}
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "atlas_monsters.csv")

def fetch(url, cache_path):
    if os.path.exists(cache_path) and os.path.getsize(cache_path) > 1000:
        return io.open(cache_path, encoding="utf-8", errors="replace").read()
    req = urllib.request.Request(url, headers=HEADERS)
    body = urllib.request.urlopen(req, timeout=40).read().decode("utf-8", "replace")
    io.open(cache_path, "w", encoding="utf-8").write(body)
    time.sleep(1.2)          # be polite; ~44 pages total
    return body

def text(s):
    s = re.sub(r"<[^>]+>", " ", s)
    s = s.replace("&nbsp;", " ").replace("&amp;", "&").replace("&#39;", "'").replace("&quot;", '"')
    return re.sub(r"\s+", " ", s).strip()

def parse_page(page, html_):
    """Yield one record per monster block. Blocks are keyed off the Experience marker; the
    name is the last <b>…</b> before it, images and Creature Type follow before the next block."""
    marks = [m.start() for m in re.finditer(r"<b>\s*Experience:?\s*</b>", html_)]
    for i, at in enumerate(marks):
        head = html_[max(0, at - 600):at]
        names = re.findall(r"<b>([^<]{2,60})</b>", head)
        if not names:
            continue
        name = text(names[-1])
        end = marks[i + 1] if i + 1 < len(marks) else len(html_)
        block = html_[at:end]
        exp_m = re.search(r"<b>\s*([\d,]+)\s*</b>", block)
        exp = exp_m.group(1).replace(",", "") if exp_m else ""
        imgs = re.findall(r"photo/monster60/([A-Za-z0-9_.\-]+\.gif)", block)
        type_m = re.search(r"Creature Type</b>\s*:\s*</font>?\s*([^<]*)", block) or \
                 re.search(r"Creature Type</b>\s*:\s*([^<]*)", block)
        ctype = text(type_m.group(1)) if type_m else ""
        yield {"name": name, "page": page, "exp": exp, "type": ctype,
               "images": ";".join(dict.fromkeys(imgs))}

def main():
    cache = os.path.join(os.path.dirname(OUT), "atlas_cache")
    if "--cache" in sys.argv:
        cache = sys.argv[sys.argv.index("--cache") + 1]
    os.makedirs(cache, exist_ok=True)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)

    index = fetch(BASE + "index.php", os.path.join(cache, "index.html"))
    pages = sorted({h for h in re.findall(r'href="([a-z]\w*\.php)"', index, re.I)
                    if h.lower() != "index.php"})
    print(f"{len(pages)} category pages")

    out, seen = [], set()
    for p in pages:
        try:
            body = fetch(BASE + p, os.path.join(cache, p.replace(".php", ".html")))
        except Exception as e:
            print(f"  FAIL {p}: {e}", file=sys.stderr)
            continue
        n = 0
        for rec in parse_page(p.replace(".php", ""), body):
            k = (rec["name"].lower(), rec["page"])
            if k in seen:
                continue
            seen.add(k)
            out.append(rec)
            n += 1
        print(f"  {p}: {n} monsters")

    out.sort(key=lambda r: (r["name"].lower(), r["page"]))
    with io.open(OUT, "w", encoding="utf-8", newline="") as f:
        f.write("# Live NexusAtlas monsters section, scraped once by tools/local/scrape_atlas_monsters.py.\n")
        f.write("# Reflects MODERN NexusTK (a superset of the 4.95 era): absence => likely RTK-added;\n")
        f.write("# presence does NOT prove era-correctness. images are ../photo/monster60/ filenames.\n")
        w = csv.DictWriter(f, fieldnames=["name", "page", "exp", "type", "images"])
        w.writeheader()
        w.writerows(out)
    print(f"{len(out)} monsters -> {OUT}")

if __name__ == "__main__":
    main()
