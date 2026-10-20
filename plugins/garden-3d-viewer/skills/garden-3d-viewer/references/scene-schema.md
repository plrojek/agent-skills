# garden-scene.json — the contract between exporter and viewer

One JSON object. Write it compact (`separators=(',', ':')`); a garden of ~80 plan entries with a
0.5 m terrain grid is about 300 kB (≈ 80 kB gzipped).

## Conventions

- **Site frame**: origin at a plot corner, **x east, y south**, metres. The viewer maps it to
  three.js as x → x, y → z, altitude → y, with the plot centroid at the origin.
- **Points** are `[x, y]`; **polygons** and **polylines** are lists of points; polygons are not closed
  (no repeated first point). Round to millimetres.
- **Altitudes** are metres in any datum; only differences matter.
- **Angles** are radians from +x towards +y (so π/2 points south), unless stated.
- **Months** are 1–12; as object keys they are strings (`"5"`).
- **Colours** are `#rrggbb`.
- A missing optional list may be `[]` or absent; `context` and `ortho` may be `null`.

## Top level

| Key | Type | Purpose |
|---|---|---|
| `meta` | object | title, counts, reference level, geography, UI overrides |
| `grid` | object | fine terrain around the plot |
| `context` | object \| null | coarse terrain under the aerial photo |
| `ortho` | object \| null | aerial photo and its georeference |
| `plot` | polygon | property outline |
| `ground` | list | ground-cover polygons painted on the terrain |
| `zones` | list | design zones (tints, labels, shopping-list groups) |
| `buildings` | list | extruded footprints: house, porch, terrace |
| `house` | object | roofs, PV, posts, openings |
| `paving` | list | hard surfaces |
| `pipes` | list | underground lines and their protection bands |
| `structures` | list | built volumes belonging to plan entries |
| `fences` | list | boundary fence runs |
| `lines` | list | crest lines and light mesh fences |
| `site` | list | furniture: pergola, playground, car … |
| `markers` | list | existing trees, gate and wicket posts |
| `views` | list | named eye-level views |
| `scatter` | list | flowers painted into the turf |
| `plants` | list | the planting plan |
| `looks` | object | seasonal appearance per species |
| `irrigation` | object, optional | irrigation plan: sources, sections, budget, materials |

## meta

```json
{ "generated": "2026-01-31", "version": "v3", "plateau": 100.0, "axis": 0.0,
  "site": { "lat": 52.0, "lon": 19.0, "north": 0.0, "utc": 1, "dst": true },
  "ui": { "title": "Garden", "currency": "zł", "layers": { "gas": "Utilities" }, "credit": "Aerial photo © …" },
  "counts": { "entries": 18, "positions": 31, "pieces": 522 } }
```

- `plateau` — the reference level in metres: scene height 0, and the level the house floor stands
  on (+2 cm). Use the finished ground level at the house.
- `axis` — direction of mowing stripes and paving joints (usually the house's long axis). Optional.
- `site` — omit to disable the real sun. `lat`/`lon` in degrees (east positive; two decimals are
  plenty). `north` = degrees **clockwise from the site's −y axis to true north**: 0 if −y is true
  north; for a projected CRS it is minus the meridian convergence at the plot. `utc` = standard
  offset in hours; `dst` adds one hour April–October.
- `ui.layers` — optional display names for layer keys `plants buildings slopes gas fences site zones ortho labels`
  (`gas` is the utilities layer). `ui.credit` is shown only when `ortho` is set.
- `counts` — shown in the header and the panel; `pieces` = sum of `qty`.

## grid (required) and context

```json
{ "x0": -8.0, "y0": -8.0, "nx": 97, "ny": 85, "step": 0.5, "zbase": 90, "alt": [1000, 1000, …] }
```

`alt` holds `nx × ny` **integer centimetres above `zbase`**, row by row from north to south
(`alt[j * nx + i]` is the ground at `x0 + i·step`, `y0 + j·step`). Cover the plot plus a margin of
about 8 m. `context` has the same shape with a coarse step (2 m) and covers the aerial photo.

Make the fine grid's edges fall on the coarse lattice (snap `x0`, `y0` and the far edges to
multiples of the coarse step): the photo ring's hole is then exactly the fine grid.

## ortho (optional aerial photo)

```json
{ "file": "ortho.jpg", "width": 1200, "height": 1200,
  "px2site": [0.2, 0.0, -104.0, 0.0, 0.2, -107.0], "source": "…", "fetched": "2026-01-31" }
```

`px2site = [a, b, c, d, e, f]` is the affine map from image pixel (col, row) to site metres:
`x = a·col + b·row + c`, `y = d·col + e·row + f`. For a north-up photo at 0.2 m/px in a site frame
that is a shifted projected CRS with y flipped, that is `[0.2, 0, x_of_left_edge, 0, 0.2, y_of_top_edge]`.
`file` is fetched relative to the page. About 240 × 240 m at 0.2 m/px (≈ 250 kB JPEG) is enough.
Check the photo's licence and put the required attribution in `meta.ui.credit`.

## ground

`[{ "cls": "lawn", "poly": [...] }, …]` in **priority order: the first polygon containing a point
decides**. Classes: `lawn` (seasonal tone, mowing stripes), `bed` and `veg` (soil with grain),
`play` (sand), `meadow`, `orchard`, `drive`. Anything else gets the plot's base green.

## zones

`{ "id": "A", "name": "Entrance", "color": "#e7d7b4", "desc": "tooltip text", "polys": [polygon, …] }`

A zone with no polygons is listed (disabled) but neither tinted nor labelled. `plants[].zone`
refers to `id`.

## buildings and house

```json
"buildings": [ { "kind": "house", "poly": [...], "h": 3.05 },
               { "kind": "porch", "poly": [...], "h": 0.12 }, { "kind": "terrace", "poly": [...], "h": 0.15 } ],
"house": {
  "roofs":    [ { "facets": [ [[x, y, height], …3 or 4 vertices], … ], "eave": [[x, y] ×4], "hEave": 2.95 } ],
  "pv":       [ [[x, y, height] ×4], … ],
  "posts":    [ { "poly": [...], "h": 3.05 } ],
  "openings": [ { "kind": "window", "label": "Kitchen window", "a": [x, y], "b": [x, y], "n": [nx, ny], "sill": 0.9, "h": 1.4 } ] }
```

- Heights in `facets`, `pv`, `hEave` are metres **above the house floor**.
- One `roofs` entry per rectangular wing: four facets of a hip roof (two trapezia, two triangles).
  The two eave vertices of each facet must be at exactly `hEave` — the tile texture is laid from them.
  `eave` is the roof rectangle (walls + overhang); the fascia board follows it.
- `openings`: `a`→`b` runs along the outer wall face, `n` is the unit outward normal.
  `kind`: `window`, `slider` (glazing bars every ~1.6 m), `door`, `garage`.
- The walk mode treats every `kind: "house"` footprint and every structure as solid.

## paving

`{ "kind": "drive", "poly": [...] }` — kinds: `drive`, `apron` (60 × 30 cm setts), `path`
(lighter 80 × 40 slabs), `patio` (60 × 60), `sand` (no joints), `greenhouse` (50 × 50). Painted over
the ground classes, with a kerb line.

## pipes

`{ "label": "Water main", "line": [[x, y], [x, y]], "zone": 1.5, "active": true, "band": [[x, y], [x, y]] }`

`zone` = half-width in metres of the no-planting band (0 = none); `band` = the part of the axis
inside the plot (the hatched band is drawn along it), or `null`. Disused lines (`active: false`) are dashed.

## structures

`{ "plant": "C2", "poly": [...], "h": 2.3, "color": "#d8e2e4", "glass": true, "soil": "#5e4a36" }`

An extruded footprint that belongs to plan entry `plant` (a click opens that entry's card).
`glass` draws it translucent with edges; `soil` adds a soil surface under the rim (raised beds).

## fences and lines

- `fences`: `{ "line": polyline, "h": 1.5 }` — posts every 2.5 m, two rails, translucent panel,
  following the terrain. Leave gate openings out of the polyline.
- `lines`: `{ "kind": "crest", "line": polyline }` — top edge of a bank, dashed with downhill ticks;
  `{ "kind": "mesh", "line": polyline, "plant": "G6" }` — a lighter 1 m mesh fence tied to a plan entry.

## site

`{ "kind": "pergola", "label": "Pergola 4 × 3.5 m", "pt": [x, y], "w": 4.0, "d": 3.5, "h": 2.6, "angle": 0.0, "vineLook": "Clematis" }`

`pt` is the centre, `w` along the object's own x axis, `d` across, `h` height. Kinds with built-in
geometry: `swing`, `slide`, `sandpit`, `pergola`, `bins`, `heatpump`, `car`. `vineLook` (pergola
only) names the look whose season colours the climber on top.

## markers

- `{ "kind": "tree", "label": "Existing oak", "pt": [x, y], "name": "Quercus robur", "dia": 9, "h": 14, "look": "Quercus", "note": "stays", "conifer": false }`
  — an existing tree: full size, untouched by the growth slider.
- `{ "kind": "gate" | "wicket", "label": "gate 4 m", "pt": [x, y] }` — a post with a label.

## views

`{ "id": "terrace", "label": "From the terrace", "from": [x, y], "to": [x, y], "step": 1.5 }`

An eye at 1.6 m standing at `from` (moved `step` metres towards `to`), looking at `to`. Each
becomes a view button; the **last** one is where the walk starts.

## scatter

`{ "look": "meadow", "density": 3.2, "share": 0.75, "polys": [polygon, …] }`

Flower specks painted into the ground texture in the months the look flowers: `density` points per
m², `share` of them shown. Use for a flower meadow and for bulbs naturalised in a lawn.

## plants

```json
{ "id": "B1", "zone": "B", "latin": "Hydrangea paniculata", "polish": "panicle hydrangea — border by the terrace",
  "cultivar": "‘Limelight’", "qty": 5, "size": "C5", "where": "every 2 m in front of the terrace",
  "notes": "prune in March", "when": "IV 2027", "price": "35–60", "priceLo": 35.0, "priceHi": 60.0, "year": 2027,
  "sym": "hyd", "r": 0.8,
  "variants": [ { "name": "Hydrangea paniculata", "label": "Hydrangea paniculata ‘Limelight’", "kind": "shrub",
                  "dia": 1.6, "h": 1.28, "look": "Hydrangea paniculata", "headLen": 1.45, "headSize": 0.3 } ],
  "ptVariant": [0, 0, 0, 0, 0],
  "pts": [[10.6, 18.4], …], "rows": [], "areas": [] }
```

- `polish` is the **common name** shown as the card title (the key name is historical); text
  before an em dash is used as the short name in tooltips. `latin` + `cultivar` form the subtitle.
- `price` is display text; `priceLo` / `priceHi` are per-piece numbers for the shopping list (`null`
  = not counted); `year` groups by planting year (`null` = "no date").
- `sym` is the plan symbol. The viewer only tests two values: `drift` (never drawn in 3D — use
  `scatter`) and `none` (no label on the plan).
- Where it grows — any combination:
  - `pts`: one plant per point, drawn as `variants[ptVariant[k]]`;
  - `rows`: polylines — `hedge` becomes a continuous clipped hedge, `row` plants every 0.45 m;
  - `areas`: polygons filled with scattered plants of `variants[0]` (about 1.3 per m², max 260).
- `variants[]` — one per distinct species in the entry:

| Field | Meaning |
|---|---|
| `name` | botanical name of this variant (matched against `looks` by the exporter) |
| `label` | display name in the calendar and highlight pill |
| `kind` | `tree`, `columnar`, `conifer`, `shrub`, `hedge`, `row`, `tuft` (grass), `clump` (peony, pot), `climber`, `ground` (cover, bed), `arch`, `bench`, `volume` (drawn by `structures`), `skip` (drawn elsewhere) |
| `dia`, `h` | **mature** crown diameter and height in metres; for `arch`/`bench` width and height |
| `look` | key into `looks`; without it the plant is one green all year |
| `angle` | `arch` / `bench` only: rotation, radians |
| `headLen`, `headSize` | flower heads: elongation (1 = round, 1.45 = panicle) and size |

A `ground` variant on a single point with `dia` > 1.2 m is filled as a round patch.

## looks

```json
"Malus domestica": { "habit": "round", "leaf": "#5f8440", "spring": "#8fae52", "bark": "#6b543a",
                     "leaves": [4, 10], "flowers": { "5": ["#f6e3e6", "cover"] },
                     "fruit": { "9": "#c8402e", "10": "#c8402e" }, "autumn": { "10": "#c9a640" } }
```

| Field | Meaning |
|---|---|
| `habit` | crown shape. Trees: `round oval spread vase column pyramid airy umbrella`; conifers: `fir spire`; shrubs and perennials: `mound low`; grasses: `tuft` |
| `leaf` | summer foliage colour (default mid green) |
| `spring` | colour in the first month in leaf (default: `leaf` slightly lighter; the crown is also 12 % smaller) |
| `leaves` | `[first, last]` month in leaf, default `[4, 10]` |
| `flowers` | `{month: colour}` or `{month: [colour, …, mode]}` — modes: `dots` (default), `cover` (the whole crown takes the colour: cherries, apples), `heads` (large heads on top: hydrangeas), `plume` (grasses), `mix` (several colours of dots) |
| `fruit` | `{month: colour}` — small dots, shown when not in flower |
| `autumn` | `{month: colour}` — crown colour in those months |
| `winter` | `keep` (evergreen), `marcescent` (dry leaves stay, `wcolour`), `straw` (stands dry, `wcolour`), `hide` (gone); default = bare branches for trees, translucent twigs for shrubs |
| `wcolour` | winter colour for `marcescent` / `straw` |
| `bark` | trunk colour for `airy` trees and the colour of bare branches |
| `height`, `fh` | grasses: height in flower, and the foliage share of it (0.55) |
| `winterPlume` | grasses: plumes stay through winter |

The exporter matches a look to a variant by substring of the botanical name, first match wins —
list specific keys (`Prunus serrulata`) before generic ones (`Prunus`).

## irrigation (optional)

Leave the key out and the irrigation layer, panel section and cost rows disappear.

```json
{ "sources": [ { "kind": "tank", "label": "Rainwater tank 3 m³", "pt": [x, y], "r": 0.9 },
               { "kind": "valves", "label": "Valve box", "pt": [x, y] }, { "kind": "tap", "label": "Garden tap", "pt": [x, y] },
               { "kind": "mains", "label": "Water meter", "pt": [x, y] } ],
  "hose": 25.0,
  "main": [ { "kind": "trench", "line": polyline } ],
  "sections": [ { "id": "N1", "name": "Kitchen garden", "color": "#2f7fb8", "source": "tank", "note": "", "temporary": 0, "optional": false,
                  "plants": ["C1", "C2"], "emitters": 140, "heads": [], "lineM": 47.0, "feedM": 6.0,
                  "trunkM": { "trench": 12.0, "sleeve": 0, "surface": 0 }, "demand": 520, "flow": 322, "minutes": 97, "groups": 1,
                  "trunk": [ { "kind": "trench", "line": polyline } ], "laterals": [polyline, …], "feeds": [polyline, …],
                  "rings": [[x, y, r], …] } ],
  "budget": { "week": 950, "tank": 3000, "autonomyDays": 22.1, "roofWeek": 2100, "lawnWeek": 0 },
  "bom": [ { "item": "Drip line 16 mm", "qty": 80, "unit": "m", "lo": 2.5, "hi": 4.5 } ], "bomOptional": [],
  "cost": [900, 1900], "costOptional": [0, 0] }
```

- `sources` — drawn as small objects on the ground (tank lid, valve box, tap post, meter cover); every `tap` gets a dashed circle of radius `hose` when the hose-reach layer is on.
- `main` and each section's `trunk` — supply pipes. `kind`: `trench` (solid), `sleeve` (solid on a white casing: under paving), `surface` (dashed).
- `laterals` — drip lines; `rings` — a drip ring round a tree, `[x, y, radius]`; `feeds` — blind pipe joining laterals and rings to the trunk (thin dashed).
- `heads` — sprinklers as `[x, y, reach radius]`; a section with heads is listed by head count instead of line length.
- `plants` — ids of the plan entries the section waters: picking the section highlights them.
- `demand` litres per week in the peak month, `flow` litres per hour, `minutes` run time per week, `groups` how many valve groups a sprinkler section needs.
- `temporary` — number of seasons a provisional section stays (0 = permanent); `optional` — drawn fainter until picked.
- `budget` — shown under the section list: weekly drip demand, days a full tank lasts without rain, weekly roof yield, weekly lawn demand.
- `bom` / `bomOptional` — materials with unit price ranges; they go into the CSV. `cost` / `costOptional` — their totals, shown as extra rows of the cost table.
