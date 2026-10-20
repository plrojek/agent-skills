---
name: garden-3d-viewer
description: "Build an interactive 3D web view of a garden with its house on a real plot: terrain, house with roof and openings, paving, fences, every planting position as a low-poly plant, seasons (leaf, flower, fruit, autumn colour, bare branches), growth over the years, real sun and shadows by month and hour, species highlight, eye-level walk, tape measure, PNG export of the plan, a shopping list with costs and CSV, an hours-of-sun map, planting stages by year and an irrigation plan layer. Static files only (three.js, no build step), generated from one plan data source through a scene JSON. Use when the user has (or wants) a planting plan and asks to see it in 3D in the browser, walk through it, check shade on the terrace, show it to family or a contractor, or publish it. Trigger phrases: 'wizualizacja ogrodu', 'ogród w 3D', 'ogród w przeglądarce', 'interaktywny plan ogrodu', 'pokaż cienie na działce', 'spacer po ogrodzie', 'garden 3D viewer', 'interactive garden plan', 'visualise my garden', 'three.js garden'."
metadata:
  version: 1.1.1
---

# Garden 3D viewer — from a planting plan to an interactive web page

The result is a folder of static files: `index.html`, seven ES modules, a vendored three.js and one
`garden-scene.json`. Open it from any static web server. Nothing is authored by hand in the
viewer: **one plan data source → an exporter → `garden-scene.json` → the viewer draws it.**

Paths in this file (`templates/`, `references/`, `scripts/`) are relative to the folder that
holds this `SKILL.md`.

```
plan data (Python tables: plot, terrain, house, zones, plants, looks)
        │  exporter  (templates/example/build_scene.py is a complete working one)
        ▼
garden-scene.json  ── the only interface; contract in references/scene-schema.md
        ▼
viewer  (templates/viewer/: index.html + garden.js site.js ground.js plants.js house.js sun.js sunmap.js)
```

## What the viewer does

| Feature | How it works | Scene fields it reads |
|---|---|---|
| Overview, plan, eye-level views | orbit camera fitted to the free screen area; orthographic plan with pan/zoom; named eye views tween between each other | `plot`, `views` |
| Seasons | month slider I–XII + play; every plant recolours, flowers, fruits, turns, drops leaves; the lawn changes tone; meadow and bulbs flower in the turf | `looks`, `plants[].variants[].look`, `scatter` |
| "What flowers now" calendar | list per month of flowers / fruit / autumn colour, click = highlight | `looks`, `variants[].label` |
| Growth | slider from just planted → year 1 → 5 → 10 → mature (crown scale 0.22 → 1.0) | `variants[].dia`, `.h` |
| Real sun | hour slider + play the day; NOAA solar position for the 21st of the chosen month; shadows of house and trees; fixed "studio" light as a switch | `meta.site` |
| Plant card | click = species, quantity, stock, date, price, mature size, flowering months; hover tooltip | `plants[]` |
| Highlight | one species, one zone or one planting year stays coloured, the rest fades; camera flies there | — |
| Walk | 1.65 m eye over the terrain, W A S D / arrows, drag to look, thumb pad on touch, walls block | `grid`, `buildings`, `structures` |
| Tape measure | click points on the ground: segment lengths, total, area | `grid` |
| PNG export | current view at 2×; the plan at 3× with zone letters, plant codes, scale bar, north arrow | — |
| Shopping list | pieces and cost range by zone or by year; row click = highlight | `priceLo`, `priceHi`, `year`, `zone` |
| Pinned controls | view buttons live in the header; one bottom dock carries the month, hour and growth sliders (one at a time with value tabs on phones); camera margins follow the measured header and dock heights | — |
| Hours-of-sun map | layer painting hours of direct sun on the 21st of the chosen month: shadows of the house, built volumes and leafed crowns are stamped on a small 2D canvas for ~30 sun positions and summed (`sunmap.js`, ~0.2 s) | `meta.site`, `buildings`, `house.roofs`, `structures`, plants |
| Planting stages | slider in the panel: show only what is planted up to a given year | `plants[].year` |
| Irrigation | layer drawing drip lines, rings, feeds, trunks (trench / sleeve / surface), sprinkler reach and hose reach from the taps; panel with sections, weekly litres and minutes and the water budget; a picked section is drawn in focus with its plants highlighted | `irrigation` (optional) |
| CSV shopping list | the cost table as a `;`-separated file with a BOM, irrigation materials included | `plants[]`, `irrigation.bom` |
| Layers and zones | toggles for plants, buildings, slopes, utilities, fences, site objects, zone tints, aerial photo, labels | `zones`, `pipes`, `fences`, `lines`, `ortho` |
| Plan furniture | zone letters, plant codes when zoomed in, scale bar, compass (true north) | `zones`, `plants[].id` |
| Surroundings | optional aerial photo draped on a terrain ring that fades into the page | `ortho`, `context` |

Rendering is on demand (nothing redraws while nothing changes), plants are instanced, and ambient
occlusion runs only on desktops — a whole garden of ~1 000 plants stays smooth on a phone.

## Phase 1 — collect the facts (do not guess any of them)

Ask for or read from the user's documents; never invent a dimension.

1. **Plot outline** in metres, and where north is. A surveyor's map or a cadastral outline; a
   projected CRS (metres) shifted to a local origin keeps everything else simple.
2. **Levels**: is the ground flat? Where does it fall, by how much, where is the top edge of any
   bank? A single `surface(x, y)` function is the whole terrain model.
3. **House**: outer wall outline, wall height, eave height, roof pitch and overhang, which
   rectangles the roof wings cover, exterior doors and windows (position, width, height, sill).
4. **Hard surfaces and furniture**: drive, paths, terrace, patio; fences with gate openings;
   pergola, playground, greenhouse, raised beds, shed; underground lines with protection bands.
5. **The planting plan**: for every entry a code, zone, botanical and common name, quantity,
   nursery stock, when to plant, price range, and **where** — points, rows (polylines) or areas
   (polygons). If there is no plan yet, design one first; this skill visualises, it does not design.
6. **Latitude / longitude** to two decimals (for the sun) and the UTC offset.

Fix one **site frame** and use it everywhere: origin at a plot corner, **x east, y south**, metres.

## Phase 2 — write the exporter

Start from `templates/example/build_scene.py` (standard library only). Its top half is a `DATA`
section — plot, `surface()`, house, paving, ground cover, zones, `LOOKS`, `PLANTS` — and its bottom
half is plumbing that turns those tables into the scene. Replace the data, keep the plumbing.

Rules that keep the scene honest:

- **One source of truth.** Positions, sizes and species live in the plan tables only. If the same
  plan also feeds a drawing, a table or another 3D model, they all import the same tables.
- **The viewer invents nothing.** A new thing to show = a new field in the scene, never a constant
  in a module. (The one exception: where exactly each plant of a scattered bed lands.)
- **Every drawn plant needs a look.** The exporter prints the entries with no match in `LOOKS`;
  fix them all, otherwise those plants stay one green all year.
- **Multi-species entries are sized per plant.** "Malus 'A' 2, Malus 'B' 1" becomes two variants;
  each point maps to its own variant (`ptVariant`).
- **Mirror, then verify.** If a number is copied from another file (furniture positions from a CAD
  export, say), have the exporter re-read that file and fail loudly when it moved.

Field-by-field contract: `references/scene-schema.md`. Read it before adding anything.

### Irrigation, if the user wants it

Design it in the plan data, like the planting — the viewer only draws the `irrigation` block.

1. **Water budget first; it decides the architecture.** Sum the July demand of the drip sections and of the lawns separately and set both against the source. A few cubic metres of rainwater carry drip for beds, hedges, vegetables and young trees; lawns need several times more and usually end up as an optional mains-fed section. Say so before drawing anything.
2. **Derive the laterals from the plan**: a drip line along every hedge and row, parallel lines across every bed polygon, a ring per tree, one line threading a group of shrubs. Count emitters from the lengths; flow = emitters × emitter rate; run time = demand ÷ flow.
3. **On a slope**: lines on the surface along the contours, fed from the top; pressure-compensating emitters with check valves (otherwise the line drains to its lowest point after every cycle); no trench near the crest.
4. **Trunk routes are the only hand-placed data** — so validate them in the exporter: inside the plot, not under the house, clear of slope crests and of any utility easement; fail the export on a violation. Mark sleeves under paving: they must go in before the paving does.
5. **State assumptions as a table** (pump curve, mains pressure and flow, emitter rate, demand per plant type) and label the result a proposal for a fitter to check.


## Phase 3 — assemble the viewer

```
mkdir -p site/garden && cp templates/viewer/* site/garden/
bash scripts/fetch_three.sh site/garden            # three.js r180 + add-ons into vendor/, imports rewritten
python3 your_exporter.py site/garden/garden-scene.json
cd site && python3 -m http.server 8741             # then open http://127.0.0.1:8741/garden/
```

Run the bundled example first (`templates/example/garden-scene.json` is its output) — if that
shows a house, plants and a working season slider, the plumbing is fine and any later problem is
in the data.

What to adapt in the viewer:

- **Texts**: everything the code writes is in the `T` table at the top of `garden.js`, month names
  in `site.js`, static labels in `index.html`. The templates ship in Polish; translate those three
  places. `meta.ui` in the scene overrides the title, currency, layer names and photo credit.
- **Look**: page colours are CSS variables in `index.html`; ground and paving palettes are the
  `GROUND`, `LAWN_BY_MONTH` and `PAVE` tables in `ground.js`; materials in `house.js` (`MAT`).
- **New furniture**: add a branch to `siteObject()` in `house.js` and a `kind` in the scene.
- **New plant shape**: add a lobe recipe to `LOBES` in `plants.js` and name it as a look's `habit`.

## Phase 4 — verify before showing anyone

Drive it in a real browser (Playwright or by hand), desktop and a phone-sized viewport:

- [ ] loads with **zero console errors**; the loading card disappears
- [ ] every view button lands on a sensible frame; the plan fits beside the panel
- [ ] step the month I → XII: nothing stays the same green all year that should not; winter shows branches
- [ ] growth slider: first and last stage both look right (hedges and grasses do not vanish)
- [ ] sun: at local noon shadows point north (northern hemisphere); sunrise/sunset times are plausible for the place
- [ ] click three plants of different kinds — card matches the plan; click a calendar row — it highlights and flies
- [ ] walk from the gate to the terrace; you cannot pass through the house
- [ ] measure a known length (a house wall) — it matches the drawing
- [ ] PNG of the plan opens, labels legible, scale bar present
- [ ] shopping-list total = sum of quantity × price range from the plan; the CSV opens in a spreadsheet with columns intact
- [ ] sun map: shade lies north of the house at midsummer (northern hemisphere) and deepens in winter; planting-stage slider empties and refills the garden
- [ ] irrigation (if present): each section in the panel focuses, highlights its plants and shows plausible litres and minutes
- [ ] portrait phone: whole plot visible in the overview, panel opens as a bottom sheet
- [ ] a second engine (Safari / WebKit) — see pitfalls

`window.__garden.look(x, y, azimuth, polar, distance)` in the console aims the camera at a site
point for checking a detail.

## Phase 5 — publish

Any static host works. Three things matter:

- **Cache**: serve `*.js` and `*.json` with `Cache-Control: no-cache` (revalidate every time) unless
  file names carry a version. With a day-long `max-age` a redeploy is invisible to everyone who
  visited that day — the browser serves the old viewer against the new scene.
- **Privacy**: the scene contains the plot outline, the house plan, prices and coordinates good to
  about a kilometre. The outline alone can be matched against public cadastral maps, so a plan view of a real
  plot gives its location away even with no address on it. If that should not be public, put the whole folder (HTML, modules, vendor,
  JSON, photo) behind the same access control, and check that a request without credentials gets
  nothing for *each* of those files, not only for the page.
- **No third-party requests**: three.js is vendored on purpose; keep it that way.

## Pitfalls (each of these cost a debugging session)

**Geometry**
- A hip roof over an L-shaped house is **the union of hip roofs over rectangles** (one per wing).
  A uniform inward offset of the L outline folds over at the inner corner and draws a spike.
- Fences must be **geometry** (posts, rails, a translucent panel). A `THREE.Line` is always 1 px
  wide and the plot reads as unfenced from above.
- Point structures (arches, benches) need their own geometry **and their angle** from the scene;
  the default blob primitive turns them into spheres, and an unrotated arch runs along its path.
- Built volumes (greenhouse, raised beds, shed) are extruded footprints. Sent down the generic
  "scatter shrubs over this polygon" path they become thickets.
- Roof facets arrive in whatever winding the exporter used; flip any triangle whose normal points down.
- The house floor sits at `meta.plateau` + 2 cm; an aerial-photo ring sits 3 cm below the fine
  terrain so the seam cannot z-fight.

**Ground**
- Paint the plan into a **canvas texture** (14 px/m) laid over the terrain mesh. Per-vertex
  colours on a 0.5 m grid smear every path edge.
- Ground-cover polygons are listed in priority order — first match wins — and painted last to first.
- Terrain samples are integer centimetres above `zbase`; 0.5 m spacing gives 4–8 samples across a
  2–4 m bank, which is what makes it read as a bank.

**Plants**
- Instanced meshes per shape ("buckets"); a hidden instance is **scale 0**, not removed. Turn off
  frustum culling on them (instances move with the sliders) and null the bounding sphere after each
  layout or picking misses them.
- Flower dots and grass plumes must not be pickable, or they block the plant behind them.
- Winter branches must share the crown's frame (do not unit-fit them separately) or they will not
  line up with the crown they replace.
- Existing trees are drawn full size and ignore the growth slider.

**Camera and screen**
- Fit the overview by **projecting the plot corners** and searching the distance at which they all
  land inside the free area (not under the panel, header or season bar). A fixed distance frames a
  desktop and shows a portrait phone the plot from the side.
- Shift the projection centre into the free area (`setViewOffset`) instead of moving the target.
- DOM labels (zone letters, plant codes) only on the orthographic plan; in perspective they pile up.
- Keep the controls people actually drag (views, month, hour, growth) **pinned outside the scrolling panel**. Inside it they end up below a long flowering list, and on phones the panel is closed on arrival.
- Measure the header and the dock (`offsetHeight`) for the camera's safe margins and publish them as CSS variables; hard-coded pixel margins break the first time a row wraps.

**Sun**
- Azimuth is from **true north**; a projected CRS's grid north can differ by a few degrees
  (meridian convergence). Export `meta.site.north` and use it for the sun and the compass alike.
- Physically, ground under a low sun is dark and its shadows barely show. The viewer lifts a low
  sun's intensity on purpose (capped) — it is a model, not a photometer. Keep the cap or walls blow out.
- Daylight-saving is approximated (April–October); state that if someone reads exact minutes.

**Sun map and stages**
- Do not read shadow maps back from the GPU. Stamp shadows as flat shapes on a 2D canvas: a prism's shadow is its footprint, the footprint shifted by height ÷ tan(elevation), and the quads between; a crown's is an ellipse. Sum the stamps with `lighter` compositing at alpha 1/N.
- Skip samples with the sun under ~3°, and normalise by the samples actually used.
- Leafless trees cast no crown shadow — take the season state from the same function the plants use, and the sizes from the same growth stage; say both in the legend, along with "flat ground".
- A planting stage hides instances (scale 0) rather than rebuilding buckets; existing trees ignore it.

**Browsers**
- **No import map.** The add-ons import the bare specifier `three`; `fetch_three.sh` rewrites them
  to a relative path. Repeat that whenever three.js is upgraded.
- **Check for float render targets** (`EXT_color_buffer_float` / `_half_float`) before building the
  PMREM environment or the AO composer; without them render plainly instead of not at all.
- Put a **classic** `<script>` in the page that reports module load errors, script errors, a lost
  WebGL context and a 25 s timeout on the loading card. Phones show no console; "it is blank" is
  not a bug report, the line on the card is.
- PNG export reads the canvas **in the same task as the render** — no `preserveDrawingBuffer` needed.
  Cap the size by `maxTextureSize`.
- A local `python3 -m http.server` drops connections under parallel module loads now and then
  (`ERR_CONNECTION_RESET`); reload before suspecting the code.

## Files in this skill

- `references/scene-schema.md` — every field of `garden-scene.json`, units and allowed values
- `templates/viewer/` — the viewer, ready to copy (seven modules + `index.html`)
- `templates/example/build_scene.py` — a complete exporter for a made-up plot; `garden-scene.json` is its output
- `scripts/fetch_three.sh` — vendors three.js and the add-ons the viewer imports
