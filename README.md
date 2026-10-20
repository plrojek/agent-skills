# agent-skills

Claude Code skills and plugins from my own projects, cleaned up enough to share. The repo is a plugin marketplace, so you can install straight from it.

```
/plugin marketplace add plrojek/agent-skills
/plugin install garden-3d-viewer@plrojek
/plugin install sanalert@plrojek
```

From a shell it's `claude plugin marketplace add plrojek/agent-skills`, then `claude plugin install garden-3d-viewer@plrojek`. If you don't want plugins, copy `plugins/garden-3d-viewer/skills/garden-3d-viewer` into `~/.claude/skills/` and it works the same way.

## garden-3d-viewer

![The example garden in the viewer, October, year five](docs/garden-3d-viewer.jpg)

Turns a planting plan into a 3D garden you open in a browser. A month slider for the seasons, a growth slider from planting day to mature size, the sun's position for any hour, walking at eye level, a tape measure, a PNG of the plan, a shopping list with a CSV export, a map of sun hours and an irrigation layer. Static files and three.js, no build step, nothing on a server.

The plan lives in one place. You keep it as Python tables, an exporter writes `garden-scene.json`, and the viewer draws only what that file says. `templates/example/build_scene.py` is a complete exporter for a made-up plot. Run it first: if the example shows a house, plants and a working month slider, any later problem is in your data.

I built it with Claude Code for my own garden. Ask Claude something like "show my planting plan in 3D" or "how much sun does the terrace get in July" and it should pick the skill up.

A few things to know:

- The interface ships in Polish. The texts sit in three places: the `T` table at the top of `garden.js`, month names in `site.js`, labels in `index.html`. `meta.ui` in the scene overrides the title, currency and layer names.
- `scripts/fetch_three.sh` downloads three.js r180 from jsDelivr into `vendor/` and rewrites the add-on imports, so the page needs no import map and makes no third-party requests once it's deployed.
- The scene file holds your plot outline, the house and coordinates good to about a kilometer. If it's your own house, don't put it on a public URL - and don't post a plan view of it either, because the outline alone can be matched against public land-registry maps. `SKILL.md` has a note on keeping the whole folder private.

## sanalert

[SanAlert](https://sanalert.pl/en/) shows an unofficial threat level from the air for places in Poland. This plugin has no skill, only two MCP servers:

- `sanalert` runs on your computer and needs [uv](https://docs.astral.sh/uv/). Its one tool, `sanalert_level`, gives the level for a town from the website's list or for a point. It downloads the same public state the website reads and works the level out locally, so no request to SanAlert carries the place you ask about. Your assistant's provider still sees your question and the answer, as with anything you ask it. The code is in [plrojek/sanalert-mcp](https://github.com/plrojek/sanalert-mcp); the plugin runs its `v1.0.0` tag.
- `sanalert-poland` is SanAlert's remote server, `https://api.sanalert.pl/mcp`: the state for the whole country, official messages from the last 24 hours, night reports, source cards and the reliability record. It takes no place.

After installing, ask something like "what's the SanAlert level in Przemyśl?".

It is not an official warning system and doesn't replace sirens, Alert RCB or instructions from the authorities. If you show its data anywhere, keep the notice and attribution that come with every answer, including the link to NEPTUN, and never show "no data" as "quiet". The full conditions are in the [sanalert-mcp README](https://github.com/plrojek/sanalert-mcp#conditions-of-use) and [SanAlert's terms](https://sanalert.pl/en/terms/).

## License

MIT. three.js, which the script downloads, is MIT as well.
