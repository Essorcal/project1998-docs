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
  <a href="patch-notes.html">Notes</a>
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
  .sitenav { max-width: 1100px; margin: 0 auto; padding: 14px 24px 0;
    display: flex; gap: 16px; align-items: baseline; font-size: 14px; flex-wrap: wrap; }
  .sitenav a { color: var(--ink-soft); text-decoration: none; }
  .sitenav a:hover { color: var(--accent-ink); text-decoration: underline; }
  .sitenav .brand { font-family: "Gowun Batang", Georgia, serif; font-weight: 700;
    color: var(--ink); margin-right: auto; font-size: 16px; }
  .sitenav a[aria-current="page"] { color: var(--accent-ink); font-weight: 600; }
  .wrap { max-width: 1100px; margin: 0 auto; padding: 0 24px 96px; }
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
  .tablewrap { overflow-x: auto; margin-top: 6px; }
  table { border-collapse: collapse; width: 100%; font-size: 13.5px; }
  th, td { text-align: left; padding: 6px 10px; border-bottom: 1px solid var(--rule-soft); vertical-align: top; }
  th { font-family: "IBM Plex Mono", ui-monospace, monospace; font-size: 11px;
    letter-spacing: 0.07em; text-transform: uppercase; color: var(--ink-faint); font-weight: 500;
    position: sticky; top: 55px; background: var(--ground); cursor: pointer; white-space: nowrap; }
  th.sorted-asc::after { content: " ▲"; } th.sorted-desc::after { content: " ▼"; }
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
paths = {num(r["PthId"]): r["PthMark0"] for r in rows("Paths.csv") if r.get("PthMark0")}
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
def build_spells():
    params = {r["key"]: r for r in rows("SpellParams.csv")}
    effects = {r["key"]: r for r in rows("spell_effects.csv")}
    levels = {r["key"]: num(r["level"]) for r in rows("SpellLevels.csv")}
    costs = {}
    for r in rows("SpellLearnCosts.csv"):
        items = [f"{r[f'item{i}'].replace('_', ' ')} x{r[f'amt{i}']}"
                 for i in (1, 2, 3, 4) if r.get(f"item{i}")]
        gold = num(r.get("gold"))
        parts = ([f"{gold:,} gold"] if gold else []) + items
        costs[(r["key"], num(r["pathId"]))] = ", ".join(parts)

    out = []
    for r in rows("Spells.csv"):
        key, name = r["SplIdentifier"], r["SplDescription"]
        if not key or key.startswith("=="):
            continue
        pid = num(r["SplPthId"])
        p, e = params.get(key, {}), effects.get(key, {})
        mana = p.get("mana") or e.get("mana") or ""
        formula = ""
        if p.get("base") or p.get("coeff"):
            formula = f"{p.get('base') or 0} + {p.get('coeff') or 0}×Will"
        out.append({
            "k": key, "n": name, "c": path_name(pid), "cl": pid,
            "lv": levels.get(key, num(r["SplLevel"])), "mk": num(r["SplMark"]),
            "al": ALIGN.get(num(r["SplAlignment"], -1), ""),
            "mana": num(mana) if str(mana).strip() else "",
            "cat": (p.get("category") or e.get("archetype") or "").strip(),
            "fx": num(e.get("animation"), -1) if (e.get("animation") or "").strip() else "",
            "form": formula,
            "cost": costs.get((key, pid), "") or costs.get((key, 99), ""),
            "note": (p.get("notes") or "").strip(),
            "skill": r.get("SplType") == "5",
        })
    out.sort(key=lambda s: (s["cl"], s["lv"], s["n"].lower()))

    classes = sorted({s["c"] for s in out})
    opts = "".join(f'<option value="{html.escape(c)}">{html.escape(c)}</option>' for c in classes)
    page = HEAD.format(title="Spells", css=CHROME_CSS) + nav("spells") + f"""
<div class="wrap">
  <header class="hero">
    <p class="kicker">Project1998 · database</p>
    <h1>Spells &amp; Skills</h1>
    <p class="lede">Every spell and skill the server teaches, with class, level, mana, formulas and learn
    costs merged from the server's own data files. <code>fx</code> is the Effect.tbl animation id
    (audition in game with <code>@efx &lt;id&gt;</code>, or click one to watch it on the <a href="effects.html">4.95 Effect Table</a>).</p>
  </header>
  <div class="toolbar">
    <input id="q" type="search" placeholder="Filter — name, key, category…" aria-label="Filter spells">
    <select id="cls" aria-label="Class filter"><option value="">All classes</option>{opts}</select>
    <span class="count" id="count"></span>
  </div>
  <div class="tablewrap"><table id="tbl">
    <thead><tr><th data-s="n">Spell</th><th data-s="c">Class</th><th data-s="lv">Lv</th><th data-s="mk">Mark</th>
    <th data-s="al">Align</th><th data-s="mana">Mana</th><th data-s="cat">Category</th><th data-s="form">Formula</th>
    <th data-s="fx">FX</th><th data-s="cost">Learn cost</th></tr></thead>
    <tbody id="rows"></tbody>
  </table></div>
""" + jsdata("DATA", out) + """
<script>
const tbody = document.getElementById('rows'), q = document.getElementById('q'),
      cls = document.getElementById('cls'), count = document.getElementById('count');
let sortKey = null, sortDir = 1;
function esc(s){ return String(s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }
function render(){
  const needle = q.value.trim().toLowerCase(), c = cls.value;
  let rows = DATA.filter(s => (!c || s.c === c) &&
    (!needle || (s.n + ' ' + s.k + ' ' + s.cat + ' ' + s.note).toLowerCase().includes(needle)));
  if (sortKey) rows = rows.slice().sort((a,b) => {
    const x = a[sortKey], y = b[sortKey];
    return (typeof x === 'number' && typeof y === 'number' ? x - y : String(x).localeCompare(String(y))) * sortDir;
  });
  tbody.innerHTML = rows.map(s => `<tr>
    <td><span class="nm">${esc(s.n)}</span>${s.skill ? ' <span class="pill">skill</span>' : ''}<span class="k">${esc(s.k)}</span>${s.note ? `<span class="sub">${esc(s.note)}</span>` : ''}</td>
    <td>${esc(s.c)}</td><td class="n">${s.lv || ''}</td><td class="n">${s.mk || ''}</td>
    <td>${esc(s.al)}</td><td class="n">${s.mana}</td><td>${esc(s.cat)}</td>
    <td>${esc(s.form)}</td><td class="n">${(typeof s.fx === 'number' && s.fx > 0) ? `<a href="effects.html#csv${s.fx}">${s.fx}</a>` : s.fx}</td><td class="sub">${esc(s.cost)}</td></tr>`).join('');
  count.textContent = rows.length + ' of ' + DATA.length;
}
q.addEventListener('input', render); cls.addEventListener('change', render);
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
def build_mobs():
    sprites = sheet("mob-sprites")
    drops = {}
    itemnames = {r["ItmIdentifier"]: r["ItmDescription"] for r in rows("Items.csv")}
    for r in rows("MobDrops.csv"):
        entries = []
        for lootcol, rare in (("Loot", False), ("RareLoot", True)):
            for part in (r.get(lootcol) or "").split("|"):
                bits = part.split(":")
                if bits[0]:
                    nm = itemnames.get(bits[0], bits[0].replace("_", " "))
                    chance = bits[2] if len(bits) > 2 else ""
                    entries.append(nm + (f" ({chance}%)" if chance else "") + (" ★" if rare else ""))
        drops[r["MobKey"]] = entries

    spells = {}
    for r in rows("MobSpells.csv"):
        if r.get("MobKey") and r.get("Name"):
            spells.setdefault(r["MobKey"], []).append(r["Name"])

    spawn_maps = {}
    mob_by_id = {num(r["MobId"]): r["Identifier"] for r in rows("mobs.csv")}
    for r in rows("Spawns.csv"):
        k = mob_by_id.get(num(r["SpnMobId"]))
        if k:
            spawn_maps.setdefault(k, set()).add(maps_by_id.get(num(r["SpnMapId"]), f"map {r['SpnMapId']}"))
    for r in rows("AreaSpawns.csv"):
        k = mob_by_id.get(num(r["MobId"]))
        if k:
            spawn_maps.setdefault(k, set()).add(maps_by_id.get(num(r["Map"]), f"map {r['Map']}"))

    bosses = {r["MobKey"] for r in rows("MobBosses.csv")}
    out = []
    for r in rows("mobs.csv"):
        key, name = r["Identifier"], r["Description"]
        if not key or key == "test":
            continue
        out.append({
            "k": key, "n": name, "lk": num(r["MobLook"]), "col": num(r["MobLookColor"]),
            "lv": num(r["Level"]), "hp": num(r["Vita"]), "xp": num(r["Exp"]),
            "dmg": f"{r['MinDmg']}–{r['MaxDmg']}" if num(r["MaxDmg"]) else "",
            "hit": num(r["MobHit"]), "ac": num(r["MobArmor"]), "prot": num(r["MobProtection"]),
            "agg": r.get("MobBehavior") == "1",
            "boss": r.get("MobIsBoss") == "1" or key in bosses,
            "maps": sorted(spawn_maps.get(key, []))[:5],
            "drops": drops.get(key, [])[:8],
            "sp": spells.get(key, [])[:6],
        })
    out.sort(key=lambda m: (m["lv"], m["n"].lower()))

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
