# Project1998 Docs

Player- and tester-facing documentation for the Project1998 NexusTK revival server,
published at **https://essorcal.github.io/project1998-docs/**.

## Pages

- `site/index.html` — landing page
- `site/commands.html` — The @Command Scroll: every `@` chat command, searchable, with tier filters
- `site/quest-registry.html` — The Quest Registry: every quest key and legend mark, the companion to `@quest`/`@legend`
- `site/patch-notes.html` — running patch notes

## Updating

Edit the HTML under `site/` and push to `main` — the `deploy` workflow publishes to
GitHub Pages automatically. No build step; the pages are self-contained static HTML.

The command and quest data are maintained by hand against the game repo
([project1998/Project1998](https://github.com/project1998/Project1998)); the source
of truth is `Server/Commands.cs` and `docs/common/Quest-Registry.md` there. When
commands change, regenerate/update `commands.html` alongside the server PR.
