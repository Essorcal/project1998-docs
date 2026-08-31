#!/usr/bin/env python3
"""Regenerate site/commands.html from the game repo's Server/Commands.cs — the command table itself,
so the sheet can never drift from the source. Section headers come from the table's own
`// ---- section ----` comments; per-command enrichments (links, sprites, extra prose) live in
tools/command_notes.json and are appended to the source help text.

Usage: python tools/gen_commands.py <path-to-game-repo>
"""
import html, io, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_db import GAME, SITE  # noqa: E402

SRC = os.path.join(GAME, "Server", "Commands.cs")
NOTES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "command_notes.json")

def parse():
    text = io.open(SRC, encoding="utf-8").read()
    table = text.split("CommandTable =", 1)[1].split("\n    };", 1)[0]
    sections, cur = [], None
    entry_re = re.compile(r'\b([PTG])\("([a-z0-9|]+)",\s*\(s, a\) =>.*?,\s*"(.*?)",\s*\n?\s*"(.*?)"\),',
                          re.S)
    sec_re = re.compile(r"// ---- (.+?) -+")
    pos = 0
    events = []
    for m in sec_re.finditer(table):
        events.append((m.start(), "sec", m.group(1).strip()))
    for m in entry_re.finditer(table):
        events.append((m.start(), "cmd", m.groups()))
    events.sort(key=lambda e: e[0])
    for _, kind, val in events:
        if kind == "sec":
            cur = {"title": val, "cmds": []}
            sections.append(cur)
        else:
            tier, names, args, help_ = val
            if cur is None:
                cur = {"title": "Commands", "cmds": []}
                sections.append(cur)
            cur["cmds"].append({"tier": tier, "names": names.split("|"),
                                "args": args.replace('\\"', '"'),
                                "help": help_.replace('\\"', '"')})
    return [s for s in sections if s["cmds"]]

SEC_TITLES = {  # source comment -> display title
    "help / discovery": "Help & discovery",
    "world / navigation": "World & navigation",
    "character": "Character",
    "items": "Items",
    "spells": "Spells",
    "moderation": "Moderation",
    "events": "Events",
    "config read-outs": "Config read-outs",
    "sprite / appearance lab": "Sprite & appearance lab",
    "media": "Media",
    "protocol probes": "Protocol probes",
}

def build():
    notes = json.load(io.open(NOTES, encoding="utf-8")) if os.path.exists(NOTES) else {}
    sections = parse()
    total = {"P": 0, "T": 0, "G": 0}
    body = []
    for sec in sections:
        title = SEC_TITLES.get(sec["title"].strip().lower(), sec["title"])
        rows_html = []
        for c in sec["cmds"]:
            total[c["tier"]] += 1
            names = " / ".join(f"<b>@{html.escape(n)}</b>" for n in c["names"])
            args = f' <span class="args">{html.escape(c["args"])}</span>' if c["args"] else ""
            help_ = html.escape(c["help"]) + notes.get(c["names"][0], "")
            rows_html.append(
                f'      <div class="cmd" data-tier="{c["tier"]}"><span class="chip">{c["tier"]}</span>'
                f'<span class="cmd-name">{names}{args}</span>'
                f'<span class="cmd-help">{help_}</span></div>')
        extra = notes.get("__section:" + title, "")
        body.append(f"""    <section>
      <div class="sec-head"><h2>{html.escape(title)}</h2><span class="count"></span></div>
{extra}{chr(10).join(rows_html)}
    </section>""")
    # @help is dispatched before the table (works at every tier) — documented via the notes file.
    if "__help_row" in notes:
        body[0] = body[0].replace('<div class="cmd" data-tier="P">',
                                  notes["__help_row"] + '\n      <div class="cmd" data-tier="P">', 1)
        total["P"] += 1

    n = total["P"] + total["T"] + total["G"]
    tpl = io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "commands_template.html"),
                  encoding="utf-8").read()
    page = (tpl.replace("{{SECTIONS}}", "\n\n".join(body))
               .replace("{{TOTAL}}", str(n))
               .replace("{{P}}", str(total["P"])).replace("{{T}}", str(total["T"]))
               .replace("{{G}}", str(total["G"])))
    io.open(os.path.join(SITE, "commands.html"), "w", encoding="utf-8").write(page)
    print(f"commands.html: {n} commands ({total['P']} P / {total['T']} T / {total['G']} G), "
          f"{len(sections)} sections")

if __name__ == "__main__":
    build()
