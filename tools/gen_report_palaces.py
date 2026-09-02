#!/usr/bin/env python3
"""Generate site/report-palaces.html: the Buya + Koguryo palace-interior layout report.

A team-memory aid. The palace interiors shipped with no Warps.csv rows (the RTK/CTK dumps never
wired them); we recovered the connectivity from passive live-retail captures + geometry, but the
live 7.x palaces are redesigned, so exact 4.95 door order / tiles are best-guesses and several
rooms have no .map terrain on our side at all. This report lays out every associated map with its
rendered image, so the team can spot where our reconstruction is wrong or fill the gaps.

Chrome (head CSS + sitenav + footer shell) is donated from an existing report page so the styling
stays identical. Usage: python gen_report_palaces.py [<path-to-game-repo>]
"""
import csv, html, os, sys
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent / "site"
GAME = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(r"C:\Repo\NexusTK")
GD = GAME / "game-data"
DONOR = SITE / "report-items-game-fixes.html"

# ---- load game data -------------------------------------------------------
def rows(name):
    with open(GD / name, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

names = {int(r["MapId"] if "MapId" in r else r[list(r)[0]]): r for r in []}  # placeholder
mapname = {}
for r in csv.reader(open(GD / "Maps.csv", encoding="utf-8-sig")):
    if r and r[0].isdigit():
        mapname[int(r[0])] = r[1].replace("\\'", "'")
idx = {int(r["id"]): (int(r["xs"]), int(r["ys"])) for r in rows("map_index.csv")}
warps = {}
for r in rows("Warps.csv"):
    warps.setdefault(int(r["SourceMapId"]), []).append(int(r["DestinationMapId"]))

def has_terrain(mid):
    return (GD / "maps" / f"TK{mid}.map").exists() and mid in idx
def img(mid):
    return f"img/maps/TK{mid}.webp" if (SITE / "img" / "maps" / f"TK{mid}.webp").exists() else None
def dests(mid):
    return sorted(set(d for d in warps.get(mid, []) if d != mid))

# ---- curated palace maps + notes -----------------------------------------
# note codes: era-only (7.x room, no 4.95), noterrain (in Maps.csv, no .map),
#             resized (dims differ live vs ours), guess (best-guess wiring), locked
BUYA = {
    "title": "Buya Palace", "hub": 4604,
    "intro": "Recovered from a live-retail walk. The live 7.x Buya palace was <b>rebuilt</b> — it "
             "shares the 46xx id space but added a whole Lobby/Treasury/Kitchen/Prison wing and "
             "renumbered rooms (live \u201cArmy Quarters\u201d 4614 \u2260 our \u201cImperial Army\u201d "
             "4615). We wired the 4.95 rooms era-faithfully from geometry, using the live walk only to "
             "confirm the courtyard\u2019s room set.",
    "maps": [
        (4604, "hub", "Courtyard \u2014 5 north vestibule doors + an east opening (east opening likely led to the 7.x-only Eternity Garden; left unwired)."),
        (4603, "wired", "Tribunal Hall \u2014 courtyard door (order best-guess)."),
        (4608, "wired", "Imperial Ministry \u2014 courtyard door (best-guess); \u201crestricted\u201d room."),
        (4606, "wired", "Throne Room \u2014 CONFIRMED behind the courtyard\u2019s center/grand door; also connects up to the Secret Garden (3 doors)."),
        (4609, "wired", "Royal Court \u2014 courtyard door (best-guess)."),
        (4615, "wired", "Imperial Army \u2014 courtyard door (best-guess); its top door \u2192 Training Hall."),
        (4610, "wired", "Training Hall \u2014 via Imperial Army\u2019s top door. Two other north doors + an east opening still unwired."),
        (4613, "wired", "Secret Garden \u2014 3 south doors \u2192 top of the Throne Room (left/center/right). Tile placement best-guess."),
        (4611, "unwired", "Lasahn\u2019s Chambers \u2014 single exit, destination undetermined from geometry."),
        (4612, "unwired", "Imperial Promenade \u2014 single exit, destination undetermined."),
        (4607, "noterrain", "General Quarters \u2014 no .map terrain in our registry."),
        (4616, "noterrain", "Buya Devotion \u2014 no .map terrain."),
        (4617, "noterrain", "Imperial Minister Office \u2014 no .map terrain."),
        (4618, "noterrain", "Buyan Fairgrounds \u2014 no .map terrain."),
        (4619, "noterrain", "Soldier\u2019s Quarters \u2014 no .map terrain."),
        (4620, "noterrain", "Officer\u2019s Deck \u2014 no .map terrain."),
    ],
    "tree": [
        "Courtyard (4604)",
        "\u251c\u2500 Tribunal Hall (4603)          door order best-guess",
        "\u251c\u2500 Imperial Ministry (4608)      door order best-guess",
        "\u251c\u2500 Throne Room (4606)  \u2713center  \u2500\u2500 Secret Garden (4613)  3 doors, top of throne",
        "\u251c\u2500 Royal Court (4609)            door order best-guess",
        "\u2514\u2500 Imperial Army (4615) \u2500\u2500 Training Hall (4610)  via army's top door",
    ],
    "questions": [
        "Which courtyard door leads to which room? Only the center door \u2192 Throne is confirmed; Tribunal / Ministry / Royal Court / Imperial Army order is a guess.",
        "Where do Lasahn\u2019s Chambers (4611) and Imperial Promenade (4612) connect? They each have one exit with no geometric destination.",
        "The courtyard\u2019s east opening \u2014 dead end in 4.95, or a real room we\u2019re missing?",
        "Training Hall\u2019s two spare north doors + east opening \u2014 where to (probably the terrain-less soldier/officer rooms)?",
    ],
}
KOG = {
    "title": "Koguryo Palace", "hub": 4504,
    "intro": "Recovered from a live-retail walk. Unlike Buya, the Koguryo rooms self-identify to the "
             "<b>same ids</b> in our registry (names match) \u2014 but several are resized in 7.x "
             "(our Mezzanine is 14\u00d715 vs the live 30\u00d720 hub) and a big chunk of the palace "
             "(Victory Square, Jeongwon, Treasury, Kitchen, Dining, Army Quarters) has no .map terrain "
             "on our side, so those connections are known but unwireable.",
    "maps": [
        (4504, "hub", "Courtyard \u2014 doors to Throne (center), Royal Ministry (top-right), Mezzanine (mid row); other doors locked or \u2192 Army Quarters (no terrain)."),
        (4506, "wired", "Throne Room \u2014 courtyard center door; top-left \u2192 Stairway, center-top \u2192 Treasury (no terrain)."),
        (4509, "wired", "Royal Ministry \u2014 courtyard top-right door; \u201cMinistry-members only\u201d."),
        (4505, "wired", "Royal Palace Mezzanine \u2014 courtyard mid door \u2192 mezzanine; mezzanine \u2192 Royal Court. RESIZED in 7.x into a hub; our 4.95 version is small (2 exits)."),
        (4508, "wired", "Royal Court \u2014 behind the Mezzanine."),
        (4514, "wired", "Royal Palace Stairway \u2014 7-door hub behind the Throne; wired to Throne + Baths (best-guess tiles)."),
        (4513, "wired", "Kugnae Palace Baths \u2014 via the Stairway (best-guess)."),
        (4503, "unwired", "Koguryo Tribunal Hall \u2014 has terrain but was not reached on the live walk (courtyard door was locked?); connection unknown."),
        (4510, "unwired", "KRA Training Area \u2014 has terrain but not reached on the live walk; likely hangs off the Army Quarters (4546) the way Buya\u2019s Training Hall hangs off Imperial Army, but 4546 is terrain-less so unconfirmed."),
        (4546, "noterrain", "Army Quarters \u2014 live: bottom-right courtyard door \u2192 here (3 sub-doors, mostly locked). No .map terrain."),
        (4518, "noterrain", "Victory Square \u2014 live: off the Mezzanine. No .map terrain (71\u00d770 live)."),
        (4519, "noterrain", "King MuHyul\u2019s Jeongwon \u2014 live: off the Mezzanine (upstairs). No .map terrain (100\u00d7100 live)."),
        (4520, "noterrain", "Koguryo Treasury \u2014 live: Throne center-top door. No .map terrain."),
        (4514, "skip", ""),  # dedup guard (stairway already listed)
        (4529, "noterrain", "Royal Palace Kitchen \u2014 live: off the Stairway. No .map terrain."),
        (4530, "noterrain", "Royal Dining Room \u2014 live: off the Stairway. No .map terrain."),
        (4542, "noterrain", "Koguryo Palace Hall \u2014 no .map terrain."),
        (4543, "noterrain", "Koguryo Royal Room \u2014 no .map terrain."),
        (4544, "noterrain", "Koguryo Guest Room \u2014 no .map terrain."),
    ],
    "tree": [
        "Courtyard (4504)",
        "\u251c\u2500 Throne Room (4506) \u2713center \u2500\u252c\u2500 Stairway (4514) \u2500\u252c\u2500 Baths (4513) \u2713",
        "\u2502                              \u2502               \u251c\u2500 Kitchen (4529)  \u2717 no terrain",
        "\u2502                              \u2502               \u2514\u2500 Dining (4530)   \u2717 no terrain",
        "\u2502                              \u2514\u2500 Treasury (4520)  \u2717 no terrain",
        "\u251c\u2500 Royal Ministry (4509) \u2713",
        "\u251c\u2500 Mezzanine (4505) \u2500\u252c\u2500 Royal Court (4508) \u2713",
        "\u2502                    \u251c\u2500 Victory Square (4518)  \u2717 no terrain",
        "\u2502                    \u2514\u2500 King MuHyul's Jeongwon (4519)  \u2717 no terrain",
        "\u2514\u2500 Army Quarters (4546)  \u2717 no terrain  (\u2192 KRA Training Area 4510? \u2014 unconfirmed)",
        "",
        "loose (terrain, connection unknown):  Tribunal Hall (4503)   KRA Training Area (4510)",
    ],
    "questions": [
        "Koguryo Tribunal Hall (4503) and KRA Training Area (4510) both have terrain but weren\u2019t reachable on the live walk (locked doors?) \u2014 where do they connect? (4510 likely off the Army Quarters, but that\u2019s terrain-less.)",
        "Our Mezzanine (4505) is a small 2-exit room but the live one is a big hub \u2014 in 4.95 did it only link Courtyard \u2194 Royal Court, or more?",
        "The Stairway (4514) throne-wing tiles are guesses \u2014 does anyone recall the real door\u2192room mapping (throne / baths / kitchen / dining)?",
        "Six rooms (Army Quarters, Victory Square, Jeongwon, Treasury, Kitchen, Dining) have no .map terrain \u2014 were they in 4.95 at all, and can anyone source the maps?",
    ],
}

STATUS = {"hub": ("HUB", "s-hub"), "wired": ("WIRED", "s-ok"), "unwired": ("terrain, unwired", "s-warn"),
          "noterrain": ("no terrain", "s-no"), "skip": ("", "")}

def map_card(mid, code, note):
    nm = html.escape(mapname.get(mid, f"map {mid}"))
    dim = f"{idx[mid][0]}\u00d7{idx[mid][1]}" if mid in idx else "\u2014"
    lbl, cls = STATUS[code]
    conn = dests(mid)
    connstr = ("\u2192 " + ", ".join(str(c) for c in conn)) if conn else ""
    im = img(mid)
    thumb = f'<img loading="lazy" src="{im}" alt="map {mid}">' if im else '<div class="noimg">no map image</div>'
    return f"""<div class="mapcard {cls}">
  <div class="thumb">{thumb}</div>
  <div class="body"><div class="mhead"><span class="mid">{mid}</span> <b>{nm}</b>
    <span class="badge {cls}">{lbl}</span></div>
    <div class="mmeta">{dim}{'  ' + connstr if connstr else ''}</div>
    <p>{note}</p></div>
</div>"""

def section(P):
    cards = "\n".join(map_card(m, c, n) for m, c, n in P["maps"] if c != "skip")
    tree = html.escape("\n".join(P["tree"]))
    qs = "\n".join(f"<li>{q}</li>" for q in P["questions"])
    return f"""
<h2 id="{P['title'].lower().split()[0]}">{P['title']}</h2>
<p>{P['intro']}</p>
<h3>Connectivity (as wired)</h3>
<pre class="tree">{tree}</pre>
<h3>Open questions for the team</h3>
<ul class="qs">{qs}</ul>
<h3>Associated maps</h3>
<div class="mapgrid">{cards}</div>
"""

# ---- assemble with donor chrome ------------------------------------------
donor = DONOR.read_text(encoding="utf-8")
head = donor[:donor.index("</nav>") + len("</nav>")]

EXTRA = """
<style>
  .lede2 { max-width: 82ch; }
  .tree { background: var(--surface); border: 1px solid var(--rule); border-radius: 8px;
    padding: 14px 16px; overflow-x: auto; font-family: "IBM Plex Mono", ui-monospace, monospace;
    font-size: 12.5px; line-height: 1.5; }
  .qs { max-width: 90ch; } .qs li { margin: 7px 0; }
  .mapgrid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 14px;
    margin: 12px 0 28px; }
  .mapcard { border: 1px solid var(--rule); border-radius: 10px; overflow: hidden; background: var(--surface);
    display: flex; flex-direction: column; }
  .mapcard .thumb { background: #14210f; aspect-ratio: 1/1; display: flex; align-items: center;
    justify-content: center; overflow: hidden; }
  .mapcard .thumb img { width: 100%; height: 100%; object-fit: contain; image-rendering: pixelated; }
  .mapcard .noimg { color: #7a8a70; font: 500 12px "IBM Plex Mono", monospace; }
  .mapcard .body { padding: 9px 11px 11px; }
  .mapcard .mhead { display: flex; align-items: baseline; gap: 6px; flex-wrap: wrap; }
  .mapcard .mid { font-family: "IBM Plex Mono", monospace; color: var(--ink-soft); font-size: 12px; }
  .mapcard .mmeta { font-family: "IBM Plex Mono", monospace; font-size: 11px; color: var(--ink-soft);
    margin: 2px 0 5px; }
  .mapcard p { margin: 0; font-size: 13px; line-height: 1.45; }
  .badge { font: 600 9.5px/1 "IBM Plex Mono", monospace; letter-spacing: .05em; border-radius: 9px;
    padding: 3px 7px; white-space: nowrap; }
  .s-hub .badge, .badge.s-hub { background: #7A5CBF; color: #fff; }
  .s-ok .badge, .badge.s-ok { background: #2E7D62; color: #fff; }
  .s-warn .badge, .badge.s-warn { background: #A0741F; color: #fff; }
  .s-no .badge, .badge.s-no { background: #8a8f98; color: #fff; }
  .mapcard.s-no .thumb { background: #1a1c20; }
</style>
"""

body = f"""
<div class="wrap">
  <header class="hero">
    <p class="kicker">Project1998 · team review</p>
    <h1>Palace Interiors \u2014 layout recovery</h1>
    <p class="lede lede2">The Buya and Koguryo palace interiors shipped <b>disconnected</b> \u2014 no
      <code>Warps.csv</code> rows, because the RTK/CTK dumps never wired them. We recovered the
      connectivity from passive live-retail walkthroughs (enter-map self-identification) and filled
      the tiles from our own map geometry. <b>But the live 7.x palaces are redesigned</b>, so the exact
      4.95 door order and several tile placements are <b>best-guesses</b>, and a number of rooms have no
      <code>.map</code> terrain on our side at all.</p>
    <p class="meta">Each map below shows its rendered image \u2014 if a door order looks wrong or you
      remember a room we\u2019re missing, that\u2019s exactly the feedback this report is fishing for.
      Colors: <span class="badge s-hub">HUB</span> <span class="badge s-ok">WIRED</span>
      <span class="badge s-warn">terrain, unwired</span> <span class="badge s-no">no terrain</span></p>
  </header>
  {section(BUYA)}
  {section(KOG)}
<footer>Session-generated report \u2014 a snapshot for team review, not regenerated nightly.
The live atlas + database pages are the always-current view; when this report and the site disagree, the site wins.</footer>
</div>
</body>
</html>
"""

out = SITE / "report-palaces.html"
out.write_text(head + EXTRA + body, encoding="utf-8")
print(f"wrote {out}  ({len(BUYA['maps'])} Buya + {len([m for m in KOG['maps'] if m[1]!='skip'])} Koguryo maps)")
