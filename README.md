# Project1998 Docs

Player- and tester-facing documentation for the Project1998 NexusTK revival server,
published at **https://p1998.essorcal.com/**.

## Pages

| Page | What | Source |
|---|---|---|
| `commands.html` | The @Command Scroll — every `@` chat command | **generated** from `Server/Commands.cs` |
| `quest-registry.html` | Quest keys + legend marks | hand-ported from the tester sheet |
| `spells.html` | Spells & skills DB | **generated** from game-data CSVs |
| `items.html` | Items DB (real icons) | **generated** from game-data CSVs |
| `mobs.html` | Mobs DB (spawns, drops, casts) | **generated** from game-data CSVs |
| `atlas.html` | World Atlas — every map, clickable warps | **generated** data + local map renders |
| `map-editor.html` | Map editor install & use | tracks `MapEditor/README.md` |
| `noclip.html` | No-clip companion setup | tracks `noclip-companion/README.txt` |
| `patch-notes.html` | Patch notes, newest first | hand-written (drafts via workflow) |

## Automation

- **`deploy.yml`** — every push to `main` publishes `site/` to Pages. Posts to Discord if a
  `DISCORD_WEBHOOK` secret exists.
- **`regen.yml`** — nightly (and on demand): checks out the public game repo, reruns the three
  generators (`tools/gen_commands.py`, `tools/gen_db.py`, `tools/gen_atlas.py`), commits + deploys
  if anything changed. The generated pages cannot drift from the server's source.
- **`draft-notes.yml`** — on demand: drafts the next patch-notes entry from upstream's merged PRs
  since the last entry and opens an issue with it. A human polishes and commits.

## Local-only artifacts (need the 5.33 client)

CI can regenerate all text/data, but the art comes from the game client, so these are rendered on
a dev machine and committed:

- `tools/local/render_sprites.py` → `site/img/item-icons.png/.json` (mob sprites: TODO — the 5.33
  mob palette scheme is not yet decoded; see the script's notes)
- `tools/local/render_atlas.py` → `site/img/maps/*.webp` + `index.json` (~75 MB, all 2,025 maps)

Re-run these after art-affecting changes (new items, new maps), then commit.

## Hand-editing

`command_notes.json` holds per-command enrichments (links, sprites) appended to the generated help
text — edit it rather than `commands.html`, which is overwritten by the generator.
