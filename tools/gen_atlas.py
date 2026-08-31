#!/usr/bin/env python3
"""Generate site/atlas.html: the world atlas viewer. CI-safe (CSV data only) — the map images
themselves are local artifacts from tools/local/render_atlas.py, and the page degrades to a
"not rendered yet" note for any map whose image is missing.

Usage: python tools/gen_atlas.py <path-to-game-repo>
"""
import html, io, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_db import rows, num, nav, CHROME_CSS, HEAD, maps_by_id, GAME, SITE  # noqa: E402

def build():
    mapmeta = {num(r["MapId"]): r for r in rows("Maps.csv")}
    maps = []
    for r in rows("map_index.csv"):
        mid = num(r["id"])
        maps.append({"id": mid, "n": r["name"], "xs": num(r["xs"]), "ys": num(r["ys"]),
                     "pvp": mapmeta.get(mid, {}).get("MapPvP") == "1"})

    warps = {}
    for r in rows("Warps.csv"):
        src = num(r["SourceMapId"])
        warps.setdefault(src, []).append(
            [num(r["SourceX"]), num(r["SourceY"]),
             num(r["DestinationMapId"]), num(r["DestinationX"]), num(r["DestinationY"])])

    npcs = {}
    for r in rows("NPCs.csv"):
        if r.get("Enabled", "1") == "0":
            continue
        npcs.setdefault(num(r.get("NpcMapId") or r.get("Map")), []).append(
            [num(r.get("NpcX") or r.get("X")), num(r.get("NpcY") or r.get("Y")),
             r.get("NpcDescription") or r.get("Description") or r.get("NpcIdentifier") or ""])

    mobname = {num(r["MobId"]): (r["Description"] or r["Identifier"]) for r in rows("mobs.csv")}
    spawns = {}
    for r in rows("Spawns.csv"):
        spawns.setdefault(num(r["SpnMapId"]), []).append(
            [num(r["SpnX"]), num(r["SpnY"]), mobname.get(num(r["SpnMobId"]), "?")])
    areas = {}
    for r in rows("AreaSpawns.csv"):
        rect = [num(r["MinX"]), num(r["MinY"]), num(r["MaxX"]), num(r["MaxY"])]
        if rect == [0, 0, 0, 0]:
            continue
        areas.setdefault(num(r["Map"]), []).append(
            rect + [f"{mobname.get(num(r['MobId']), '?')} ×{r['Count']}"])

    def js(name, obj):
        return f"<script>const {name} = {json.dumps(obj, separators=(',', ':'), ensure_ascii=False)};</script>"

    extra_css = """
  .layout { display: grid; grid-template-columns: 270px 1fr; gap: 16px; margin-top: 16px; }
  @media (max-width: 800px) { .layout { grid-template-columns: 1fr; } }
  .picker { max-height: calc(100vh - 140px); overflow-y: auto; position: sticky; top: 60px;
    border: 1px solid var(--rule); border-radius: 8px; background: var(--surface); }
  .picker a { display: block; padding: 5px 12px; text-decoration: none; color: var(--ink-soft);
    font-size: 13px; border-bottom: 1px solid var(--rule-soft); }
  .picker a:hover { background: var(--chip-ghost); }
  .picker a.cur { color: var(--accent-ink); font-weight: 600; }
  .picker a .dim { color: var(--ink-faint); font-size: 11px; float: right; }
  .viewer { min-height: 300px; }
  .stage { position: relative; display: inline-block; max-width: 100%; border: 1px solid var(--rule);
    border-radius: 6px; overflow: hidden; background: #000; }
  .stage img { display: block; max-width: 100%; height: auto; image-rendering: auto; }
  .mk { position: absolute; transform: translate(-50%, -50%); cursor: default; }
  .mk.warp { width: 10px; height: 10px; background: #27c3e0; transform: translate(-50%, -50%) rotate(45deg);
    cursor: pointer; box-shadow: 0 0 0 1.5px rgba(0,0,0,0.65); }
  .mk.warp.inb { background: transparent; border: 2px solid #27c3e0; }
  .mk.npc { width: 8px; height: 8px; background: #58c470; box-shadow: 0 0 0 1.5px rgba(0,0,0,0.65); }
  .mk.spawn { width: 7px; height: 7px; border-radius: 50%; background: #e8963c; box-shadow: 0 0 0 1.5px rgba(0,0,0,0.65); }
  .area { position: absolute; border: 1.5px dashed #e8963c; background: rgba(232,150,60,0.12); pointer-events: none; }
  .mk.here { width: 14px; height: 14px; border-radius: 50%; background: transparent;
    border: 3px solid #ff5470; box-shadow: 0 0 0 2px rgba(0,0,0,0.6); animation: pulse 1.2s ease-out 4; pointer-events: none; }
  @keyframes pulse { 0% { transform: translate(-50%,-50%) scale(1); } 50% { transform: translate(-50%,-50%) scale(1.8); } 100% { transform: translate(-50%,-50%) scale(1); } }
  .viewer h2 { font-family: "Gowun Batang", Georgia, serif; margin: 0 0 4px; font-size: 22px; }
  .viewer .meta { font-family: "IBM Plex Mono", ui-monospace, monospace; font-size: 12px; color: var(--ink-faint); margin: 0 0 10px; }
  .legend { display: flex; gap: 14px; flex-wrap: wrap; align-items: center; margin: 8px 0; font-size: 13px; color: var(--ink-soft); }
  .legend label { display: flex; gap: 5px; align-items: center; cursor: pointer; }
  .sw { display: inline-block; width: 10px; height: 10px; }
  .missing { padding: 40px; color: var(--ink-faint); font-style: italic; }
  #tip { position: fixed; pointer-events: none; background: var(--ink); color: var(--ground);
    font-size: 12px; padding: 3px 8px; border-radius: 4px; z-index: 20; display: none; white-space: nowrap; }
"""
    page = HEAD.format(title="World Atlas", css=CHROME_CSS + extra_css) + nav("") + """
<div class="wrap">
  <header class="hero">
    <p class="kicker">Project1998 · the world, rendered</p>
    <h1>World Atlas</h1>
    <p class="lede">Every map the server serves, drawn with the real client tile art. Cyan diamonds are
    warps — <b>click one to walk through it</b> (filled = outgoing, hollow = an arrival from another
    map). Orange dots and boxes are spawns; green squares are NPCs. Hover anything for its name.
    Link to a spot with <code>#map=&lt;id&gt;</code>.</p>
  </header>
  <div class="toolbar">
    <input id="q" type="search" placeholder="Find a map — name or id…" aria-label="Find a map">
    <span class="count" id="count"></span>
  </div>
  <div class="layout">
    <div class="picker" id="picker"></div>
    <div class="viewer" id="viewer"><p class="missing">Pick a map.</p></div>
  </div>
  <div id="tip"></div>
""" + js("MAPS", maps) + js("WARPS", warps) + js("NPCS", npcs) + js("SPAWNS", spawns) + js("AREAS", areas) + """
<script>
const byId = Object.fromEntries(MAPS.map(m => [m.id, m]));
const INBOUND = {};
for (const [src, list] of Object.entries(WARPS))
  for (const w of list) (INBOUND[w[2]] = INBOUND[w[2]] || []).push([w[3], w[4], +src, w[0], w[1]]);

const picker = document.getElementById('picker'), q = document.getElementById('q'),
      viewer = document.getElementById('viewer'), count = document.getElementById('count'),
      tip = document.getElementById('tip');
let current = null, layers = { warps: true, spawns: true, npcs: true };

function esc(s){ return String(s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }
function renderPicker(){
  const needle = q.value.trim().toLowerCase();
  const list = MAPS.filter(m => !needle || m.n.toLowerCase().includes(needle) || String(m.id) === needle);
  picker.innerHTML = list.slice(0, 600).map(m =>
    `<a href="#map=${m.id}" class="${current === m.id ? 'cur' : ''}">${esc(m.n)} <span class="dim">${m.id} · ${m.xs}×${m.ys}</span></a>`).join('');
  count.textContent = list.length + ' of ' + MAPS.length + ' maps';
}
function pct(v, total){ return ((v + 0.5) / total * 100).toFixed(3) + '%'; }
function show(mid, atX, atY){
  const m = byId[mid];
  if (!m) return;
  current = mid;
  const outs = (WARPS[mid] || []), ins = (INBOUND[mid] || []);
  let marks = '';
  if (layers.warps) {
    marks += outs.map((w, i) => `<span class="mk warp" data-go="${w[2]}" data-gx="${w[3]}" data-gy="${w[4]}"
      data-t="→ ${esc((byId[w[2]] || {n: 'map ' + w[2]}).n)} (${w[3]},${w[4]})"
      style="left:${pct(w[0], m.xs)};top:${pct(w[1], m.ys)}"></span>`).join('');
    marks += ins.map(w => `<span class="mk warp inb" data-go="${w[2]}" data-gx="${w[3]}" data-gy="${w[4]}"
      data-t="← from ${esc((byId[w[2]] || {n: 'map ' + w[2]}).n)}"
      style="left:${pct(w[0], m.xs)};top:${pct(w[1], m.ys)}"></span>`).join('');
  }
  if (layers.npcs) marks += (NPCS[mid] || []).map(n =>
    `<span class="mk npc" data-t="${esc(n[2])}" style="left:${pct(n[0], m.xs)};top:${pct(n[1], m.ys)}"></span>`).join('');
  if (layers.spawns) {
    marks += (SPAWNS[mid] || []).map(s =>
      `<span class="mk spawn" data-t="${esc(s[2])}" style="left:${pct(s[0], m.xs)};top:${pct(s[1], m.ys)}"></span>`).join('');
    marks += (AREAS[mid] || []).map(a =>
      `<span class="area" data-t="${esc(a[4])}" style="left:${(a[0]/m.xs*100).toFixed(2)}%;top:${(a[1]/m.ys*100).toFixed(2)}%;width:${((a[2]-a[0]+1)/m.xs*100).toFixed(2)}%;height:${((a[3]-a[1]+1)/m.ys*100).toFixed(2)}%"></span>`).join('');
  }
  if (atX !== undefined) marks += `<span class="mk here" style="left:${pct(atX, m.xs)};top:${pct(atY, m.ys)}"></span>`;
  viewer.innerHTML = `
    <h2>${esc(m.n)}${m.pvp ? ' <span class="pill">PvP</span>' : ''}</h2>
    <p class="meta">map ${m.id} · ${m.xs}×${m.ys} tiles · ${outs.length} warp(s) out, ${ins.length} in</p>
    <div class="legend">
      <label><input type="checkbox" ${layers.warps ? 'checked' : ''} data-l="warps"><span class="sw" style="background:#27c3e0;transform:rotate(45deg)"></span>warps</label>
      <label><input type="checkbox" ${layers.spawns ? 'checked' : ''} data-l="spawns"><span class="sw" style="background:#e8963c;border-radius:50%"></span>spawns</label>
      <label><input type="checkbox" ${layers.npcs ? 'checked' : ''} data-l="npcs"><span class="sw" style="background:#58c470"></span>NPCs</label>
    </div>
    <div class="stage"><img src="img/maps/TK${m.id}.webp" alt="${esc(m.n)}"
      onerror="this.parentNode.innerHTML='&lt;p class=missing&gt;This map hasn\\'t been rendered yet.&lt;/p&gt;'">${marks}</div>`;
  viewer.querySelectorAll('[data-l]').forEach(cb => cb.addEventListener('change', () => {
    layers[cb.dataset.l] = cb.checked; show(mid, atX, atY);
  }));
  viewer.querySelectorAll('.mk.warp').forEach(el => el.addEventListener('click', () => {
    location.hash = 'map=' + el.dataset.go;
    show(+el.dataset.go, +el.dataset.gx, +el.dataset.gy);
    renderPicker();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }));
  viewer.querySelectorAll('[data-t]').forEach(el => {
    el.addEventListener('mousemove', e => {
      tip.style.display = 'block'; tip.textContent = el.dataset.t;
      tip.style.left = (e.clientX + 14) + 'px'; tip.style.top = (e.clientY + 6) + 'px';
    });
    el.addEventListener('mouseleave', () => tip.style.display = 'none');
  });
  renderPicker();
}
function fromHash(){
  const h = /map=(\\d+)/.exec(location.hash);
  if (h) show(+h[1]);
}
q.addEventListener('input', renderPicker);
window.addEventListener('hashchange', fromHash);
renderPicker();
fromHash();
if (!current) { location.hash = 'map=0'; fromHash(); }
</script>
<footer>Rendered with the repo's own pixel-identical map renderer; marker data from the live game-data CSVs.</footer>
</div>
</body>
</html>
"""
    io.open(os.path.join(SITE, "atlas.html"), "w", encoding="utf-8").write(page)
    print("atlas.html:", len(maps), "maps,",
          sum(len(v) for v in warps.values()), "warps,",
          sum(len(v) for v in npcs.values()), "npcs,",
          sum(len(v) for v in spawns.values()), "spawn points")

if __name__ == "__main__":
    build()
