"""Wrap the invisible-icons fix proposal (generated in the GAME repo by
re/atlas_invisible_icons.py `html`) in the site chrome, as a static report snapshot.

The proposal page arrives self-contained (every sprite inlined as a data URI); this keeps its
content untouched from the first <h2> on and swaps its scratch styling for the site's design
system, plus the report-specific component CSS below.

Usage: python gen_report_invisible_icons.py <proposal.html> [<out.html>]
"""
import re, sys
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent / "site"
BASE = SITE / "report-items-game-fixes.html"          # chrome donor: head CSS + sitenav + footer

EXTRA_CSS = """
  /* invisible-icons report components. Icon cells keep a committed dark ground in BOTH themes -
     the 4.95 sprites were drawn against the client's dark bag panel and are unreadable on parchment. */
  :root { --gold: #8A6A1F; --ok2: #2E7D62; --warn2: #A04545;
          --strip: #16171C; --strip-cell: #22232A; --strip-line: #34353D; --strip-ink: #C6C6D0; }
  @media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
    --gold: #D9B25E; --ok2: #6FBF9F; --warn2: #E08A8A; } }
  :root[data-theme="dark"] { --gold: #D9B25E; --ok2: #6FBF9F; --warn2: #E08A8A; }
  .cellrow { display: flex; flex-wrap: wrap; gap: 8px; margin: 8px 0; }
  .cell { background: var(--strip-cell); border: 1px solid var(--strip-line); border-radius: 6px;
    padding: 6px 6px 4px; text-align: center; min-width: 78px; color: var(--strip-ink); }
  .cell img { image-rendering: pixelated; background: var(--strip); border-radius: 3px;
    display: block; margin: 0 auto; max-width: 100%; }
  .cell .cap { font-family: "IBM Plex Mono", ui-monospace, monospace; font-size: 11px;
    line-height: 1.35; margin-top: 4px; max-width: 120px; color: var(--strip-ink); }
  .cell .cap .u { display: block; font-size: 10px; }
  .ref { border-color: var(--ok2); }
  .rec { outline: 2px solid var(--gold); outline-offset: 1px; }
  .chip { display: inline-block; font: 600 10px/1 "IBM Plex Mono", ui-monospace, monospace;
    letter-spacing: 0.06em; border-radius: 9px; padding: 3px 7px; margin-bottom: 3px; }
  .chip.rec-chip { background: var(--gold); color: #1C1608; }
  .chip.ref-chip { background: var(--ok2); color: #F2F6EF; }
  .strip .cell { min-width: 44px; padding: 3px; }
  .warn { color: var(--warn2); } .ok { color: var(--ok2); }
  .mono { font-family: "IBM Plex Mono", ui-monospace, monospace; font-size: 0.92em; }
  .qs { background: var(--surface); border: 1px solid var(--rule); border-radius: 8px;
    padding: 14px 18px; margin: 16px 0; }
  .qs li { margin: 7px 0; max-width: 90ch; }
  .tablewrap { overflow-x: auto; }
  .tablewrap table { font-variant-numeric: tabular-nums; }
  .eyebrow { display: none; }  /* the hero kicker replaces the generated eyebrow */
"""

HERO = """<div class="wrap">
  <header class="hero">
    <p class="kicker">Project1998 · reports</p>
    <h1>Invisible Icons of 4.95 — fix proposal</h1>
    <p class="lede">The remap proposal for the 92 Atlas-confirmed items whose ItmIcon lies past the
4.95 client's 1,310 Item.epf frames: reference art beside the proposed 4.95 frame for every item,
with alternatives, the green_cloak worn-look verdict, the wedding-cloak row, and the open judgment
calls. Nothing here is applied yet — this is the review copy.</p>
    <p class="meta">source: ITEMS-FIX session · 2026-08-31 · art: 4.95 NexusTK.dat + 5.33 Item.epf vs NexusAtlas · tool: re/atlas_invisible_icons.py (game repo)</p>
  </header>
<p>How to read each section: the green-bordered cells are the reference art — the NexusAtlas gif
(true hue) and, where the icon id exists in the 5.33 client, that intended sprite (true shape,
palette-0 hue). The gold-outlined cell is the proposed 4.95 frame. Icon ids are ItmIcon values
(client frame = id + 1), and every cell names the items already drawn from that frame.</p>
"""

FOOTER = """<footer>Session-generated report — a snapshot for team review, not regenerated nightly.
The proposal applies to game-data/Items.csv in the game repo; when it and the repo disagree, the repo wins.</footer>
</div>
</body>
</html>"""


def main():
    src = Path(sys.argv[1])
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else SITE / "report-invisible-icons.html"

    base = BASE.read_text(encoding="utf-8")
    head = base[:base.index("</style>")]
    head = re.sub(r"<title>.*?</title>", "<title>Invisible Icons of 4.95 · Project1998</title>", head)
    nav = base[base.index('<nav class="sitenav">'):base.index("</nav>") + len("</nav>")]

    body = src.read_text(encoding="utf-8")
    start = body.index("<h2>")                       # drop the scratch page's own head/intro
    end = body.index("</main>") if "</main>" in body else len(body)
    content = body[start:end]

    out.write_text(head + EXTRA_CSS + "</style>\n</head>\n<body>\n" + nav + "\n" + HERO
                   + content + "\n" + FOOTER, encoding="utf-8")
    print(f"wrote {out} ({out.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
