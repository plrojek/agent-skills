# pl-genealogy-record-search

Finds your Polish ancestors in parish indexes, deportation lists, cemetery registers and scanned parish books, then grades each finding and patches your GEDCOM so it still imports.

```
/plugin marketplace add plrojek/agent-skills
/plugin install pl-genealogy-record-search@plrojek
```

I wrote it while working through my own family's lines. Most of it is about what goes wrong: Geneteka answering with thousands of rows from the wrong province, a zero that was a spelling, a marriage filed in the bride's parish because she was of the other rite, a cemetery search that can't find a woman under her maiden name, a book written off as "needs a letter to the archive" that had been free online for weeks. Each of those cost me a session or more, and the skill now checks for them.

It works in four steps:

1. **Inventory.** Parse the tree, list the brick walls on the direct line, the placeholders (missing given names, a wife with her husband's surname), and which surname sits in which village.
2. **Sweep.** Geneteka parish indexes, the Indeks Represjonowanych (Soviet deportations; searching by village returns the whole transport), the Przemyśl municipal cemeteries with birth dates from the grave cards, any Grobonet cemetery with everyone in a grave, and scans from Skanoteka, metryki.genealodzy.pl, CAAK and, through your browser, szukajwarchiwach.gov.pl.
3. **Cross-match and grade.** Tree people against the saved index rows, then confirmed / probable / hypothesis / rejected, with the act that would settle each open question.
4. **Capture.** A research note with act numbers and archive signatures, a patched copy of the GEDCOM checked for broken links and records after the trailer, and an order-of-entry list for MyHeritage, which can't merge a GEDCOM back.

Ask Claude something like "find the parents of this ancestor of mine" or "check if this family story about Anders' Army holds up", point it at a GEDCOM, and it should pick the skill up.

A few things to know:

- The sources are Polish sites and most of the material is Polish and Latin. Claude reads both; you don't need to.
- Geneteka covers all of Poland and many parishes now in Ukraine, Belarus and Lithuania. The cemetery scripts cover the Przemyśl municipal cemeteries and the cemeteries on Grobonet only.
- Some important sources need a real browser or an account (szukajwarchiwach.gov.pl, Gesher Galicia, FamilySearch). The skill uses them through your browser if you have Claude in Chrome, and otherwise tells you what to open.
- Geneteka can block an IP address that sent it too many automated searches. It doesn't return an error: every search from that address gets thousands of unrelated rows, in a script and in your browser alike. The skill spots that, stops querying and tells you. It happened to me after weeks of big sweeps: connecting the computer to the internet through my iPhone's hotspot gave real answers again at once, and the home connection was unblocked within two months. Whichever connection you use, keep the searches narrow.

## What it runs, downloads and sends

The skill tells Claude to run Python scripts from its `scripts/` folder; there are no hooks and no MCP servers.

- **Programs:** Python 3.10 or newer, standard library only. `contact_sheet.py` (cropping and stacking scans) needs Pillow and is run with `uv run`, which installs `pillow==11.3.0` for that script only.
- **Sites it contacts**, only when Claude runs a search you asked for: `geneteka.genealodzy.pl`, `indeksrepresjonowanych.pl`, `cmentarzeprzemysl.pl`, the `*.grobonet.com` instance you name, `skanoteka.genealodzy.pl` and `metryki.genealodzy.pl` with their `metbox*.genealodzy.pl` image hosts, and `caak.upjp2.edu.pl`. What it sends is the search: surnames, given names, years, places. Each request carries the User-Agent `pl-genealogy-record-search/<version> (+https://github.com/plrojek/agent-skills)` (override with `GENEALOGY_UA`), and the scripts wait at least a second between requests to one site (`GENEALOGY_DELAY`). The Przemyśl cemetery site's TLS certificate is issued for a different host name, so that one script doesn't verify certificates.
- **What it saves:** Geneteka answers are cached in `~/.cache/pl-genealogy-record-search` for 30 days (`GENEALOGY_CACHE_DIR`, `GENEALOGY_CACHE_DAYS`). Scans go to the folder you give. Everything else is files in your working folder.
- **Your tree stays on your computer.** The GEDCOM, its JSON and your notes are read and written locally and never sent to these sites. A family tree is personal data about living people too, so keep it out of public repositories.

The scripts' tests are offline and live outside the plugin: `python3 -m unittest discover -s tests/pl-genealogy-record-search` from the repository root.

## License

MIT. Source: [github.com/plrojek/agent-skills](https://github.com/plrojek/agent-skills).
