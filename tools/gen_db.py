#!/usr/bin/env python3
"""Generate the database pages (spells.html, items.html, mobs.html) from the game repo's game-data CSVs.

Usage:  python tools/gen_db.py <path-to-game-repo>

Runs the same locally and in CI (the regen workflow checks out the public game repo). Pure CSV -> HTML:
no client assets needed. Sprite sheets are OPTIONAL local artifacts (site/img/item-icons.png + .json,
site/img/mob-sprites.png + .json, produced by tools/local/render_sprites.py on a machine that has the
5.33 client); the pages check for the .json at generation time and render icon cells only when present.
"""
import csv, html, io, json, os, sys

GAME = sys.argv[1] if len(sys.argv) > 1 else r"C:\Repo\NexusTK"
GD = os.path.join(GAME, "game-data")
SITE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "site")

def rows(name):
    """DictReader over a game-data CSV, skipping '#' comment lines."""
    with io.open(os.path.join(GD, name), encoding="utf-8-sig", errors="replace") as f:
        lines = [l for l in f if not l.lstrip().startswith("#")]
    return list(csv.DictReader(lines))

def rows_opt(name):
    """rows(), but an absent file is empty rather than fatal — for the smaller side tables."""
    if not os.path.exists(os.path.join(GD, name)):
        print(f"warning: {name} not found; generating without it", file=sys.stderr)
        return []
    return rows(name)

def num(v, default=0):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return default

# ---------------------------------------------------------------- shared page chrome
NAV = """<nav class="sitenav">
  <a class="brand" href="./">Project1998</a>
  <a href="commands.html">Commands</a>
  <a href="quest-registry.html">Quests</a>
  <a href="spells.html"{sp}>Spells</a>
  <a href="effects.html">Effects</a>
  <a href="items.html"{it}>Items</a>
  <a href="mobs.html"{mo}>Mobs</a>
  <a href="atlas.html">Atlas</a>
  <a href="map-editor.html">Map Editor</a>
  <a href="noclip.html">No-Clip</a>
  <a href="patch-notes.html">Patch Notes</a>
</nav>"""

def nav(current):
    return NAV.format(sp=' aria-current="page"' if current == "spells" else "",
                      it=' aria-current="page"' if current == "items" else "",
                      mo=' aria-current="page"' if current == "mobs" else "")

CHROME_CSS = """
  :root {
    --ground: #F4F6F1; --surface: #FCFDFB; --ink: #1F2A26; --ink-soft: #55645D;
    --ink-faint: #8A978F; --rule: #DDE4DD; --rule-soft: #E8EDE7;
    --accent: #2E7D62; --accent-ink: #1E5A46; --focus: #2E7D62; --chip-ghost: #F0F3EE;
  }
  @media (prefers-color-scheme: dark) {
    :root:not([data-theme="light"]) {
      --ground: #141B18; --surface: #1B2420; --ink: #D8E2DA; --ink-soft: #93A49A;
      --ink-faint: #66766D; --rule: #2A3630; --rule-soft: #222D28;
      --accent: #6FBF9F; --accent-ink: #8FD4B8; --focus: #6FBF9F; --chip-ghost: #202A25;
    }
  }
  :root[data-theme="dark"] {
    --ground: #141B18; --surface: #1B2420; --ink: #D8E2DA; --ink-soft: #93A49A;
    --ink-faint: #66766D; --rule: #2A3630; --rule-soft: #222D28;
    --accent: #6FBF9F; --accent-ink: #8FD4B8; --focus: #6FBF9F; --chip-ghost: #202A25;
  }
  * { box-sizing: border-box; }
  body { margin: 0; background: var(--ground); color: var(--ink);
    font-family: "IBM Plex Sans", "Segoe UI", system-ui, sans-serif; font-size: 14.5px; line-height: 1.5; }
  a { color: var(--accent-ink); text-underline-offset: 2px; }
  a:focus-visible, button:focus-visible, input:focus-visible, select:focus-visible { outline: 2px solid var(--focus); outline-offset: 2px; }
  code { font-family: "IBM Plex Mono", ui-monospace, monospace; font-size: 0.92em; color: var(--accent-ink); }
  .sitenav { max-width: min(1680px, 96vw); margin: 0 auto; padding: 14px 24px 0;
    display: flex; gap: 16px; align-items: baseline; font-size: 14px; flex-wrap: wrap; }
  .sitenav a { color: var(--ink-soft); text-decoration: none; }
  .sitenav a:hover { color: var(--accent-ink); text-decoration: underline; }
  .sitenav .brand { font-family: "Gowun Batang", Georgia, serif; font-weight: 700;
    color: var(--ink); margin-right: auto; font-size: 16px; }
  .sitenav a[aria-current="page"] { color: var(--accent-ink); font-weight: 600; }
  .wrap { max-width: min(1680px, 96vw); margin: 0 auto; padding: 0 24px 96px; }
  header.hero { padding: 34px 0 6px; }
  .kicker { font-family: "IBM Plex Mono", ui-monospace, monospace; font-size: 12px;
    letter-spacing: 0.14em; text-transform: uppercase; color: var(--accent); margin: 0 0 8px; }
  h1 { font-family: "Gowun Batang", Georgia, serif; font-weight: 700;
    font-size: clamp(28px, 4.5vw, 38px); line-height: 1.15; margin: 0 0 8px; text-wrap: balance; }
  .lede { max-width: 68ch; color: var(--ink-soft); margin: 0; }
  .toolbar { position: sticky; top: 0; z-index: 5; background: var(--ground);
    border-bottom: 1px solid var(--rule); padding: 10px 0;
    display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin-top: 18px; }
  .toolbar input[type="search"] { flex: 1 1 220px; font: 14px "IBM Plex Sans", system-ui, sans-serif;
    padding: 7px 12px; border: 1px solid var(--rule); border-radius: 6px;
    background: var(--surface); color: var(--ink); }
  .toolbar select { font: 13px "IBM Plex Sans", system-ui, sans-serif; padding: 6px 8px;
    border: 1px solid var(--rule); border-radius: 6px; background: var(--surface); color: var(--ink); }
  .toolbar .count { font-size: 12.5px; color: var(--ink-faint); margin-left: auto;
    font-variant-numeric: tabular-nums; white-space: nowrap; }
  /* Sticky header vs horizontal fallback: position:sticky computes against the nearest scroll
     container, so a th inside an overflow-x wrapper pins INSIDE the table (pushed down over row 1)
     and never reaches the viewport. Wide screens drop the overflow wrapper so the header truly
     sticks under the toolbar; narrow screens keep the horizontal scroll and a static header. */
  .tablewrap { overflow-x: auto; margin-top: 6px; }
  table { border-collapse: collapse; width: 100%; font-size: 13.5px; }
  th, td { text-align: left; padding: 6px 10px; border-bottom: 1px solid var(--rule-soft); vertical-align: top; }
  th { font-family: "IBM Plex Mono", ui-monospace, monospace; font-size: 11px;
    letter-spacing: 0.07em; text-transform: uppercase; color: var(--ink-faint); font-weight: 500;
    position: sticky; top: var(--thead-top, 55px); background: var(--ground); cursor: pointer; white-space: nowrap; }
  th.sorted-asc::after { content: " ▲"; } th.sorted-desc::after { content: " ▼"; }
  /* Sticky header vs horizontal fallback: position:sticky computes against the nearest scroll
     container, so a th inside an overflow-x wrapper pins INSIDE the table (pushed down over row 1)
     and never reaches the viewport. Wide screens drop the overflow wrapper so the header truly
     sticks under the toolbar; narrow screens keep the horizontal scroll and a static header.
     (These come after the base th rule — same specificity, so order decides.) */
  @media (min-width: 1560px) { .tablewrap { overflow-x: visible; } }
  @media (max-width: 1559.98px) { th { position: static; } }
  td.n { text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }
  td .k { font-family: "IBM Plex Mono", ui-monospace, monospace; font-size: 11px; color: var(--ink-faint); display: block; }
  td .nm { font-weight: 600; color: var(--ink); }
  .spr { width: 24px; height: 24px; display: inline-block; vertical-align: middle;
    image-rendering: pixelated; background-repeat: no-repeat; }
  .muted { color: var(--ink-faint); }
  .pill { font-family: "IBM Plex Mono", ui-monospace, monospace; font-size: 10.5px;
    padding: 1px 7px; border-radius: 999px; background: var(--chip-ghost); color: var(--ink-soft); white-space: nowrap; }
  .sub { font-size: 12.5px; color: var(--ink-soft); }
  footer { margin-top: 40px; padding-top: 14px; border-top: 1px solid var(--rule); font-size: 12.5px; color: var(--ink-faint); }
"""

HEAD = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} · Project1998</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Gowun+Batang:wght@400;700&family=IBM+Plex+Sans:ital,wght@0,400;0,500;0,600;1,400&family=IBM+Plex+Mono:wght@400;500;600&display=swap">
<style>{css}</style>
</head>
<body>
"""

FOOT = """<footer>Generated from the game repo's <code>game-data</code> CSVs — the server's own truth.
Regenerated automatically; report mismatches on Discord.</footer>
</div>
</body>
</html>
"""

# ---------------------------------------------------------------- lookups
# Full path tree: name, base-class id (PthType) and PthIcon (0 base class / 4 NPC subpath / 1-3 PC subpath),
# mirroring Content.PathBaseOf / Content.IsNpcSubpath.
PATHS = {num(r["PthId"]): {"name": r["PthMark0"], "base": num(r["PthType"]), "icon": num(r["PthIcon"])}
         for r in rows("Paths.csv") if r.get("PthMark0")}
paths = {pid: p["name"] for pid, p in PATHS.items()}
def path_name(pid):
    if pid == 99: return "All"
    if pid == -1: return "Any"
    return paths.get(pid, f"path {pid}")

ALIGN = {-1: "", 0: "", 1: "Kwisin", 2: "Mingken", 3: "Ohaeng"}
maps_by_id = {num(r["id"]): r["name"] for r in rows("map_index.csv")}

TYPE_NAMES = {2: "Use (target)", 3: "Weapon", 4: "Armor", 5: "Shield", 6: "Helm", 7: "Ring (L)",
              8: "Ring (R)", 9: "Hand (L)", 10: "Hand (R)", 11: "Face acc", 12: "Head", 13: "Mantle",
              14: "Necklace", 15: "Boots", 16: "Coat", 18: "Use / etc", 22: "Quest", 24: "Mount"}

def sheet(kind):
    """Load a sprite-sheet coordinate map if the local render step produced one."""
    p = os.path.join(SITE, "img", kind + ".json")
    if os.path.exists(p):
        return json.load(io.open(p, encoding="utf-8"))
    return None

def jsdata(name, obj):
    return f"<script>const {name} = {json.dumps(obj, separators=(',', ':'), ensure_ascii=False)};</script>"

# ---------------------------------------------------------------- spells
# Server-code mirrors. The classification SETS are parsed out of Server/Content.cs and npc_dialog.lua at
# generation time so the page tracks the code; each has a baked fallback (warned on stderr) so the nightly
# regen survives a refactor that moves them. The narrative provenance STRINGS (dog requirements, sage terms,
# quest grants) are transcriptions — their one source is named next to each.
import re

def _read(relpath):
    p = os.path.join(GAME, relpath)
    try:
        return io.open(p, encoding="utf-8", errors="replace").read()
    except OSError:
        return ""

def _parse_keys(text, pattern, fallback, label):
    m = re.search(pattern, text, re.S)
    keys = re.findall(r'"([a-z0-9_]+)"', m.group(1)) if m else []
    if not keys:
        print(f"warning: could not parse {label} from server source; using baked copy", file=sys.stderr)
        return fallback
    return keys

_CONTENT = _read(os.path.join("Server", "Content.cs"))
_DIALOG = _read(os.path.join("game-data", "npc_dialog.lua"))

# Content.cs SageLadder — rung order matters (rung n = index+1).
SAGE_LADDER = _parse_keys(_CONTENT, r"SageLadder\s*=\s*\{([^}]*)\}",
    ["share_wisdom", "mentors_wisdom", "apprentices_wisdom", "adepts_wisdom", "sages_wisdom"], "SageLadder")
# Content.cs SplitTrapSpells — the 8 post-2003 individual traps behind the SplitTrapSpells era gate.
SPLIT_TRAPS = set(_parse_keys(_CONTENT, r"SplitTrapSpells\s*=\s*new\([^)]*\)\s*\{([^}]*)\}",
    ["set_dart_trap", "set_flash_trap", "set_repeating_dart_trap", "set_snare_trap",
     "set_spear_trap", "set_poison_dart_trap", "set_death_trap", "set_sleep_trap"], "SplitTrapSpells"))
# Content.cs UniversalBaseSpells — taught to EVERY class (tutorial), SpellCosts rows are relearn-only.
UNIVERSAL = set(_parse_keys(_CONTENT, r"UniversalBaseSpells\s*=\s*new\([^)]*\)\s*\{([^}]*)\}",
    ["soothe"], "UniversalBaseSpells"))
# npc_dialog.lua ALL_DOG_SPELLS — membership of the Dog Linguist flow.
DOG_SPELLS = set(_parse_keys(_DIALOG, r"ALL_DOG_SPELLS\s*=\s*\{([^}]*)\}",
    ["greater_blessing", "spirit_fury", "spot_traps", "serpents_fury",
     "fissure", "lava_surge", "survive", "fascinate"], "ALL_DOG_SPELLS"))
# Content.cs CityLockedSpells: base key -> region id (RegionCityName: 0 Kugnae, 1 Buya, 2 Mythic, 3 Nagnang).
_m = re.search(r"CityLockedSpells\s*=\s*new\([^)]*\)\s*\{(.*?)\};", _CONTENT, re.S)
CITY_LOCK = dict(re.findall(r'\["([a-z0-9_]+)"\]\s*=\s*(\d+)', _m.group(1))) if _m else {}
if not CITY_LOCK:
    print("warning: could not parse CityLockedSpells; using baked copy", file=sys.stderr)
    CITY_LOCK = {"maros_remedy": "0", "masos_remedy": "1", "daggers_remedy": "3"}
CITY_NAME = {"0": "Kugnae", "1": "Buya", "2": "the Mythic", "3": "Nagnang"}
CITY_TRAINER = {"maros_remedy": "Maro", "masos_remedy": "Maso", "daggers_remedy": "Dagger"}

# Content.cs NpcGrantedSpells = SageLadder + propose: trainers refuse these even where cost rows exist.
NPC_GRANTED = set(SAGE_LADDER) | {"propose"}

# Content.cs BaseKey: strip one alignment prefix, then one class suffix.
def base_key(k):
    k = k.lower()
    for pre in ("kwisin_", "mingken_", "ohaeng_"):
        if k.startswith(pre):
            k = k[len(pre):]
            break
    for suf in ("_peasant", "_warrior", "_rogue", "_mage", "_poet"):
        if k.endswith(suf):
            k = k[:-len(suf)]
            break
    return k

# npc_dialog.lua DOG_SPELLS table (kill/goods requirements) + BIG_GATE_VITA/MANA 20000/10000. The two-line
# summary per spell is a transcription of that table; sources tswolf + nexusatlas per its own header.
DOG_INFO = {
    "greater_blessing": "Warrior Dog Linguist · lv 70 · slay 3 Trapdoor spiders",
    "spirit_fury": "Warrior Dog Linguist · lv 99 + 20k vita or 10k mana · slay the Non-Corporeal Bunny · Ambrosia + 10,000 gold",
    "spot_traps": "Rogue Dog Linguist · lv 70 · slay 3 Trapdoor spiders",
    "serpents_fury": "Rogue Dog Linguist · lv 99 + 20k vita or 10k mana · slay Zin-te and Zangze · show a Whisper bracelet (not taken)",
    "fissure": "Mage Dog Linguist · lv 70 · Amber, Amethyst, Quartz, Topaz",
    "lava_surge": "Mage Dog Linguist · lv 99 + 20k vita or 10k mana · slay an Ice panther · Star staff + Scribe's pen",
    "survive": "Poet Dog Linguist · lv 70 · 10 Mountain ginseng + Pearl charm",
    "fascinate": "Poet Dog Linguist · lv 99 + 20k vita or 10k mana · slay an Ice panther · Titanium lance + Purified water",
}
# The dialog-enforced learn levels (DOG_SPELLS `level` fields; Content.SageLevel = 90). Spells.csv carries
# SplLevel 0 for all of these because no trainer path applies — the NPC flow is the gate.
DOG_LEVEL = {"greater_blessing": 70, "spot_traps": 70, "fissure": 70, "survive": 70,
             "spirit_fury": 99, "serpents_fury": 99, "lava_surge": 99, "fascinate": 99}
SAGE_LEVEL = 90

BASE_CLASS = {1: "Warrior", 2: "Rogue", 3: "Mage", 4: "Poet"}
RANK = {1: "Il san", 2: "Ee san", 3: "Sam san"}
MARK_SPELL_LEVEL = 99   # Content.MarkSpellLevel — mark rows carry SplLevel 0, floored at load

def clean_name(s):
    return (s or "").replace("\\", "")   # Content.Clean strips the export's backslash escapes

def fx_gifs():
    """csv-id -> data-URI animated gif, lifted from the committed site/effects.html (which is built
    locally from the 4.95 client). Parsing the committed page keeps CI able to embed the animations
    without client assets; absent file just means no inline animations."""
    p = os.path.join(SITE, "effects.html")
    if not os.path.exists(p):
        print("warning: site/effects.html not found; spells page gets no fx animations", file=sys.stderr)
        return {}
    h = io.open(p, encoding="utf-8").read()
    found = re.findall(r'<span class="wire">csv (\d+)</span><span class="meta">[^<]*</span>'
                       r'</header><div class="stage"><img src="(data:image/gif;base64,[^"]+)"', h)
    if not found:
        print("warning: no fx cards parsed from site/effects.html; its markup may have changed", file=sys.stderr)
    return {int(n): g for n, g in found}

def fmt_ms(ms):
    ms = num(ms, 0)
    if ms <= 0: return ""
    if ms < 1000: return f"{ms}ms"
    s = round(ms / 1000)
    for big, small, bu, su in ((86400, 3600, "d", "h"), (3600, 60, "h", "m"), (60, 1, "m", "s")):
        if s >= big:
            hi, rest = divmod(s, big)
            lo = round(rest / small)
            return f"{hi}{bu} {lo}{su}" if lo else f"{hi}{bu}"
    return f"{s}s"

def build_spells():
    params = {r["key"]: r for r in rows("SpellParams.csv")}
    effects = {r["key"]: r for r in rows("spell_effects.csv")}
    levels = {r["key"]: num(r["level"]) for r in rows("SpellLevels.csv")}
    texts = {r["key"]: r for r in rows("SpellText.csv")}
    mods = {r["key"]: r for r in rows("SpellMods.csv")}
    itemnames = {r["ItmIdentifier"]: clean_name(r["ItmDescription"]) for r in rows("Items.csv")}
    def item_name(k):
        return itemnames.get(k, k.replace("_", " "))

    # ServerTuning.csv SplitTrapSpells toggle (Content.SplitTrapSpellsEnabled, default 0 = era gate closed).
    tuning = {r[list(r)[0]]: r[list(r)[1]] for r in rows("ServerTuning.csv")}
    split_traps_on = num(tuning.get("SplitTrapSpells"), 0) != 0

    # SpellLearnCosts.csv: key -> {base pathId -> row}. Content.LearnCostFor keys strictly on base path 1-4;
    # the row's own `level` is the level the trainer actually enforces (SpellsForClass overrides SplLevel).
    costs = {}
    for r in rows("SpellLearnCosts.csv"):
        costs.setdefault(r["key"], {})[num(r["pathId"])] = r

    def cost_text(r):
        items = [f"{item_name(r[f'item{i}'])} x{r[f'amt{i}']}" for i in (1, 2, 3, 4) if r.get(f"item{i}")]
        gold = num(r.get("gold"))
        return ", ".join(([f"{gold:,} gold"] if gold else []) + items) or "free"

    # WeaponProcs.csv: spell key -> "Item name chance%" list (spells that arrive as weapon procs).
    procs = {}
    for r in rows("WeaponProcs.csv"):
        if r.get("spell"):
            procs.setdefault(r["spell"], []).append(f"{item_name(r['item'])} {r['chancePct']}%")

    # MobSpells.csv rows are self-contained mob spells matched to player spells by DISPLAY NAME — the mob
    # rows carry their own mob-tuned numbers, so this is "mobs cast a spell of this name".
    mobnames = {r["Identifier"]: r["Description"] for r in rows("mobs.csv")}
    castby = {}
    for r in rows("MobSpells.csv"):
        if r.get("MobKey") and r.get("Name"):
            castby.setdefault(r["Name"].strip().lower(), set()).add(mobnames.get(r["MobKey"], r["MobKey"]))

    def effect_text(key, p, e, m):
        parts = []
        verb = (p.get("verb") or "").strip()
        stat, amount = (p.get("stat") or "").strip(), (p.get("amount") or "").strip()
        base, coeff, wc = (p.get("base") or "").strip(), (p.get("coeff") or "").strip(), (p.get("willcoeff") or "").strip()
        if verb == "venom":
            seg = "DoT"
            if (p.get("flat") or "").strip(): seg += f" flat {num(p['flat']):,}/tick"
            elif amount: seg += f" tick cap {num(amount):,}"
            parts.append(seg)
        elif verb == "endear":
            parts.append("mind control")                 # base column holds the aether for this family
        elif verb == "kamikaze":
            parts.append(f"blast {coeff}×caster's current HP — caster left at {amount} HP")
        elif stat and amount:
            parts.append(f"{stat} {num(amount):+d}")
        elif verb == "heal" and amount:
            parts.append(f"heal {amount}" + (f" + {wc}×Will" if wc else ""))
        elif verb == "drain" and amount:
            parts.append(f"absorb mobs ≤{num(amount):,} HP")
        elif base or coeff:
            parts.append(base if not num(coeff, 0) and base else f"{base or 0} + {coeff or 0}×Will")
        elif amount and num(amount):
            parts.append(f"amount {amount}")
        arch = (e.get("archetype") or "").strip()
        expr = (e.get("amountExpr") or "").strip()
        if expr and not (base or coeff or amount):
            label = {"Damage": "dmg", "Heal": "heal", "ManaBattery": "mana"}.get(arch, "amount")
            parts.append(f"{label} {expr}")
        if (e.get("buffStat") or "").strip() and not stat:
            parts.append(f"{e['buffStat']} {num(e.get('buffAmt')):+d}" if (e.get("buffAmt") or "").strip() else e["buffStat"])
        # A params row means the verb defines the behavior — the spell_effects debuff is then only the old
        # keyword extraction (amnesia's own notes call it out as wrong), so it defers to the verb.
        if (e.get("debuff") or "").strip() and not p: parts.append(e["debuff"])
        if (e.get("cureCat") or "").strip(): parts.append(f"cures {e['cureCat']}")
        if (e.get("healthCost") or "").strip(): parts.append(f"cost {e['healthCost']}")
        chance = (p.get("chance") or "").strip() or (e.get("chance") or "").strip()
        if chance: parts.append(f"{chance}% to land")
        if (m.get("rage") or "").strip(): parts.append(f"fury tier {m['rage']}")
        if (m.get("enchantAmt") or "").strip():
            parts.append(f"enchant ×{m['enchantAmt']}" + (f" ({num(m.get('enchantMana')):,} mana)" if (m.get("enchantMana") or "").strip() else ""))
        return " · ".join(parts)

    def learn_lines(key, name, pid, lv, e_class):
        """[(line, title)] for the Learn / source column, mirroring who can actually grant the spell."""
        if key in SPLIT_TRAPS and not split_traps_on:
            return [("Era-gated off (SplitTrapSpells=0) — Set Trap sets this trap", "Server/Content.cs IsOutOfEraSplitTrap")]
        if key in DOG_SPELLS:
            return [(DOG_INFO.get(key, "Taught only by the class's Dog Linguist — kills and goods, never the guildmaster"),
                     "game-data/npc_dialog.lua DOG_SPELLS")]
        if key in SAGE_LADDER:
            rung = SAGE_LADDER.index(key) + 1
            line = f"Sage only (rung {rung}/5) · lv 90+ · 100,000 gold · 90-day wait · replaces the rung below"
            if rung == 5: line += " · requires Sam san"
            return [(line, "game-data/npc_dialog.lua SageNpc; Server/Content.cs SageLadder")]
        if key == "propose":
            return [("Wedding flow only — never sold by trainers", "Server/Content.cs NpcGrantedSpells")]
        if key == "restore_poet":
            return [("Quest: avenge the Dogs (Old Dog NPC) · Poet lv 99 + Dog legend · slay Tiger Storm with no other kills · +50,000,000 exp",
                     "game-data/npc_dialog.lua OldDogNpc")]
        out = []
        if key in UNIVERSAL:
            out.append(("Tutorial quest — taught to every class (5 acorns + 5 rabbit meat)",
                        "game-data/npc_dialog.lua; Server/Content.cs UniversalBaseSpells"))
            per = costs.get(key, {})
            for p_ in sorted(per):
                r = per[p_]
                out.append((f"relearn: {BASE_CLASS[p_]} lv {num(r['level'])} — {cost_text(r)}", r.get("source") or ""))
            missing = [BASE_CLASS[p_] for p_ in BASE_CLASS if p_ not in per]
            if missing:
                out.append((f"{'/'.join(missing)}s cannot relearn it", "Server/Content.cs CanRelearnAtNpc"))
            return out
        if pid in PATHS and PATHS[pid]["icon"] != 0:      # subpath signature spell — granted at the rank
            base = paths.get(PATHS[pid]["base"], "?")
            kind = "NPC" if PATHS[pid]["icon"] == 4 else "PC"
            return [(f"Granted on reaching {paths[pid]} ({kind} subpath of {base})", "Server/Content.cs SpellsForClass")]
        if pid == 5:
            return [("GM only", "")]
        per = costs.get(key, {})
        lock = CITY_LOCK.get(base_key(key))
        for p_ in sorted(per):
            r = per[p_]
            line = f"{BASE_CLASS.get(p_, f'path {p_}')} lv {num(r['level'])} — {cost_text(r)}"
            if lock is not None:
                line += f" · {CITY_NAME.get(lock, lock)} only ({CITY_TRAINER.get(base_key(key), 'trainer')})"
            out.append((line, r.get("source") or ""))
        if out:
            return out
        if pid in BASE_CLASS:
            return [(f"{BASE_CLASS[pid]} trainer lv {lv} — free", "no SpellLearnCosts row: taught free")]
        if pid == 0:
            return [(f"Any class trainer lv {lv} — free", "no SpellLearnCosts row: taught free")]
        if key in procs:
            return []                                     # proc-only: the procs line below covers it
        if (e_class or "") in ("baseFunc", "instance"):
            return [("Internal server mechanism", "")]
        return [("Not trainer-taught", "")]

    out = []
    for r in rows("Spells.csv"):
        key, name = r["SplIdentifier"], clean_name(r["SplDescription"])
        if not key or key.startswith("=="):
            continue
        pid = num(r["SplPthId"])
        typ = num(r["SplType"])
        mk = num(r["SplMark"])
        p, e, m = params.get(key, {}), effects.get(key, {}), mods.get(key, {})
        e_class = (e.get("class") or "").strip()
        mana = p.get("mana") or e.get("mana") or ""
        active = r.get("SplActive") != "0"

        # Level exactly as the server derives it: SpellLevels override -> SplLevel, floored to 99 for mark
        # rows (LoadSpells), then the class's own SpellLearnCosts level wins where a row exists
        # (SpellsForClass). Subpath signature spells pin to the rank (MarkSpellLevel).
        lv = levels.get(key, num(r["SplLevel"]))
        if mk > 0: lv = max(lv, MARK_SPELL_LEVEL)
        if key in SAGE_LADDER: lv = SAGE_LEVEL
        if key in DOG_LEVEL: lv = DOG_LEVEL[key]
        if pid in PATHS and PATHS[pid]["icon"] != 0:
            lv = MARK_SPELL_LEVEL
        elif pid in BASE_CLASS and pid in costs.get(key, {}):
            lv = num(costs[key][pid]["level"])

        # Durations: SpellParams wins over spell_effects (the verb reads its params row when one exists).
        # The sage rungs' params.duration IS the aether, per the row's own notes.
        sage = key in SAGE_LADDER
        dur_ms = 0 if sage else (num(p.get("duration"), 0) or num(e.get("durationMs"), 0))
        durmax = 0 if sage else num(p.get("durationMax"), 0)
        aet_ms = num(p.get("duration"), 0) if sage else num(e.get("aether"), 0)
        if (p.get("verb") or "").strip() == "endear":    # endear family: params.base IS the aether
            aet_ms = aet_ms or num(p.get("base"), 0)
        if (p.get("verb") or "").strip() == "venom" and not (p.get("flat") or "").strip():
            # venom-family durations are the upper bound of 1+rand(...) — the notes carry the full shape.
            # (flat-tick rows like burn run a FIXED duration and take the normal branch.)
            dur_tx = f"≤{fmt_ms(dur_ms)}" if dur_ms >= 1000 else ""
            if dur_ms < 1000: dur_ms = 0
        elif durmax and durmax < dur_ms:
            dur_tx = f"{fmt_ms(dur_ms)} (boss {fmt_ms(durmax)})"   # amnesia: 15m on a mob, 5s on a boss
        else:
            dur_tx = fmt_ms(dur_ms) + (f"–{fmt_ms(durmax)}" if durmax else "")

        pills = []
        if typ == 5: pills.append("skill")
        if not active: pills.append("inactive")
        if key in SPLIT_TRAPS and not split_traps_on: pills.append("era off")
        if pid == 5 or e_class == "GM": pills.append("GM")
        if e_class in ("baseFunc", "instance"): pills.append("internal")

        detail = []
        q = (r.get("SplQuestion") or "").strip()
        if q.upper() == "NO": q = ""
        if typ == 2: detail.append("targeted")
        if typ == 1: detail.append("prompt-cast")
        if q: detail.append(f"asks “{clean_name(q)}”")
        if r.get("SplCanFail") == "1": detail.append("can fail (deflect)")
        if (p.get("verb") or "").strip(): detail.append(f"verb: {p['verb']}")
        t = texts.get(key)
        if t:
            if (t.get("targetText") or "").strip(): detail.append(f"“{t['targetText']}”")
            if (t.get("fadeText") or "").strip(): detail.append(f"fades: “{t['fadeText']}”")
        if num(p.get("pcDps"), 0): detail.append(f"vs players: {num(p['pcDps']):,}/tick, {fmt_ms(p.get('pcDurMs'))}")
        if key in procs: detail.append("weapon proc: " + ", ".join(procs[key]))

        mobs = sorted(castby.get(name.strip().lower(), []))
        subpath = PATHS.get(pid, {}).get("icon", 0) != 0 and pid in PATHS
        out.append({
            "k": key, "id": num(r["SplId"]), "n": name, "c": path_name(pid), "cl": pid,
            "cb": paths.get(PATHS[pid]["base"], "") if subpath else "",
            "lv": lv, "mk": mk, "rk": RANK.get(mk, ""),
            "al": ALIGN.get(num(r["SplAlignment"], -1), ""),
            "mana": num(mana) if str(mana).strip() else "",
            "cat": (p.get("category") or e.get("archetype") or "").strip(),
            "eff": effect_text(key, p, e, m),
            "durMs": dur_ms or "", "dur": dur_tx, "aetMs": aet_ms or "", "aet": fmt_ms(aet_ms),
            "fx": num(e.get("animation"), -1) if (e.get("animation") or "").strip() else "",
            "snd": num(e.get("sound"), -1) if (e.get("sound") or "").strip() else "",
            "learn": [{"t": l, "s": s} for l, s in learn_lines(key, name, pid, lv, e_class)],
            "note": (p.get("notes") or "").strip(),
            "det": " · ".join(detail),
            "mb": mobs, "pills": pills,
        })
    out.sort(key=lambda s: (s["cl"], s["lv"], s["n"].lower()))

    gifs = fx_gifs()
    fxg = {s["fx"]: gifs[s["fx"]] for s in out if isinstance(s["fx"], int) and s["fx"] in gifs}

    classes = sorted({s["c"] for s in out})
    opts = "".join(f'<option value="{html.escape(c)}">{html.escape(c)}</option>' for c in classes)
    page = HEAD.format(title="Spells", css=CHROME_CSS) + nav("spells") + f"""
<style>
  #tbl td:nth-child(1) {{ min-width: 240px; }}
  #tbl td:nth-child(8) {{ min-width: 140px; }}
  #tbl td:nth-child(12) {{ min-width: 300px; }}
  td.fx {{ text-align: center; }}
  .fxg {{ display: block; margin: 0 auto 2px; image-rendering: pixelated; max-width: 72px; height: auto; }}
</style>
<div class="wrap">
  <header class="hero">
    <p class="kicker">Project1998 · database</p>
    <h1>Spells &amp; Skills</h1>
    <p class="lede">Every spell and skill the server knows, with the level, mana, effect, durations and
    per-class learn costs the server itself enforces — including who actually teaches it (trainers, the
    Sage, the Dog Linguists, quests) and which mobs cast a spell of the same name (with their own mob-tuned
    numbers). Lv is the level <em>your own class</em> learns it at; the Learn column carries the other
    classes. Hover a learn line for its source. <code>fx</code> is the Effect.tbl animation id
    (audition in game with <code>@efx &lt;id&gt;</code>, or click one to watch it on the
    <a href="effects.html">4.95 Effect Table</a>). Era toggles are read at generation time.</p>
  </header>
  <div class="toolbar">
    <input id="q" type="search" placeholder="Filter — name, key, effect, mob, teacher…" aria-label="Filter spells">
    <select id="cls" aria-label="Class filter"><option value="">All classes</option>{opts}</select>
    <span class="count" id="count"></span>
  </div>
  <div class="tablewrap"><table id="tbl">
    <thead><tr><th data-s="n">Spell</th><th data-s="c">Class</th><th data-s="lv">Lv</th><th data-s="mk">Rank</th>
    <th data-s="al">Align</th><th data-s="mana">Mana</th><th data-s="cat">Category</th><th data-s="eff">Effect</th>
    <th data-s="durMs">Duration</th><th data-s="aetMs">Aether</th>
    <th data-s="fx">FX</th><th>Learn / source</th></tr></thead>
    <tbody id="rows"></tbody>
  </table></div>
""" + jsdata("DATA", out) + jsdata("FXG", fxg) + """
<script>
const tbody = document.getElementById('rows'), q = document.getElementById('q'),
      cls = document.getElementById('cls'), count = document.getElementById('count'),
      toolbar = document.querySelector('.toolbar'), twrap = document.querySelector('.tablewrap');
let sortKey = null, sortDir = 1;
function headTop(){ document.documentElement.style.setProperty('--thead-top', toolbar.offsetHeight + 'px'); }
headTop(); addEventListener('resize', headTop);
function snapTop(){ const y = twrap.offsetTop - toolbar.offsetHeight; if (scrollY > y) scrollTo(0, y); }
function fxCell(s){
  if (typeof s.fx !== 'number' || s.fx <= 0) return s.fx;
  const g = FXG[s.fx];
  return `<a href="effects.html#csv${s.fx}">${g ? `<img class="fxg" loading="lazy" src="${g}" alt="">` : ''}${s.fx}</a>`;
}
function esc(s){ return String(s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }
function blob(s){
  return (s.n + ' ' + s.k + ' ' + s.cat + ' ' + s.note + ' ' + s.eff + ' ' + s.det + ' ' +
          s.rk + ' ' + s.pills.join(' ') + ' ' + s.learn.map(l => l.t).join(' ') + ' ' + s.mb.join(' ')).toLowerCase();
}
function castBy(s){
  if (!s.mb.length) return '';
  const head = s.mb.slice(0, 4).map(esc).join(', '), more = s.mb.length - 4;
  return `<span class="sub">cast by ${s.mb.length} mob${s.mb.length > 1 ? 's' : ''}: ${head}${more > 0 ? ` +${more} more` : ''}</span>`;
}
function render(){
  const needle = q.value.trim().toLowerCase(), c = cls.value;
  let rows = DATA.filter(s => (!c || s.c === c) && (!needle || blob(s).includes(needle)));
  if (sortKey) rows = rows.slice().sort((a,b) => {
    const x = a[sortKey], y = b[sortKey];
    return (typeof x === 'number' && typeof y === 'number' ? x - y : String(x).localeCompare(String(y))) * sortDir;
  });
  tbody.innerHTML = rows.map(s => `<tr>
    <td><span class="nm">${esc(s.n)}</span>${s.pills.map(p => ` <span class="pill">${esc(p)}</span>`).join('')}<span class="k">${esc(s.k)} · #${s.id}</span>${s.note ? `<span class="sub">${esc(s.note)}</span>` : ''}${s.det ? `<span class="sub">${esc(s.det)}</span>` : ''}${castBy(s)}</td>
    <td>${esc(s.c)}${s.cb ? `<span class="k">${esc(s.cb)} subpath</span>` : ''}</td>
    <td class="n">${s.lv || ''}</td><td>${esc(s.rk)}</td>
    <td>${esc(s.al)}</td><td class="n">${s.mana}</td><td>${esc(s.cat)}</td>
    <td>${esc(s.eff)}</td><td class="n">${esc(s.dur)}</td><td class="n">${esc(s.aet)}</td>
    <td class="fx"${(typeof s.snd === 'number' && s.snd >= 0) ? ` title="sound ${s.snd}"` : ''}>${fxCell(s)}</td>
    <td class="sub">${s.learn.map(l => `<span${l.s ? ` title="${esc(l.s)}"` : ''}>${esc(l.t)}</span>`).join('<br>')}</td></tr>`).join('');
  count.textContent = rows.length + ' of ' + DATA.length;
}
q.addEventListener('input', () => { render(); snapTop(); });
cls.addEventListener('change', () => { render(); snapTop(); });
document.querySelectorAll('th[data-s]').forEach(th => th.addEventListener('click', () => {
  const k = th.dataset.s;
  sortDir = (sortKey === k) ? -sortDir : 1; sortKey = k;
  document.querySelectorAll('th').forEach(t => t.classList.remove('sorted-asc','sorted-desc'));
  th.classList.add(sortDir > 0 ? 'sorted-asc' : 'sorted-desc');
  render();
}));
render();
</script>
""" + FOOT
    io.open(os.path.join(SITE, "spells.html"), "w", encoding="utf-8").write(page)
    return len(out)

# ---------------------------------------------------------------- items
def build_items():
    icons = sheet("item-icons")
    # Reverse the drop table: item key -> [mob names]
    dropped = {}
    mobnames = {r["Identifier"]: r["Description"] for r in rows("mobs.csv")}
    for r in rows("MobDrops.csv"):
        for lootcol in ("Loot", "RareLoot"):
            for part in (r.get(lootcol) or "").split("|"):
                bits = part.split(":")
                if bits[0]:
                    dropped.setdefault(bits[0], set()).add(mobnames.get(r["MobKey"], r["MobKey"]))

    out = []
    for r in rows("Items.csv"):
        key, name = r["ItmIdentifier"], r["ItmDescription"]
        if not key:
            continue
        t = num(r["ItmType"])
        dmg = ""
        if num(r["ItmMaximumSDamage"]):
            dmg = f"{r['ItmMinimumSDamage']}–{r['ItmMaximumSDamage']}"
            if num(r["ItmMaximumLDamage"]):
                dmg += f" / {r['ItmMinimumLDamage']}–{r['ItmMaximumLDamage']}"
        out.append({
            "id": num(r["ItmId"]), "k": key, "n": name,
            "t": TYPE_NAMES.get(t, f"type {t}"),
            "c": path_name(num(r["ItmPthId"])) if num(r["ItmPthId"]) else "",
            "lv": num(r["ItmLevel"]), "mk": num(r["ItmMark"]),
            "dmg": dmg, "ac": num(r["ItmArmor"]), "hit": num(r["ItmHit"]), "dam": num(r["ItmDam"]),
            "vita": num(r["ItmVita"]), "mana": num(r["ItmMana"]),
            "mgt": num(r["ItmMight"]), "wil": num(r["ItmWill"]), "grc": num(r["ItmGrace"]),
            "buy": num(r["ItmBuyPrice"]), "sell": num(r["ItmSellPrice"]),
            "ic": num(r["ItmIcon"]),
            "drops": sorted(dropped.get(key, []))[:6],
        })
    out.sort(key=lambda i: (i["t"], i["lv"], i["n"].lower()))

    types = sorted({i["t"] for i in out})
    opts = "".join(f'<option value="{html.escape(t)}">{html.escape(t)}</option>' for t in types)
    has_icons = icons is not None
    page = HEAD.format(title="Items", css=CHROME_CSS) + nav("items") + f"""
<div class="wrap">
  <header class="hero">
    <p class="kicker">Project1998 · database</p>
    <h1>Items</h1>
    <p class="lede">Every item in the registry — stats, requirements, prices and the mobs that drop it,
    straight from the server's data files.</p>
  </header>
  <div class="toolbar">
    <input id="q" type="search" placeholder="Filter — name, key, dropped-by…" aria-label="Filter items">
    <select id="typ" aria-label="Type filter"><option value="">All types</option>{opts}</select>
    <span class="count" id="count"></span>
  </div>
  <div class="tablewrap"><table>
    <thead><tr>{'<th></th>' if has_icons else ''}<th data-s="n">Item</th><th data-s="t">Type</th><th data-s="c">Class</th>
    <th data-s="lv">Lv</th><th data-s="dmg">Damage</th><th data-s="ac">AC</th><th data-s="dam">Dam</th><th data-s="hit">Hit</th>
    <th data-s="vita">Vita</th><th data-s="mana">Mana</th><th data-s="buy">Buy</th><th data-s="sell">Sell</th>
    <th>Dropped by</th></tr></thead>
    <tbody id="rows"></tbody>
  </table></div>
""" + jsdata("DATA", out) + jsdata("ICONS", icons or {}) + f"<script>const HAS_ICONS = {str(has_icons).lower()};</script>" + """
<script>
const tbody = document.getElementById('rows'), q = document.getElementById('q'),
      typ = document.getElementById('typ'), count = document.getElementById('count');
let sortKey = null, sortDir = 1, shown = 400;
function esc(s){ return String(s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }
function icon(ic){
  if (!HAS_ICONS) return '';
  const pos = ICONS[ic];
  if (!pos) return '<td></td>';
  return `<td><span class="spr" style="background-image:url(img/item-icons.png);background-position:-${pos[0]}px -${pos[1]}px"></span></td>`;
}
function filt(){
  const needle = q.value.trim().toLowerCase(), t = typ.value;
  let rows = DATA.filter(i => (!t || i.t === t) &&
    (!needle || (i.n + ' ' + i.k + ' ' + i.drops.join(' ')).toLowerCase().includes(needle)));
  if (sortKey) rows = rows.slice().sort((a,b) => {
    const x = a[sortKey], y = b[sortKey];
    return (typeof x === 'number' && typeof y === 'number' ? x - y : String(x).localeCompare(String(y))) * sortDir;
  });
  return rows;
}
function render(){
  const rows = filt();
  tbody.innerHTML = rows.slice(0, shown).map(i => `<tr>
    ${icon(i.ic)}
    <td><span class="nm">${esc(i.n)}</span><span class="k">${esc(i.k)} · #${i.id}</span></td>
    <td>${esc(i.t)}</td><td>${esc(i.c)}</td><td class="n">${i.lv || ''}</td>
    <td class="n">${i.dmg}</td><td class="n">${i.ac || ''}</td><td class="n">${i.dam || ''}</td><td class="n">${i.hit || ''}</td>
    <td class="n">${i.vita || ''}</td><td class="n">${i.mana || ''}</td>
    <td class="n">${i.buy ? i.buy.toLocaleString() : ''}</td><td class="n">${i.sell ? i.sell.toLocaleString() : ''}</td>
    <td class="sub">${i.drops.map(esc).join(', ')}</td></tr>`).join('')
    + (rows.length > shown ? `<tr><td colspan="14"><button id="more" style="font:inherit;padding:6px 14px;cursor:pointer">Show ${rows.length - shown} more…</button></td></tr>` : '');
  count.textContent = Math.min(shown, rows.length) + ' shown of ' + rows.length + ' matching (' + DATA.length + ' total)';
  const m = document.getElementById('more');
  if (m) m.addEventListener('click', () => { shown += 800; render(); });
}
q.addEventListener('input', () => { shown = 400; render(); });
typ.addEventListener('change', () => { shown = 400; render(); });
document.querySelectorAll('th[data-s]').forEach(th => th.addEventListener('click', () => {
  const k = th.dataset.s;
  sortDir = (sortKey === k) ? -sortDir : 1; sortKey = k;
  document.querySelectorAll('th').forEach(t => t.classList.remove('sorted-asc','sorted-desc'));
  th.classList.add(sortDir > 0 ? 'sorted-asc' : 'sorted-desc');
  render();
}));
render();
</script>
""" + FOOT
    io.open(os.path.join(SITE, "items.html"), "w", encoding="utf-8").write(page)
    return len(out)

# ---------------------------------------------------------------- mobs
def _atlas_names(fname):
    """Normalized name set from a committed tools/data atlas list (None when the file is absent)."""
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", fname)
    if not os.path.exists(p):
        print(f"warning: {fname} not found; atlas cross-reference degraded", file=sys.stderr)
        return None
    with io.open(p, encoding="utf-8") as f:
        rdr = csv.DictReader(l for l in f if not l.startswith("#"))
        return {re.sub(r"[^a-z0-9]", "", r["name"].lower()) for r in rdr}

# Bespoke per-mob mechanics that live in code, not CSVs — each with its one source named.
MOB_NOTES = {
    "ice_beast": ("docile until lured — unleashed (no chase leash) and one-shots for ~300k; "
                  "it melts when led onto the lava row", "Server/World.cs Ice Beast questline (map 3040)"),
    "sute": ("bespoke quest-boss AI: at ≤25% HP it self-heals 200, at most once per 20s on a 1-in-12 roll",
             "Server/SuteAi.cs"),
    "spy_hwan": ("its Spawns.csv row is excluded at load — the Spy-subpath storyline he serves is unbuilt",
                 "Server/Content.cs ExcludedSpawnMobIds"),
}

def build_mobs():
    sprites = sheet("mob-sprites")
    itemnames = {r["ItmIdentifier"]: clean_name(r["ItmDescription"]) for r in rows("Items.csv")}
    def item_name(k):
        return itemnames.get(k, k.replace("_", " "))
    def pctx(v):
        try: return f"{float(v):g}"
        except ValueError: return v

    # Drops mirror Content.LoadMobDrops/RollDrops: Loot is item:MaxAmount:RatePercent (amount rolled
    # 1..Max, each line independent; malformed lines skipped); RareLoot is item:RatePercent — TWO fields,
    # amount always 1, and at most ONE rare drops per kill (first listed line to hit wins).
    drops = {}
    for r in rows("MobDrops.csv"):
        entries = []
        for part in (r.get("Loot") or "").split("|"):
            bits = part.split(":")
            if len(bits) != 3 or not bits[0]:
                continue
            nm = "gold" if bits[0] == "GOLD" else item_name(bits[0])
            amt = num(bits[1], 1)
            entries.append({"t": (f"1–{amt:,} " if amt > 1 else "") + f"{nm} ({pctx(bits[2])}%)", "r": 0})
        for part in (r.get("RareLoot") or "").split("|"):
            bits = part.split(":")
            if len(bits) != 2 or not bits[0]:
                continue
            nm = "gold" if bits[0] == "GOLD" else item_name(bits[0])
            entries.append({"t": f"{nm} ({pctx(bits[1])}%)", "r": 1})
        if entries:
            drops[r["MobKey"]] = entries

    # Casts: MobSpells.csv rows in FILE ORDER (the server walks them in order, first roll that passes
    # wins). Per the file's own header: timer rows re-roll every 333ms once off cooldown, so EveryMs is
    # the real pacing and Chance only shifts WHEN; onhit rows are a true 1-in-N per landed blow.
    casts = {}
    for r in rows("MobSpells.csv"):
        if not (r.get("MobKey") and r.get("Name")):
            continue
        eff, amount, dur = (r.get("Effect") or "").strip(), num(r.get("Amount")), num(r.get("DurationMs"))
        per_tick = num(r.get("PerTick"))
        bits, title = [], ""
        if eff == "damage":
            bits.append(f"{amount:,} damage")
        elif eff == "poison":
            if per_tick:
                tmin, tmax = num(r.get("TickMinMs")), num(r.get("TickMaxMs"))
                bits.append(f"poison {per_tick:,}/tick" + (f" every {fmt_ms(tmin)}–{fmt_ms(tmax)}" if tmax else ""))
            else:
                bits.append(f"poison {amount:,}/s")
            if dur: bits.append(fmt_ms(dur))
        elif eff == "curse":
            stat = (r.get("Stat") or "").strip()
            bits.append(f"{stat} −{amount}" if stat else "curse")
            if dur: bits.append(fmt_ms(dur))
        elif eff == "blind":
            bits.append(("blind " + fmt_ms(dur) if dur else "blind") + " — no effect on players")
            title = ("Acknowledged gap (Session.MobSpells.cs): no player-blind state exists, so the row "
                     "lands and occupies the blinds slot (cures work) but does not impair you")
        elif eff:
            bits.append(eff)
        if (r.get("Trigger") or "").strip() == "onhit":
            bits.append(f"on hit: 1-in-{num(r.get('Chance'), 1)} per landed blow")
        else:
            if num(r.get("EveryMs")): bits.append(f"every {fmt_ms(num(r['EveryMs']))}")
            if num(r.get("Range")) > 1: bits.append(f"range {num(r['Range'])}")
        casts.setdefault(r["MobKey"], []).append({
            "n": clean_name(r["Name"]), "d": " · ".join(bits),
            "say": clean_name((r.get("Say") or "").strip()), "ti": title})

    # Spawn provenance keyed by MobId (NOT Identifier — six buya_library_mob tiers share a key but spawn
    # on different maps). The server concatenates AreaSpawns + AreaSpawnsTrap + AreaSpawnsCrafting
    # (Content.cs LoadContent) and drops ExcludedSpawnMobIds from Spawns.csv at load.
    excluded = {num(x) for x in _parse_keys(_CONTENT, r"ExcludedSpawnMobIds\s*=\s*new\(\)\s*\{([^}]*)\}",
                                            [], "ExcludedSpawnMobIds") or ()}
    if not excluded:
        m = re.search(r"ExcludedSpawnMobIds\s*=\s*new\(\)\s*\{([^}]*)\}", _CONTENT)
        excluded = {num(x) for x in re.findall(r"\d+", m.group(1))} if m else {729}
    spawn = {}
    def add_spawn(mid, mapid, tag=""):
        nm = maps_by_id.get(mapid, f"map {mapid}")
        spawn.setdefault(mid, {}).setdefault(nm, set())
        if tag: spawn[mid][nm].add(tag)
    for r in rows("Spawns.csv"):
        if num(r["SpnMobId"]) not in excluded:
            add_spawn(num(r["SpnMobId"]), num(r["SpnMapId"]))
    for r in rows("AreaSpawns.csv"):
        add_spawn(num(r["MobId"]), num(r["Map"]))
    for r in rows_opt("AreaSpawnsTrap.csv"):
        add_spawn(num(r["MobId"]), num(r["Map"]), "trap, rare" if num(r.get("RespawnSec")) > 0 else "trap")
    for r in rows_opt("AreaSpawnsCrafting.csv"):
        add_spawn(num(r["MobId"]), num(r["Map"]), "crafting")

    # Ambush bursts: AmbushConfig maps ("90-96;208" lists) fire AmbushBursts tables when a hidden trap is
    # stepped on (Content.LoadAmbushConfig / World.RefillAmbush) — ~19 mobs spawn ONLY this way.
    bursts = {}
    for r in rows_opt("AmbushBursts.csv"):
        ids = {num(x) for x in (r.get("MobIds") or "").split(";") if num(x) > 0}
        bursts.setdefault((r.get("Table") or "").strip(), set()).update(ids)
    def map_list(s):
        out = []
        for part in (s or "").split(";"):
            part = part.strip()
            if "-" in part[1:]:
                lo, hi = part.split("-", 1)
                if lo.strip().isdigit() and hi.strip().isdigit():
                    out.extend(range(int(lo), int(hi) + 1))
            elif part.isdigit():
                out.append(int(part))
        return out
    for r in rows_opt("AmbushConfig.csv"):
        mob_ids = set()
        primary = (r.get("Primary") or "").strip()
        if primary.startswith("burst:"):
            mob_ids |= bursts.get(primary[6:], set())
        elif primary.startswith("single:"):
            mob_ids.add(num(primary[7:]))
        elif primary.startswith("ogre:"):
            parts = primary[5:].split("/")
            mob_ids.add(num(parts[0]))
            if len(parts) >= 3: mob_ids.add(num(parts[1]))
        for col in ("SentryTable", "BigTable"):
            t = (r.get(col) or "").strip()
            if t: mob_ids |= bursts.get(t, set())
        for mid in mob_ids:
            for mp in map_list(r.get("Maps")):
                add_spawn(mid, mp, "ambush")

    # Side tables — each mirrors its loader's own skip rules.
    flees = {r["Identifier"] for r in rows_opt("MobFlees.csv") if (r.get("Flees") or "0").strip() != "0"}
    still = {r["Identifier"] for r in rows_opt("MobStationary.csv") if (r.get("Stationary") or "0").strip() != "0"}
    bosskit = {r["MobKey"]: r for r in rows_opt("MobBosses.csv") if r.get("MobKey")}
    rules = {}
    for r in rows_opt("MobSpawnRules.csv"):
        k = (r.get("MobKey") or "").strip()
        if not k or k == "*":       # '*' is the global HpJitter switch, not a rule
            continue
        if any(num(r.get(c)) > 0 for c in ("MaxAlive", "FleeBelowPct", "SpawnChance", "DeathCooldownSec")) \
                or (r.get("Rooms") or "").strip() or (r.get("CapMaps") or "").strip():
            rules[k] = r
    chatterby = {r["MobKey"]: r for r in rows_opt("MobChatter.csv") if r.get("MobKey")}
    pets = {r["mobKey"]: r for r in rows_opt("Pets.csv") if r.get("mobKey")}
    nodes = {r["NodeMob"]: r for r in rows_opt("HarvestNodes.csv") if r.get("NodeMob")}

    atlas_live = _atlas_names("atlas_monsters.csv")
    atlas_2005 = _atlas_names("atlas_monsters_2005.csv")
    has_atlas = atlas_live is not None or atlas_2005 is not None
    def atlas_flag(name):
        n1 = re.sub(r"[^a-z0-9]", "", name.lower())
        n2 = re.sub(r"[^a-z0-9]", "", re.sub(r"\s*\[[^\]]*\]\s*$", "", name).lower())
        hit_live = atlas_live is not None and (n1 in atlas_live or n2 in atlas_live)
        hit_2005 = atlas_2005 is not None and (n1 in atlas_2005 or n2 in atlas_2005)
        return "both" if hit_live and hit_2005 else "live" if hit_live else "2005" if hit_2005 else ""

    out = []
    for r in rows("mobs.csv"):
        key, name = r["Identifier"], clean_name(r["Description"])
        if not key or key == "test":
            continue
        mid = num(r["MobId"])
        hp = max(1, num(r["Vita"]))            # Content.LoadMobs: hp <= 0 loads as 1
        mind, maxd = num(r["MinDmg"]), num(r["MaxDmg"])
        if mind <= 0: mind = 1                 # …and the damage clamps
        if maxd < mind: maxd = mind
        move = num(r["MobMoveTime"]) or 2500   # 0/absent -> the loader's calm default
        st = (r.get("SpawnTime") or "").strip()
        respawn = num(st) if st != "" and num(st, -1) >= 0 else 180   # DefaultSpawnTimeSec; 0 is real
        beh = (r.get("MobBehavior") or "0").strip()
        prot, will = num(r["MobProtection"]), num(r["Will"])
        deflect = int(100 - (0.9 ** prot) * 100 + 0.5) if prot > 0 else 0
        if prot >= 200:
            prot_t = "immune — deflects ~100% of fail-able spells"
        elif prot > 0 or will > 0:
            prot_t = f"deflects ≈{deflect}% of fail-able spells"
            if will: prot_t += f" · Will {will} adds up to +{will // 10} prot vs lower-Will casters"
        else:
            prot_t = ""

        pills, sub = [], []
        atl = atlas_flag(name) if has_atlas else "n/a"
        if has_atlas and not atl:
            pills.append({"t": "no atlas", "ti": "Not documented on NexusAtlas — neither the live site "
                          "(2026, documents modern NexusTK) nor the ~2005 Wayback archive. Likely "
                          "RTK-added rather than era-original."})
        myth = key in bosskit
        if myth:
            b = bosskit[key]
            heal, hc = num(b.get("HealAmount")), max(2, num(b.get("HealChance"), 2))
            pb, ls = num(b.get("ParaBreakChance")), num(b.get("LastStandMs"))
            pills.append({"t": "mythic", "ti": "Mythic boss — carries the MobBosses.csv survival kit "
                          "(and player weapons roll their Large damage range against it)"})
            bits = []
            if heal: bits.append(f"a lethal blow heals it {heal:,} ({hc - 1}-in-{hc}) unless overkilled "
                                 f"(dmg ≥ HP+{heal:,} kills through)")
            if ls: bits.append(f"first brink: {fmt_ms(ls)} frozen last stand")
            if pb and heal: bits.append(f"heals through paralysis 1-in-{pb} per 3s")
            sub.append({"t": "boss kit: " + " · ".join(bits),
                        "ti": "game-data/MobBosses.csv · World.cs lethal-blow ladder: last stand → overkill → save roll"})
        elif r.get("MobIsBoss") == "1":
            pills.append({"t": "boss", "ti": "MobIsBoss — player weapons roll their Large damage range "
                          "against it (no mythic survival kit)"})
        if beh == "1":
            pills.append({"t": "aggro", "ti": "Attacks on sight (MobBehavior 1)"})
        if beh == "2":
            pills.append({"t": "dummy", "ti": "Inert training target — never fights back (MobBehavior 2)"})
        if key in flees:
            pills.append({"t": "prey", "ti": "Runs away instead of fighting when swung at (MobFlees.csv)"})
        if key in still:
            pills.append({"t": "still", "ti": "Never takes a step (MobStationary.csv)"})
        if key in rules:
            ru = rules[key]
            bits = []
            if num(ru.get("SpawnChance")) > 1: bits.append(f"1-in-{num(ru['SpawnChance'])} roll per spawn-point refill")
            if num(ru.get("DeathCooldownSec")) > 0: bits.append(f"{fmt_ms(num(ru['DeathCooldownSec']) * 1000)} cooldown after a kill")
            if num(ru.get("MaxAlive")) > 0: bits.append(f"max {num(ru['MaxAlive'])} alive")
            if (ru.get("CapMaps") or "").strip(): bits.append("capped per map")
            if bits:
                pills.append({"t": "rare", "ti": "Rare spawn (MobSpawnRules.csv / World.cs refill gate)"})
                sub.append({"t": "rare spawn: " + " · ".join(bits), "ti": "game-data/MobSpawnRules.csv"})
            if num(ru.get("FleeBelowPct")) > 0:
                sub.append({"t": f"breaks off and flees below {num(ru['FleeBelowPct'])}% HP",
                            "ti": "game-data/MobSpawnRules.csv FleeBelowPct"})
        if key in pets:
            p = pets[key]
            pills.append({"t": "summon", "ti": "Spawned by a spell, not the world (Pets.csv)"})
            if p.get("key") == "cotw_giasomo_bird_poet":
                sub.append({"t": "summoned only by the Giasomo stick's on-swing proc · lasts 5m",
                            "ti": "game-data/Pets.csv + WeaponProcs.csv; Server/Content.cs PetSpells"})
            else:
                cd = num(p.get("cooldownMs"))
                sub.append({"t": f"Poet summon — Call of the Wild lv {num(p.get('level'))} · {num(p.get('mana'))} mana"
                               + (f" · {fmt_ms(cd)} cooldown" if cd else "")
                               + " · lasts 5m · cap 4 (6 at lv 90, 8 at 99)",
                            "ti": "game-data/Pets.csv; Server/Content.cs PetCapFor; expiry in World.Tick"})
        if key in nodes:
            nd = nodes[key]
            tools = " or ".join(item_name(t) for t in (nd.get("Tools") or "").split("|") if t)
            yield_tx = " / ".join(f"{item_name(b.split(':')[0])} {pctx(b.split(':')[1])}" for b in (nd.get("Yield") or "").split("|") if ":" in b)
            bonus_tx = " / ".join(f"{item_name(b.split(':')[0])} {pctx(b.split(':')[1])}%" for b in (nd.get("Bonus") or "").split("|") if ":" in b)
            brk = (nd.get("BreakChance") or "").strip()
            t = f"gathering node — drop a {tools} on it ({nd.get('Skill')}): 1 + {num(nd.get('Rolls'))} coin-flip yields, weighted {yield_tx}"
            if bonus_tx: t += f" · bonus roll {bonus_tx}"
            if brk and brk != "0": t += f" · may snap the tool (1-in-{brk.replace('|', '/')}+dmg)"
            pills.append({"t": "node", "ti": "Harvest node, not a fight (HarvestNodes.csv)"})
            sub.append({"t": t, "ti": "game-data/HarvestNodes.csv · Session.Harvest.cs — on 4.95 you harvest "
                        "by DROPPING the tool beside the node, and it never leaves your bag"})
        if key in chatterby:
            ch = chatterby[key]
            lines = [l for l in (ch.get("Lines") or "").split("|") if l]
            shown = " ".join(f"“{clean_name(l)}”" for l in lines[:3]) + (f" +{len(lines) - 3} more" if len(lines) > 3 else "")
            sub.append({"t": f"chatters: {shown} (1-in-{num(ch.get('Chance'), 1)} per move tick)",
                        "ti": "game-data/MobChatter.csv — RTK's 'custom mob AI' idle flavour"})
        if key in MOB_NOTES:
            sub.append({"t": MOB_NOTES[key][0], "ti": MOB_NOTES[key][1]})

        maps = [{"t": nm, "g": ", ".join(sorted(tags))} for nm, tags in sorted(spawn.get(mid, {}).items())]
        if any(m["g"] and "ambush" in m["g"] for m in maps) and not any(not m["g"] for m in maps):
            pills.append({"t": "ambush", "ti": "Spawns only from stepped-on ambush traps "
                          "(AmbushConfig/AmbushBursts.csv, World.RefillAmbush)"})
        out.append({
            "k": key, "id": mid, "n": name, "lk": num(r["MobLook"]), "col": num(r["MobLookColor"]),
            "lv": num(r["Level"]), "hp": hp, "xp": num(r["Exp"]),
            "dmg": f"{mind:,}–{maxd:,}", "dmgN": maxd,
            "hit": num(r["MobHit"]), "ac": num(r["MobArmor"]),
            "prot": prot, "protT": prot_t,
            "mv": move, "mvT": fmt_ms(move),
            "rs": respawn, "rsT": fmt_ms(respawn * 1000) if respawn > 0 else "next tick",
            "agg": beh == "1", "boss": r.get("MobIsBoss") == "1", "myth": myth,
            "rare": key in rules and any(num(rules[key].get(c)) > 0 for c in ("SpawnChance", "DeathCooldownSec", "MaxAlive")),
            "atl": atl, "pills": pills, "sub": sub,
            "maps": maps, "drops": drops.get(key, []), "sp": casts.get(key, []),
        })
    out.sort(key=lambda m: (m["lv"], m["n"].lower(), m["id"]))

    has_sprites = sprites is not None
    page = HEAD.format(title="Mobs", css=CHROME_CSS) + nav("mobs") + """
<div class="wrap">
  <header class="hero">
    <p class="kicker">Project1998 · database</p>
    <h1>Mobs</h1>
    <p class="lede">Every creature in the registry — stats, where it spawns, what it drops, and what it
    casts, straight from the server's data files. ★ marks rare loot.</p>
  </header>
  <div class="toolbar">
    <input id="q" type="search" placeholder="Filter — name, map, drop…" aria-label="Filter mobs">
    <select id="kind" aria-label="Kind filter"><option value="">All</option>
      <option value="boss">Bosses</option><option value="agg">Aggressive</option></select>
    <span class="count" id="count"></span>
  </div>
  <div class="tablewrap"><table>
    <thead><tr>""" + ("<th></th>" if has_sprites else "") + """<th data-s="n">Mob</th><th data-s="lv">Lv</th>
    <th data-s="hp">Vita</th><th data-s="xp">Exp</th><th data-s="dmg">Damage</th><th data-s="ac">AC</th>
    <th>Spawns</th><th>Drops</th><th>Casts</th></tr></thead>
    <tbody id="rows"></tbody>
  </table></div>
""" + jsdata("DATA", out) + jsdata("SPRITES", sprites or {}) + f"<script>const HAS_SPRITES = {str(has_sprites).lower()};</script>" + """
<script>
const tbody = document.getElementById('rows'), q = document.getElementById('q'),
      kind = document.getElementById('kind'), count = document.getElementById('count');
let sortKey = null, sortDir = 1, shown = 300;
function esc(s){ return String(s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }
function spr(m){
  if (!HAS_SPRITES) return '';
  const pos = SPRITES[m.lk + ':' + m.col] || SPRITES[m.lk + ':0'];
  if (!pos) return '<td></td>';
  return `<td><span class="spr" style="width:${pos[2]}px;height:${pos[3]}px;background-image:url(img/mob-sprites.png);background-position:-${pos[0]}px -${pos[1]}px"></span></td>`;
}
function render(){
  const needle = q.value.trim().toLowerCase(), f = kind.value;
  let rows = DATA.filter(m => (f !== 'boss' || m.boss) && (f !== 'agg' || m.agg) &&
    (!needle || (m.n + ' ' + m.k + ' ' + m.maps.join(' ') + ' ' + m.drops.join(' ')).toLowerCase().includes(needle)));
  if (sortKey) rows = rows.slice().sort((a,b) => {
    const x = a[sortKey], y = b[sortKey];
    return (typeof x === 'number' && typeof y === 'number' ? x - y : String(x).localeCompare(String(y))) * sortDir;
  });
  tbody.innerHTML = rows.slice(0, shown).map(m => `<tr>
    ${spr(m)}
    <td><span class="nm">${esc(m.n)}</span>${m.boss ? ' <span class="pill">boss</span>' : ''}${m.agg ? ' <span class="pill">aggro</span>' : ''}<span class="k">${esc(m.k)}</span></td>
    <td class="n">${m.lv || ''}</td><td class="n">${m.hp.toLocaleString()}</td><td class="n">${m.xp.toLocaleString()}</td>
    <td class="n">${m.dmg}</td><td class="n">${m.ac || ''}</td>
    <td class="sub">${m.maps.map(esc).join(', ')}</td>
    <td class="sub">${m.drops.map(esc).join(', ')}</td>
    <td class="sub">${m.sp.map(esc).join(', ')}</td></tr>`).join('')
    + (rows.length > shown ? `<tr><td colspan="10"><button id="more" style="font:inherit;padding:6px 14px;cursor:pointer">Show ${rows.length - shown} more…</button></td></tr>` : '');
  count.textContent = Math.min(shown, rows.length) + ' shown of ' + rows.length + ' matching (' + DATA.length + ' total)';
  const b = document.getElementById('more');
  if (b) b.addEventListener('click', () => { shown += 600; render(); });
}
q.addEventListener('input', () => { shown = 300; render(); });
kind.addEventListener('change', () => { shown = 300; render(); });
document.querySelectorAll('th[data-s]').forEach(th => th.addEventListener('click', () => {
  const k = th.dataset.s;
  sortDir = (sortKey === k) ? -sortDir : 1; sortKey = k;
  document.querySelectorAll('th').forEach(t => t.classList.remove('sorted-asc','sorted-desc'));
  th.classList.add(sortDir > 0 ? 'sorted-asc' : 'sorted-desc');
  render();
}));
render();
</script>
""" + FOOT
    io.open(os.path.join(SITE, "mobs.html"), "w", encoding="utf-8").write(page)
    return len(out)

if __name__ == "__main__":
    print("spells:", build_spells())
    print("items:", build_items())
    print("mobs:", build_mobs())
