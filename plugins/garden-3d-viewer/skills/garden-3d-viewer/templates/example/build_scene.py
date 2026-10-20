#!/usr/bin/env python3
"""Example exporter: writes a complete garden-scene.json for a made-up 32 x 26 m plot.

    python3 build_scene.py [out.json]        # default: garden-scene.json next to this file

Use it two ways: run it as is to see the viewer working, then replace the DATA section with a
real plan. Everything below DATA is geometry plumbing you can keep. Standard library only.

Site frame: origin at the plot's north-west corner, x east, y SOUTH, metres. Altitudes in metres
(any datum — only differences matter). Angles in radians, measured from +x towards +y.
"""
import json, math, re, sys, os, datetime

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), 'garden-scene.json')

# =============================================================================== DATA
TITLE, CURRENCY, VERSION = 'Ogród przykładowy', 'zł', 'v1'
GEO = {'lat': 52.0, 'lon': 19.0, 'north': 0.0, 'utc': 1, 'dst': True}   # north: degrees clockwise from the -y axis to true north

PLOT = [(0, 0), (32, 0), (32, 26), (0, 26)]
LEVEL = 100.0                                   # finished ground level at the house, m

def surface(x, y):
    """Ground altitude at a site point. Here: flat, with a 1.4 m bank falling east beyond x = 28."""
    drop = max(0.0, min(1.0, (x - 28.0) / 3.0))
    return LEVEL - 1.4 * drop * drop * (3 - 2 * drop)
CREST = [(28, 0), (28, 26)]                     # top edge of the bank, drawn dashed with downhill ticks

HOUSE = [(9, 5), (21, 5), (21, 14), (9, 14)]    # outer wall line
WALL_H, EAVE_H, OVERHANG, PITCH = 3.05, 2.95, 0.6, 30.0
TERRACE = [(11, 14), (19, 14), (19, 17.5), (11, 17.5)]
PORCH = [(9, 8), (9, 10.4), (7.8, 10.4), (7.8, 8)]
# exterior openings: (kind, label, wall point A, wall point B, outward normal, sill, height)
OPENINGS = [
    ('door',   'Drzwi wejściowe', (9, 8.7), (9, 9.8),   (-1, 0), 0.0, 2.1),
    ('garage', 'Brama garażowa',  (9, 10.9), (9, 13.5), (-1, 0), 0.0, 2.2),
    ('slider', 'Wyjście na taras', (12.5, 14), (17.5, 14), (0, 1), 0.0, 2.3),
    ('window', 'Okno kuchni',     (12, 5), (13.6, 5),   (0, -1), 0.9, 1.4),
    ('window', 'Okno sypialni',   (17, 5), (18.6, 5),   (0, -1), 0.9, 1.4),
    ('window', 'Okno wschodnie',  (21, 8), (21, 10),    (1, 0),  0.9, 1.4),
]
PV_ROWS = [(1.0, 2.05), (2.25, 3.3)]            # rows on the south roof face: metres up the slope from the eave

GATE, WICKET = (0, 12.2), (0, 9.2)              # mid points of the openings in the west fence
PAVING = [                                      # kind: drive | apron | path | patio | sand | greenhouse
    ('drive', [(0, 10.7), (9, 10.7), (9, 13.7), (0, 13.7)]),
    ('path',  [(0, 8.6), (7.8, 8.6), (7.8, 9.8), (0, 9.8)]),
    ('patio', [(22.5, 15), (26.5, 15), (26.5, 18.5), (22.5, 18.5)]),
    ('sand',  [(2, 19), (8, 19), (8, 24), (2, 24)]),
]
# ground cover, FIRST match wins: lawn | bed | veg | play | meadow | orchard | drive
GROUND = [
    ('bed',    [(0, 0), (28, 0), (28, 1.6), (0, 1.6)]),
    ('bed',    [(9.6, 17.6), (20.4, 17.6), (20.4, 19.2), (9.6, 19.2)]),
    ('veg',    [(22, 1.8), (27.6, 1.8), (27.6, 9), (22, 9)]),
    ('play',   [(2, 19), (8, 19), (8, 24), (2, 24)]),
    ('meadow', [(28, 0), (32, 0), (32, 26), (28, 26)]),
    ('lawn',   [(0, 0), (28, 0), (28, 26), (0, 26)]),
]
ZONES = [   # id, name, colour, description, polygons (the viewer tints them and labels the largest)
    ('A', 'Wejście',          '#e7d7b4', 'podjazd, ścieżka, rabata przy płocie',  [[(0, 0), (9, 0), (9, 14), (0, 14)]]),
    ('B', 'Trawnik i taras',  '#cfe0b0', 'trawnik główny, rabata przy tarasie',  [[(0, 14), (22, 14), (22, 26), (0, 26)]]),
    ('C', 'Warzywnik',        '#e3c9a4', 'szklarnia i grządki',                  [[(21.5, 0), (28, 0), (28, 10), (21.5, 10)]]),
    ('D', 'Sad i patio',      '#d9e6a8', 'drzewa owocowe, patio z pergolą',      [[(22, 10), (28, 10), (28, 26), (22, 26)]]),
    ('E', 'Skarpa',           '#c9cf9a', 'łąka kwietna i okrywowe na skarpie',   [[(28, 0), (32, 0), (32, 26), (28, 26)]]),
]
UTILITIES = [  # label, axis (two points), half-width of the no-tree band (0 = none), in service?
    ('Wodociąg — pas bez drzew 1,5 m', ((14, 26), (32, 19)), 1.5, True),
]
EXISTING_TREES = [('Dąb istniejący', (30.5, 23.5), 'Quercus robur', 9.0, 14.0, 'istniejący — zostaje')]
# site furniture: kind (swing | slide | sandpit | pergola | bins | heatpump | car), label, centre, w, d, h, angle
SITE = [
    ('pergola', 'Pergola 4 × 3,5 m', (24.5, 16.75), 4.0, 3.5, 2.6, 0.0, 'Clematis'),
    ('swing',   'Huśtawka',          (3.6, 21.5),  2.5, 1.8, 2.2, math.pi / 2, None),
    ('sandpit', 'Piaskownica',       (6.3, 22.2),  2.4, 2.4, 0.3, 0.0, None),
    ('car',     'Auto',              (5.2, 12.2),  4.6, 1.8, 1.45, 0.0, None),
    ('bins',    'Wiata śmietnikowa', (1.4, 6.6),   2.2, 1.2, 1.3, math.pi / 2, None),
]
# structures drawn as extruded footprints, tied to a plan entry by its id
STRUCTURES = {'C2': {'h': 2.3, 'color': '#d8e2e4', 'glass': True}, 'C3': {'h': 0.4, 'color': '#8d6f4c', 'soil': '#5e4a36'}}

# Seasonal looks. Keys are matched as substrings of the plant's latin name (first match wins).
#   habit: round oval spread vase column pyramid airy umbrella (trees) | fir spire (conifers) | mound low | tuft
#   leaf, spring, bark: colours;  leaves: (first, last) month in leaf, default (4, 10)
#   flowers / fruit / autumn: {month: colour}; flowers may be [colour, ..., mode] with mode
#       'cover' (whole crown takes the colour), 'dots' (default), 'heads', 'plume', 'mix'
#   winter: 'keep' (evergreen) | 'marcescent' | 'straw' | 'hide'; default = bare branches / twigs
LOOKS = [
    ('Carpinus', dict(habit='mound', leaf='#5a7a38', autumn={10: '#c9a449'}, winter='marcescent', wcolour='#a8763f')),
    ('Prunus serrulata', dict(habit='vase', leaf='#5d7f3c', spring='#9c7a4a', flowers={4: ['#f4b6cf', 'cover'], 5: ['#f0a8c6', 'cover']}, autumn={10: '#d9772e'})),
    ('Malus domestica', dict(habit='round', leaf='#5f8440', flowers={5: ['#f6e3e6', 'cover']}, fruit={9: '#c8402e', 10: '#c8402e'}, autumn={10: '#c9a640'})),
    ('Acer', dict(habit='oval', leaf='#5b8a3a', autumn={10: '#d2452a', 11: '#b8371f'})),
    ('Betula', dict(habit='airy', leaf='#7fa24a', bark='#e9e6dc', autumn={10: '#e2c23f'})),
    ('Quercus', dict(habit='spread', leaf='#4f7434', autumn={10: '#b07a35', 11: '#9a6a30'})),
    ('Picea', dict(habit='fir', leaf='#3f6b46', winter='keep')),
    ('Hydrangea paniculata', dict(habit='mound', leaf='#6a8c47', flowers={7: ['#f1f0dc', 'heads'], 8: ['#f3e3e0', 'heads'], 9: ['#e2a8b6', 'heads'], 10: ['#c98a96', 'heads']}, autumn={10: '#b9963f'})),
    ('Lavandula', dict(habit='low', leaf='#8a9a7c', flowers={6: '#7a68c2', 7: '#7a68c2', 8: '#8a7ac6'}, winter='keep')),
    ('Calamagrostis', dict(habit='tuft', height=1.6, fh=0.55, leaf='#6f8d47', flowers={6: ['#b89676', 'plume'], 7: ['#c7a67a', 'plume'], 8: ['#d2b884', 'plume'], 9: ['#d2b884', 'plume']}, autumn={10: '#cdb57e'}, winter='straw', wcolour='#d0bb88', winterPlume=True)),
    ('Rubus', dict(habit='mound', leaf='#5f8a40', fruit={7: '#b3263c', 8: '#b3263c', 9: '#b3263c'}, autumn={10: '#c9b04a'})),
    ('Rosa', dict(habit='mound', leaf='#557c3a', flowers={6: '#d2456f', 7: '#d2456f', 8: '#d85a80', 9: '#d2456f'}, fruit={10: '#b8392a'})),
    ('Clematis', dict(habit='mound', leaf='#5f8742', flowers={6: '#6f5bb5', 7: '#6f5bb5', 8: '#7c69bd'})),
    ('Cotoneaster', dict(habit='low', leaf='#4f733a', flowers={5: '#f0ead8'}, fruit={9: '#c23a2a', 10: '#c23a2a', 11: '#c23a2a'}, winter='keep')),
    ('rabata', dict(habit='mound', leaf='#6f8a4c', winter='straw', wcolour='#bba27a', flowers={5: ['#7a5ab0', '#8f6fc4', 'mix'], 6: ['#6c64b8', '#d5a2c4', 'mix'], 7: ['#c96a9c', '#8e73c9', 'mix'], 8: ['#e0a05e', '#c5689c', 'mix'], 9: ['#c96a8e', '#8a8fcc', 'mix']})),
    ('Crocus', dict(habit='low', leaf='#7fa05a', leaves=(3, 5), winter='hide', flowers={3: ['#a88bd6', '#f1e7a8', 'mix'], 4: ['#f4f1e4', '#efe6b8', 'mix']})),
    ('łąka', dict(habit='low', leaf='#9aab62', winter='straw', wcolour='#c2b27e', flowers={5: ['#f3f0e2', '#e9d86a', 'mix'], 6: ['#f3f0e2', '#6f7fc6', '#e9d86a', 'mix'], 7: ['#6f7fc6', '#e2c24a', '#b96fb0', 'mix'], 8: ['#b96fb0', '#e2c24a', 'mix']})),
]

# The plan. sym decides how an entry is drawn:
#   tree flower fruit conifer -> tree at each pt        hyd shrub -> shrub at each pt (r = radius)
#   grass -> tuft   peony pot -> clump   climber -> column   struct -> see STRUCT / STRUCTURES
#   hedge row -> along each polyline of rows            bed cover area -> scattered over each polygon of areas
#   drift none -> nothing in 3D (drift is painted into the lawn via SCATTER)
PLANTS = []
def plant(pid, zone, latin, polish, qty, size, where, notes, when, price, sym, r=0.0, h=None, pts=(), rows=(), areas=(), cultivar=''):
    PLANTS.append(dict(id=pid, zone=zone, latin=latin, polish=polish, cultivar=cultivar, qty=qty, size=size, where=where,
                       notes=notes, when=when, price=price, sym=sym, r=r, h=h, pts=list(pts), rows=list(rows), areas=list(areas)))

plant('A1', 'A', 'Carpinus betulus', 'grab pospolity — żywopłot', 54, '60–80 cm, gołokorzeniowe', '18 mb × 3 szt./mb wzdłuż płotu N',
      'strzyżony do 1,6 m; trzyma suche liście zimą', 'XI 2026', '4–7', 'hedge', h=1.6, rows=[[(0.6, 0.7), (18.6, 0.7)]])
plant('A2', 'A', 'Prunus serrulata', 'wiśnia piłkowana — soliter przy wejściu', 1, 'Pa 180, C20', 'przy furtce', 'kwitnie IV–V',
      'IV 2027', '250–400', 'flower', r=2.2, h=6.0, pts=[(3.5, 4.2)], cultivar='‘Kanzan’')
plant('A3', 'A', 'Rosa ‘Laguna’, Rosa ‘Jasmina’', 'róże pnące na łukach', 4, 'C5', 'po jednej u stopy każdego łuku', 'cięcie III',
      'IV 2027', '40–70', 'climber', pts=[(2.5, 8.4), (2.5, 10.0), (5.5, 8.4), (5.5, 10.0)])
plant('A4', 'A', 'łuk różany', 'łuki nad ścieżką', 2, 'stal, 2,0 × 2,6 m', 'nad ścieżką do drzwi', '', '2027', '400–900', 'struct',
      pts=[(2.5, 9.2), (5.5, 9.2)])
plant('B1', 'B', 'Hydrangea paniculata', 'hortensja bukietowa — rabata przy tarasie', 5, 'C5', 'co 2 m przed tarasem', 'cięcie III',
      'IV 2027', '35–60', 'hyd', r=0.8, pts=[(10.6, 18.4), (12.8, 18.4), (15, 18.4), (17.2, 18.4), (19.4, 18.4)], cultivar='‘Limelight’')
plant('B2', 'B', 'Calamagrostis ×acutiflora', 'trzcinnik ostrokwiatowy', 6, 'C2', 'między hortensjami', 'ciąć w III', 'IV 2027', '12–20',
      'grass', r=0.35, pts=[(11.7, 18.9), (13.9, 18.9), (16.1, 18.9), (18.3, 18.9), (9.9, 18.9), (20.1, 18.9)], cultivar='‘Karl Foerster’')
plant('B3', 'B', 'Lavandula angustifolia', 'lawenda — obwódka tarasu', 24, 'P9', '4 szt./mb wzdłuż krawędzi tarasu', '', 'V 2027', '6–10',
      'row', rows=[[(11.2, 17.75), (18.8, 17.75)]], cultivar='‘Hidcote’')
plant('B4', 'B', 'Crocus + Narcissus', 'krokusy i narcyzy w trawniku', 300, 'cebule', 'plama w trawniku przed tarasem', 'kosić po zaschnięciu liści',
      'X 2026', '0,6–1,2', 'drift', areas=[[(11, 20.5), (20, 20.5), (21, 23.5), (10, 23.5)]])
plant('B5', 'B', 'Acer platanoides', 'klon — cień nad placem zabaw', 1, 'Pa 200, obw. 10–12', 'narożnik SW', '', 'XI 2026', '300–500',
      'tree', r=3.0, h=10.0, pts=[(2.8, 17.2)])
plant('C1', 'C', 'Rubus idaeus', 'malina jesienna', 14, 'sadzonki', 'rząd przy płocie E warzywnika', 'ciąć całość w II', 'X 2026', '8–14',
      'row', rows=[[(27.3, 2.2), (27.3, 8.8)]], cultivar='‘Polka’')
plant('C2', 'C', 'szklarnia', 'szklarnia 3 × 2 m', 1, 'szkło hartowane', 'w narożniku warzywnika', '', '2027', '', 'struct',
      areas=[[(22.3, 2.1), (25.3, 2.1), (25.3, 4.1), (22.3, 4.1)]])
plant('C3', 'C', 'grządki podwyższone', 'grządki 2,4 × 1,2 × 0,4 m', 2, 'modrzew', 'obok szklarni', '', '2027', '250–400', 'struct',
      areas=[[(22.4, 5.2), (24.8, 5.2), (24.8, 6.4), (22.4, 6.4)], [(22.4, 7.2), (24.8, 7.2), (24.8, 8.4), (22.4, 8.4)]])
plant('D1', 'D', 'Malus domestica ‘Szampion’ 2, Malus domestica ‘Ligol’ 1', 'jabłonie na podkładce półkarłowej', 3, 'dwulatki', 'rząd w sadzie, co 4 m',
      'cięcie II–III', 'XI 2026', '40–70', 'fruit', r=1.8, h=4.0, pts=[(24.5, 11.5), (24.5, 21.5), (24.5, 24.6)])
plant('D2', 'D', 'Clematis ‘Jackmanii’', 'powojnik na pergoli', 2, 'C2', 'przy słupach pergoli', '', 'V 2027', '25–40', 'climber',
      pts=[(22.7, 15.2), (26.3, 15.2)])
plant('D3', 'D', 'Picea omorika', 'świerk serbski — osłona od N', 2, 'C10, 100–125 cm', 'za warzywnikiem', '', 'IX 2027', '80–140', 'conifer',
      r=1.4, h=9.0, pts=[(20, 2.6), (20.6, 21.8)])
plant('E1', 'E', 'Cotoneaster dammeri', 'irga Dammera — okrywa skarpy', 60, 'P9', '4 szt./m² na skarpie', 'mata + ściółka', 'IX 2027', '5–9',
      'cover', r=0.3, areas=[[(28.4, 0.5), (30.6, 0.5), (30.6, 12), (28.4, 12)]])
plant('E2', 'E', 'łąka kwietna', 'mieszanka łąki kwietnej', 1, 'nasiona 2 g/m²', 'dolna część skarpy', 'kosić 2× w roku', 'IV 2027', '120–200', 'none')
plant('B6', 'B', 'rabata bylinowa', 'rabata bylinowo-trawiasta przy płocie N', 40, 'P9–C2', '6 szt./m²', '', 'V 2027', '8–18', 'bed', r=0.3,
      areas=[[(19, 0.2), (21.3, 0.2), (21.3, 1.5), (19, 1.5)]])

# point structures: id -> (primitive, height, width).  arch = rose arch, bench = bench.  + their angle
STRUCT = {'A4': ('arch', 2.6, 2.0)}
STRUCT_ANGLE = {'A4': math.pi / 2}              # the arch spans ACROSS the east-west path
SCATTER = [('łąka', 3.2, 0.75, [p for c, p in GROUND if c == 'meadow']),     # look, points per m², share shown, polygons
           ('Crocus', 5.0, 1.0, next(p['areas'] for p in PLANTS if p['id'] == 'B4'))]
EYE_VIEWS = [('terrace', 'Z tarasu', (15, 15.75), (15, 22), 1.5), ('gate', 'Od bramy', GATE, (15, 9.5), 2.0)]

# Irrigation (optional block). Hand-placed here to keep the example short; in a real exporter derive the
# laterals from the plan (a line along every hedge and row, parallel lines across every bed, a ring per tree)
# and compute lengths, emitters, flow and run time from them — see references/scene-schema.md.
TANK, VALVES_PT, TAP = (20.5, 20.5), (20.5, 19.2), (21.1, 12.0)
IRRIGATION = [   # id, name, colour, plan entries, trunk [(kind, polyline)], drip lines, rings (x, y, r), litres/week
    ('N1', 'Rabata przy tarasie i żywopłot', '#2f7fb8', ['A1', 'B1', 'B2', 'B3'],
     [('trench', [VALVES_PT, (20.5, 18.4)]), ('trench', [VALVES_PT, (21.6, 19.2), (21.6, 1.2)])],
     [[(9.9, 18.4), (20.4, 18.4)], [(9.9, 18.9), (20.4, 18.9)], [(11.2, 17.75), (18.8, 17.75)], [(0.6, 0.7), (18.6, 0.7)]], [], 520),
    ('N2', 'Warzywnik i sad', '#7a5fc0', ['C1', 'C2', 'C3', 'D1'],
     [('trench', [VALVES_PT, (23.6, 19.2), (23.6, 9.4)]), ('sleeve', [(23.6, 19.2), (23.6, 18.5)])],
     [[(27.3, 2.2), (27.3, 8.8)], [(22.6, 5.5), (24.6, 5.5)], [(22.6, 6.1), (24.6, 6.1)], [(22.6, 7.5), (24.6, 7.5)], [(22.6, 8.1), (24.6, 8.1)]],
     [(24.5, 11.5, 0.4), (24.5, 21.5, 0.4), (24.5, 24.6, 0.4)], 430),
]

# =============================================================================== PLUMBING
STEP, MARGIN, CSTEP, ZBASE = 0.5, 8.0, 2.0, math.floor(LEVEL - 10)

def P(pt): return [round(pt[0], 3), round(pt[1], 3)]
def poly(pg): return [P(q) for q in pg]
def centroid(pg): return (sum(q[0] for q in pg) / len(pg), sum(q[1] for q in pg) / len(pg))

def look_for(*names):
    for n in names:
        for key, lk in LOOKS:
            if key in n: return key, lk
    return None, None
LOOK_TABLE = {}
def look_id(*names):
    key, lk = look_for(*names)
    if key and key not in LOOK_TABLE:
        LOOK_TABLE[key] = {k: ({str(m): v for m, v in val.items()} if isinstance(val, dict) else list(val) if isinstance(val, tuple) else val)
                           for k, val in lk.items()}
    return key

def price_range(txt):
    num = r'(\d+(?:[.,]\d+)?)'
    m = re.search(num + r'\s*[–-]\s*' + num, txt or '')
    if m: return float(m.group(1).replace(',', '.')), float(m.group(2).replace(',', '.'))
    m = re.search(num, txt or '')
    return (float(m.group(1).replace(',', '.')),) * 2 if m else (None, None)

def species_list(p):
    """'Malus ‘A’ 2, Malus ‘B’ 1' -> one name per plant, so a mixed entry sizes and colours each plant on its own"""
    out = []
    for part in re.split(r',\s*|\s\+\s', p['latin']):
        toks = part.strip().split(' ')
        if toks and toks[-1].isdigit(): out += [' '.join(toks[:-1])] * int(toks[-1])
        else: out.append(part.strip())
    return out or [p['latin']]

def render(p):
    """drawing primitive + mature size for one plant of an entry"""
    sym, r, h = p['sym'], p['r'], p['h']
    if sym in ('tree', 'flower', 'fruit'): return {'kind': 'tree', 'dia': round(2 * r, 2), 'h': h or round(3.2 * r, 2)}
    if sym == 'conifer': return {'kind': 'conifer', 'dia': round(2 * r, 2), 'h': h or round(5 * r, 2)}
    if sym == 'hyd':     return {'kind': 'shrub', 'dia': round(2 * r, 2), 'h': h or round(max(0.7, 1.6 * r), 2)}
    if sym == 'shrub':   return {'kind': 'shrub', 'dia': round(2 * r, 2), 'h': h or round(min(2.5, 2 * r), 2)}
    if sym == 'grass':   return {'kind': 'tuft', 'dia': round(2 * r, 2), 'h': h or 1.6}
    if sym == 'climber': return {'kind': 'climber', 'dia': 0.7, 'h': h or 2.5}
    if sym == 'hedge':   return {'kind': 'hedge', 'dia': 0.6, 'h': h or 1.4}
    if sym == 'row':     return {'kind': 'row', 'dia': 0.5, 'h': h or 0.5}
    if sym in ('peony', 'pot'): return {'kind': 'clump', 'dia': 0.8, 'h': h or 0.7}
    if sym == 'struct':
        if p['id'] in STRUCT: k, hh, w = STRUCT[p['id']]; return {'kind': k, 'dia': w, 'h': hh, 'angle': STRUCT_ANGLE.get(p['id'], 0.0)}
        return {'kind': 'volume', 'dia': 1.0, 'h': STRUCTURES.get(p['id'], {}).get('h', 1.0)}
    return {'kind': 'ground', 'dia': round(max(0.4, 2 * r), 2), 'h': h or 0.4}       # bed, cover, area, drift, none

def hip_roof(rect, he, pitch_deg):
    """Hip roof over an axis-aligned rectangle (x0, y0, x1, y1): four facets as lists of (x, y, height).
    An L-shaped house is TWO of these, one per wing — never one offset of the L outline."""
    x0, y0, x1, y1 = rect; t = math.tan(math.radians(pitch_deg)); W, D = x1 - x0, y1 - y0
    if W <= D:
        h = he + t * W / 2; xc = (x0 + x1) / 2; r0, r1 = (xc, y0 + W / 2, h), (xc, y1 - W / 2, h)
        return [[(x0, y0, he), (x0, y1, he), r1, r0], [(x1, y1, he), (x1, y0, he), r0, r1],
                [(x0, y0, he), r0, (x1, y0, he)], [(x1, y1, he), r1, (x0, y1, he)]]
    h = he + t * D / 2; yc = (y0 + y1) / 2; r0, r1 = (x0 + D / 2, yc, h), (x1 - D / 2, yc, h)
    return [[(x0, y0, he), r0, r1, (x1, y0, he)], [(x1, y1, he), r1, r0, (x0, y1, he)],
            [(x0, y1, he), r0, (x0, y0, he)], [(x1, y0, he), r1, (x1, y1, he)]]

def irrigation(emitter_lh=2.3, pitch=0.33, tank_l=3000):
    plen = lambda pl: sum(math.dist(pl[i], pl[i + 1]) for i in range(len(pl) - 1))
    secs = []
    for sid, name, col, ids, trunk, lines, rings, litres in IRRIGATION:
        line_m = sum(plen(l) for l in lines) + sum(2 * math.pi * r for _, _, r in rings)
        emitters = round(sum(plen(l) for l in lines) / pitch) + 4 * len(rings)
        flow = emitters * emitter_lh
        secs.append({'id': sid, 'name': name, 'color': col, 'source': 'tank', 'note': '', 'temporary': 0, 'optional': False, 'plants': ids,
                     'emitters': emitters, 'heads': [], 'lineM': round(line_m, 1), 'feedM': 0, 'feeds': [],
                     'trunkM': {k: round(sum(plen(pl) for kk, pl in trunk if kk == k), 1) for k in ('trench', 'sleeve', 'surface')},
                     'demand': litres, 'flow': round(flow), 'minutes': round(litres / flow * 60), 'groups': 1,
                     'trunk': [{'kind': k, 'line': poly(pl)} for k, pl in trunk], 'laterals': [poly(l) for l in lines],
                     'rings': [[x, y, r] for x, y, r in rings]})
    week = sum(s['demand'] for s in secs)
    bom = [{'item': 'Linia kroplująca 16 mm', 'qty': round(sum(s['lineM'] for s in secs)), 'unit': 'm', 'lo': 2.5, 'hi': 4.5},
           {'item': 'Rura PE 32 mm', 'qty': round(sum(s['trunkM']['trench'] + s['trunkM']['sleeve'] for s in secs)), 'unit': 'm', 'lo': 5, 'hi': 9},
           {'item': 'Elektrozawór + filtr + reduktor', 'qty': len(secs), 'unit': 'kpl.', 'lo': 170, 'hi': 300},
           {'item': 'Sterownik', 'qty': 1, 'unit': 'szt.', 'lo': 300, 'hi': 800}]
    return {'sources': [{'kind': 'tank', 'label': 'Zbiornik na deszczówkę 3 m³', 'pt': P(TANK), 'r': 0.9},
                        {'kind': 'valves', 'label': 'Skrzynka zaworowa', 'pt': P(VALVES_PT)}, {'kind': 'tap', 'label': 'Kran ogrodowy', 'pt': P(TAP)}],
            'hose': 20.0, 'main': [], 'sections': secs,
            'budget': {'week': week, 'tank': tank_l, 'autonomyDays': round(tank_l / (week / 7), 1), 'roofWeek': 2100, 'lawnWeek': 0},
            'bom': bom, 'bomOptional': [],
            'cost': [round(sum(b['qty'] * b['lo'] for b in bom)), round(sum(b['qty'] * b['hi'] for b in bom))], 'costOptional': [0, 0]}

def build():
    xs = [q[0] for q in PLOT]; ys = [q[1] for q in PLOT]
    # the fine grid's edges sit on the coarse lattice, so an orthophoto ring (if you add one) meets it exactly
    X0 = math.floor((min(xs) - MARGIN) / CSTEP) * CSTEP; Y0 = math.floor((min(ys) - MARGIN) / CSTEP) * CSTEP
    NX = int(round((math.ceil((max(xs) + MARGIN) / CSTEP) * CSTEP - X0) / STEP)) + 1
    NY = int(round((math.ceil((max(ys) + MARGIN) / CSTEP) * CSTEP - Y0) / STEP)) + 1
    alt = [round((surface(X0 + i * STEP, Y0 + j * STEP) - ZBASE) * 100) for j in range(NY) for i in range(NX)]   # integer cm

    plants = []
    for p in PLANTS:
        names, variants, per_pt, index = species_list(p), [], [], {}
        if p['pts'] and p['sym'] not in ('hedge', 'row', 'bed', 'cover', 'area', 'drift', 'none'):
            for k in range(len(p['pts'])):
                sp = names[k % len(names)]
                if sp not in index: index[sp] = len(variants); variants.append({'name': sp, **render(p)})
                per_pt.append(index[sp])
        if not variants: variants, per_pt = [{'name': p['latin'], **render(p)}], [0] * len(p['pts'])
        for v in variants:
            lid = look_id(v['name'], p['latin'])
            if lid:
                v['look'] = lid
                if 'height' in LOOK_TABLE[lid]: v['h'] = LOOK_TABLE[lid]['height']
            v['label'] = re.sub(r'\s*\(.*\)$', '', v['name']) + (' ' + p['cultivar'] if p['cultivar'] and len(variants) == 1 else '')
            if 'paniculata' in v['name']: v['headLen'], v['headSize'] = 1.45, 0.3
        lo, hi = price_range(p['price']); ym = re.search(r'20\d\d', p['when'] or '')
        plants.append({'id': p['id'], 'zone': p['zone'], 'latin': p['latin'], 'polish': p['polish'], 'cultivar': p['cultivar'],
                       'qty': p['qty'], 'size': p['size'], 'where': p['where'], 'notes': p['notes'], 'when': p['when'], 'price': p['price'],
                       'priceLo': lo, 'priceHi': hi, 'year': int(ym.group(0)) if ym else None, 'sym': p['sym'], 'r': p['r'],
                       'variants': variants, 'ptVariant': per_pt, 'pts': poly(p['pts']),
                       'rows': [poly(r) for r in p['rows']], 'areas': [poly(a) for a in p['areas']]})

    hx = [q[0] for q in HOUSE]; hy = [q[1] for q in HOUSE]
    rect = (min(hx) - OVERHANG, min(hy) - OVERHANG, max(hx) + OVERHANG, max(hy) + OVERHANG)
    roof = {'facets': [[[round(c, 3) for c in v] for v in f] for f in hip_roof(rect, EAVE_H, PITCH)],
            'eave': poly([(rect[0], rect[1]), (rect[2], rect[1]), (rect[2], rect[3]), (rect[0], rect[3])]), 'hEave': EAVE_H}
    t = math.tan(math.radians(PITCH)); pv = []
    for d0, d1 in PV_ROWS:                       # rows parallel to the south eave, 1.65 m panels on a 1.75 m pitch
        n = int((rect[2] - rect[0] - 2 * d1 - 0.6) // 1.75); start = (rect[0] + rect[2]) / 2 - n * 1.75 / 2
        for k in range(n):
            a, b = start + k * 1.75 + 0.05, start + k * 1.75 + 1.70
            pv.append([[round(c, 3) for c in v] for v in [(a, rect[3] - d0, EAVE_H + d0 * t + 0.06), (b, rect[3] - d0, EAVE_H + d0 * t + 0.06),
                                                         (b, rect[3] - d1, EAVE_H + d1 * t + 0.06), (a, rect[3] - d1, EAVE_H + d1 * t + 0.06)]])

    def pipe(label, seg, half, active):
        (ax, ay), (bx, by) = seg                 # the band only means something on the plot itself: clip it
        ins = [i / 400 for i in range(401) if min(xs) <= ax + (bx - ax) * i / 400 <= max(xs) and min(ys) <= ay + (by - ay) * i / 400 <= max(ys)]
        band = [(ax + (bx - ax) * min(ins), ay + (by - ay) * min(ins)), (ax + (bx - ax) * max(ins), ay + (by - ay) * max(ins))] if ins and half > 0 else None
        return {'label': label, 'line': poly(seg), 'zone': half, 'active': active, 'band': poly(band) if band else None}

    W = min(xs)                                  # west fence with the gate (4 m) and wicket (1.1 m) left open
    fences = [[(W, 0), (W, WICKET[1] - 0.55)], [(W, WICKET[1] + 0.55), (W, GATE[1] - 2.0)], [(W, GATE[1] + 2.0), (W, max(ys))],
              [(W, max(ys)), (max(xs), max(ys)), (max(xs), 0), (W, 0)]]

    return {
        'meta': {'generated': datetime.date.today().isoformat(), 'version': VERSION, 'plateau': LEVEL, 'site': GEO, 'axis': 0.0,
                 'ui': {'title': TITLE, 'currency': CURRENCY, 'layers': {'gas': 'Sieci i pasy ochronne'}, 'credit': ''},
                 'counts': {'entries': len(plants), 'positions': sum(len(p['pts']) for p in plants), 'pieces': sum(p['qty'] for p in plants)}},
        'grid': {'x0': X0, 'y0': Y0, 'nx': NX, 'ny': NY, 'step': STEP, 'zbase': ZBASE, 'alt': alt},
        'context': None, 'ortho': None,          # see references/scene-schema.md to add an aerial photo around the plot
        'ground': [{'cls': c, 'poly': poly(pg)} for c, pg in GROUND],
        'plot': poly(PLOT),
        'zones': [{'id': i, 'name': n, 'color': c, 'desc': d, 'polys': [poly(q) for q in pp]} for i, n, c, d, pp in ZONES],
        'buildings': [{'kind': 'house', 'poly': poly(HOUSE), 'h': WALL_H}, {'kind': 'porch', 'poly': poly(PORCH), 'h': 0.12},
                      {'kind': 'terrace', 'poly': poly(TERRACE), 'h': 0.15}],
        'house': {'roofs': [roof], 'pv': pv, 'posts': [],
                  'openings': [{'kind': k, 'label': lb, 'a': P(a), 'b': P(b), 'n': list(n), 'sill': s, 'h': h} for k, lb, a, b, n, s, h in OPENINGS]},
        'paving': [{'kind': k, 'poly': poly(pg)} for k, pg in PAVING],
        'pipes': [pipe(*u) for u in UTILITIES],
        'structures': [{'plant': p['id'], 'poly': poly(a), **STRUCTURES[p['id']]} for p in PLANTS if p['id'] in STRUCTURES for a in p['areas']],
        'slopes': [], 'fences': [{'kind': 'boundary', 'h': 1.5, 'line': poly(f)} for f in fences],
        'lines': [{'kind': 'crest', 'label': 'korona skarpy', 'line': poly(CREST)}],
        'site': [{'kind': k, 'label': lb, 'pt': P(pt), 'w': w, 'd': d, 'h': h, 'angle': round(a, 5), **({'vineLook': look_id(vl)} if vl else {})}
                 for k, lb, pt, w, d, h, a, vl in SITE],
        'markers': [{'kind': 'tree', 'label': lb, 'pt': P(pt), 'name': nm, 'dia': dia, 'h': h, 'note': note, 'look': look_id(nm)}
                    for lb, pt, nm, dia, h, note in EXISTING_TREES]
                 + [{'kind': 'gate', 'label': 'brama 4 m', 'pt': P(GATE)}, {'kind': 'wicket', 'label': 'furtka', 'pt': P(WICKET)}],
        'views': [{'id': i, 'label': lb, 'from': P(a), 'to': P(b), 'step': s} for i, lb, a, b, s in EYE_VIEWS],
        'scatter': [{'look': look_id(lk), 'density': dn, 'share': sh, 'polys': [poly(q) for q in pp]} for lk, dn, sh, pp in SCATTER],
        'plants': plants,
        'looks': LOOK_TABLE,
        'irrigation': irrigation(),
    }

if __name__ == '__main__':
    scene = build()
    missing = [f"{p['id']} {v['name']}" for p in scene['plants'] for v in p['variants']
               if 'look' not in v and v['kind'] not in ('arch', 'bench', 'volume', 'skip') and (p['pts'] or p['rows'] or p['areas'])]
    if missing: print('no seasonal look for:', '; '.join(missing), '— add them to LOOKS')
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(scene, f, ensure_ascii=False, separators=(',', ':'))
    g = scene['grid']
    print(f"{OUT}  {os.path.getsize(OUT) / 1024:.0f} kB — grid {g['nx']}×{g['ny']} @ {g['step']} m, "
          f"{len(scene['plants'])} entries, {scene['meta']['counts']['pieces']} pieces, {len(scene['looks'])} looks")
