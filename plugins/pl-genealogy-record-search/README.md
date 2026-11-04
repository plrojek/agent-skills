# pl-genealogy-record-search

Finds your Polish ancestors in parish indexes, deportation lists, cemetery registers and scanned parish books, then grades each finding and patches your GEDCOM so it still imports.

```
/plugin marketplace add plrojek/agent-skills
/plugin install pl-genealogy-record-search@plrojek
```

I wrote it while working through my own family's lines. Most of it is about what goes wrong: Geneteka answering with thousands of rows from the wrong province, a zero that was a spelling, a marriage filed in the bride's parish because she was of the other rite, a cemetery search that can't find a woman under her maiden name, a book written off as "needs a letter to the archive" that had been free online for weeks. Each of those cost me a session or more, and the skill now checks for them.

It works in four steps:

1. **Inventory.** Parse the tree, list the brick walls on the direct line, the placeholders (missing given names, a wife with her husband's surname), and which surname sits in which village.
2. **Sweep.** Geneteka parish indexes, the Indeks Represjonowanych (Soviet deportations; searching by village returns the whole transport), the Przemyśl municipal cemeteries with birth dates from the grave cards, any Grobonet cemetery with everyone in a grave, and scans from Skanoteka, metryki.genealodzy.pl and CAAK. Through your browser: szukajwarchiwach.gov.pl, the Lviv archive's online metrical books (ARCHIUM), FamilySearch (records, the film catalog that says which archive holds a parish's books, and full-text search of emigrant documents) and Gesher Galicia. For each village it works out which parish the village belonged to at the time, from the 19th-century gazetteer, not today's municipality. Every search goes into a research log with its result, nothing-found included, and the log is checked before the next search, so the same book is never searched twice.
3. **Cross-match and grade.** Tree people against the saved index rows, then confirmed / probable / hypothesis / rejected, with the act that would settle each open question. A conclusion that rests on one hard-to-read word (a maiden name, a house number) is read a second time by a separate reader that isn't told what to expect.
4. **Capture.** A research note with act numbers and archive signatures, a patched copy of the GEDCOM checked for broken links and records after the trailer, and an order-of-entry list for MyHeritage, which can't merge a GEDCOM back.

Ask Claude something like "find the parents of this ancestor of mine" or "check if this family story about Anders' Army holds up", point it at a GEDCOM, and it should pick the skill up.

A few things to know:

- The sources are Polish sites and most of the material is Polish and Latin. Claude reads both; you don't need to.
- Geneteka covers all of Poland and many parishes now in Ukraine, Belarus and Lithuania. The cemetery scripts cover the Przemyśl municipal cemeteries and the cemeteries on Grobonet only.
- Some important sources need a real browser or an account (szukajwarchiwach.gov.pl, the Lviv archive's ARCHIUM, Gesher Galicia, FamilySearch). The skill uses them through your browser if you have Claude in Chrome, and otherwise tells you what to open. On FamilySearch it only reads: it never saves or attaches anything to your tree.
- The scripts keep to each site's robots.txt. Geneteka asks for two minutes between automated requests (Skanoteka and Metryki for one), so a search that pages through a few hundred rows takes several minutes and a sweep of a family's surnames runs for hours. The wait is remembered between runs, so restarting a script doesn't skip it. Cached answers come back at once.
- Geneteka can block an IP address that sent it too many automated searches. It doesn't return an error: every search from that address gets thousands of unrelated rows, in a script and in your browser alike. The skill spots that, stops querying and tells you. It happened to me after weeks of big sweeps: connecting the computer to the internet through my iPhone's hotspot gave real answers again at once, and the home connection was unblocked within two months. Whichever connection you use, keep the searches narrow.

## The tree page and the family book

The plugin has a second skill, `pl-genealogy-tree-viewer`, for showing the tree once the records are in it. From the GEDCOM and a small Python file with the research (which act proves what, where each line ends and what would break the wall, which links are only hypotheses, which sources disagree) it builds a private website and a printable family book. It is the viewer I use for my own family's tree.

- **Views:** a family view with couples side by side and every partner's ancestors, a map of everyone (names stay readable far out), an ancestor fan, a timeline, a list grouped by family, kinship between any two people.
- **Lines and the path:** each grandparent's line on its own background colour, with the same colours in the map, the fan and the minimap; a bar at the top with the route from you to whoever is in the centre, in those colours, with the kinship term.
- **Ancestor picture:** a fan or a tree of one person's ancestors to download (PNG, JPG or SVG) or share from a phone, with options for generations, dates, places, photos and theme; people presumed living without dates by default.
- **Evidence on the card:** an "akt" mark next to each date, parent or spouse that a transcribed act proves, the act itself with its scan crop and translation, walls with the next step, hypotheses with their variants, conflicting sources side by side. When acts replaced something the family remembered, the card keeps the old value and says which acts changed it. On a computer the card opens as a wide panel beside the tree.
- **Search** by every spelling of a surname, by place and by years, with the hits highlighted in the tree.
- **Publishing:** a public copy with noindex and PESEL-like numbers masked, people presumed living redacted on request (their names also leave the line labels, and lines anchored on a living person are listed so you can relabel them), and a book PDF built from that copy.

The interface and the book are in Polish. Try it on the invented family in `skills/pl-genealogy-tree-viewer/templates/example/` first.

## What it runs, downloads and sends

The skill tells Claude to run Python scripts from its `scripts/` folder; there are no hooks and no MCP servers.

- **Programs:** Python 3.10 or newer, standard library only. `contact_sheet.py` (cropping and stacking scans) needs Pillow and is run with `uv run`, which installs `pillow==11.3.0` for that script only.
- **Sites it contacts**, only when Claude runs a search you asked for: `geneteka.genealodzy.pl`, `indeksrepresjonowanych.pl`, `cmentarzeprzemysl.pl`, the `*.grobonet.com` instance you name, `skanoteka.genealodzy.pl` and `metryki.genealodzy.pl` with their `metbox*.genealodzy.pl` image hosts, and `caak.upjp2.edu.pl`. What it sends is the search: surnames, given names, years, places. Each request carries the User-Agent `pl-genealogy-record-search/<version> (+https://github.com/plrojek/agent-skills)` (override with `GENEALOGY_UA`). Before the first request of the day to a site, the scripts read its `/robots.txt`, then skip any path it disallows and wait its `Crawl-delay` between requests: 120 s for Geneteka, 60 s for Skanoteka and Metryki, one second where a site sets none. `GENEALOGY_DELAY` can make the wait longer, not shorter. A site whose robots.txt refuses automated access (HTTP 401 or 403) gets no requests at all. The Przemyśl cemetery site's TLS certificate is issued for a different host name, so that one script doesn't verify certificates.
- **What it saves:** Geneteka answers are cached in `~/.cache/pl-genealogy-record-search` for 30 days (`GENEALOGY_CACHE_DIR`, `GENEALOGY_CACHE_DAYS`), each site's robots.txt for a day, and the time of the next allowed request per site in `next-request.json` in the same folder. The research log, one line per search with the surnames, places and years searched and what came back, is written to `GENEALOGY_LOG`, or to `~/.local/share/pl-genealogy-record-search/searches.jsonl` if that isn't set; every write prints the path. Scans go to the folder you give. Everything else is files in your working folder.
- **Your tree stays on your computer.** The GEDCOM, its JSON, the research log and your notes are read and written locally and never sent to these sites. A family tree is personal data about living people too, so keep it out of public repositories.

The tree viewer's scripts (`build_tree.py`, `check_tree.py`, `publish.py`, `build_book.py`) contact no site. They use the standard library, Pillow (`pillow==11.3.0` through `uv run`) only for scan pages and photos, and Google Chrome or Chromium for the browser check and the book PDF; `check_tree.py` serves the page on 127.0.0.1 for the browser it starts. They write the page, its `scans/` folder, the publication folder and the book where you point them. The page itself makes no outside requests.

The scripts' tests are offline and live outside the plugin: `python3 -m unittest discover -s tests/pl-genealogy-record-search` and `python3 -m unittest discover -s tests/pl-genealogy-tree-viewer` from the repository root.

## License

MIT. Source: [github.com/plrojek/agent-skills](https://github.com/plrojek/agent-skills).
