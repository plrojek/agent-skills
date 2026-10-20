/* Plants for the garden viewer: model-style foliage (faceted lobe clusters per habit), bare
   branches in winter, and a season model driven by the scene's `looks` table — leaf
   colour, spring flush, autumn colour, flowers as a crown colour ("cover") or as dots / hydrangea
   heads / grass plumes, fruit. Positions and sizes come from the exporter; nothing is invented
   here except where a scattered bed places its individual plants. */

import * as THREE from './vendor/three.module.min.js';
import { S, groundAt, sceneY, rng, hashStr, pointInPoly, polyArea, col } from './site.js';

/* ---------------------------------------------------------------- geometry */
function merge(list) {
  let n = 0;
  list.forEach((g) => { n += g.attributes.position.count; });
  const pos = new Float32Array(n * 3);
  let o = 0;
  list.forEach((g) => { pos.set(g.attributes.position.array, o); o += g.attributes.position.array.length; g.dispose(); });
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  return geo;
}
/** fit into x,z in [-0.5, 0.5], y in [0, 1] — instances are then scaled by (diameter, height, diameter) */
function unit(geo) {
  geo.computeBoundingBox();
  const b = geo.boundingBox, sx = b.max.x - b.min.x, sy = b.max.y - b.min.y, sz = b.max.z - b.min.z;
  geo.translate(-(b.min.x + b.max.x) / 2, -b.min.y, -(b.min.z + b.max.z) / 2);
  geo.scale(1 / sx, 1 / sy, 1 / sz);
  geo.computeVertexNormals();
  geo.computeBoundingSphere();
  return geo;
}
const ring = (n, y, R, r, ph = 0) => Array.from({ length: n }, (_, k) => {
  const a = ph + (k / n) * Math.PI * 2; return [Math.cos(a) * R, y, Math.sin(a) * R, r];
});
const LOBES = {
  round:    () => [[0, 0.5, 0, 0.48], ...ring(6, 0.42, 0.34, 0.3), ...ring(3, 0.76, 0.16, 0.3, 0.5)],
  oval:     () => [[0, 0.3, 0, 0.34], [0, 0.58, 0, 0.38], [0, 0.86, 0, 0.3], ...ring(5, 0.5, 0.22, 0.27), ...ring(4, 0.76, 0.14, 0.22, 0.4)],
  spread:   () => [[0, 0.5, 0, 0.42], ...ring(7, 0.4, 0.44, 0.3), ...ring(4, 0.62, 0.22, 0.3, 0.4)],
  vase:     () => [...ring(3, 0.28, 0.12, 0.2), ...ring(6, 0.62, 0.36, 0.3, 0.3), [0, 0.74, 0, 0.34]],
  column:   (r) => Array.from({ length: 7 }, (_, k) => [(r() - 0.5) * 0.08, 0.1 + k * 0.13, (r() - 0.5) * 0.08, 0.27]),
  pyramid:  () => [...ring(6, 0.25, 0.34, 0.3), ...ring(5, 0.5, 0.24, 0.27, 0.5), ...ring(3, 0.72, 0.12, 0.24), [0, 0.9, 0, 0.18]],
  airy:     (r) => Array.from({ length: 15 }, () => {
    const a = r() * 6.283, y = 0.15 + r() * 0.75, R = Math.sin(Math.PI * y) * (0.18 + r() * 0.2);
    return [Math.cos(a) * R, y, Math.sin(a) * R, 0.15 + r() * 0.08];
  }),
  umbrella: () => [[0, 0.55, 0, 0.36], ...ring(8, 0.45, 0.42, 0.24), ...ring(4, 0.62, 0.2, 0.24, 0.3)],
  mound:    () => [[0, 0.42, 0, 0.45], ...ring(5, 0.3, 0.32, 0.3), ...ring(2, 0.62, 0.12, 0.28, 0.7)],
  low:      () => [[0, 0.3, 0, 0.4], ...ring(6, 0.25, 0.36, 0.28)],
};
function lobeCrown(habit, seed) {
  const r = rng(seed);
  const parts = (LOBES[habit] || LOBES.round)(r).map(([x, y, z, rad]) => {
    const g = new THREE.IcosahedronGeometry(1, 1);
    const p = g.attributes.position;
    for (let i = 0; i < p.count; i++) {       // same input -> same bump, so shared corners never crack
      const vx = p.getX(i), vy = p.getY(i), vz = p.getZ(i);
      const k = 1 + 0.13 * Math.sin(vx * 5.3 + vy * 3.7 + seed) * Math.cos(vz * 4.1 - vy * 2.3 + seed * 0.7);
      p.setXYZ(i, vx * k, vy * k, vz * k);
    }
    const j = 0.86 + r() * 0.28;
    g.scale(rad * j, rad * j, rad * j);
    g.translate(x + (r() - 0.5) * 0.06, y + (r() - 0.5) * 0.06, z + (r() - 0.5) * 0.06);
    return g;
  });
  return unit(merge(parts));
}
function coneTiers(n, shrink, seed) {
  const r = rng(seed), parts = [];
  for (let k = 0; k < n; k++) {
    const g = new THREE.ConeGeometry(0.5 * (1 - k * shrink), 0.46, 9, 1, false, r() * 6).toNonIndexed();
    g.translate(0, 0.23 + k * (0.8 / n), 0);
    parts.push(g);
  }
  return unit(merge(parts));
}
function limb(a, b, r0, r1) {
  const d = new THREE.Vector3().subVectors(b, a), L = d.length();
  const g = new THREE.CylinderGeometry(r1, r0, L, 5, 1, true).toNonIndexed();
  g.translate(0, L / 2, 0);
  g.applyQuaternion(new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 1, 0), d.normalize()));
  g.translate(a.x, a.y, a.z);
  return g;
}
/** winter branches in crown space (y 0..1 = crown base..top); `w` = spread */
function branches(w, seed) {
  const r = rng(seed), parts = [], V = (x, y, z) => new THREE.Vector3(x, y, z);
  parts.push(limb(V(0, -0.15, 0), V(0, 0.95, 0), 0.035, 0.008));
  for (let k = 0; k < 6; k++) {
    const a = (k / 6) * 6.283 + r() * 0.5, y0 = r() * 0.25;
    const tip = V(Math.cos(a) * 0.42 * w, 0.62 + r() * 0.25, Math.sin(a) * 0.42 * w);
    parts.push(limb(V(0, y0, 0), tip, 0.022, 0.006));
    const mid = V(tip.x * 0.55, y0 + (tip.y - y0) * 0.55, tip.z * 0.55);
    parts.push(limb(mid, V(Math.cos(a + 0.5) * 0.47 * w, 0.9 + r() * 0.1, Math.sin(a + 0.5) * 0.47 * w), 0.012, 0.004));
    parts.push(limb(mid, V(Math.cos(a - 0.45) * 0.5 * w, 0.55 + r() * 0.15, Math.sin(a - 0.45) * 0.5 * w), 0.01, 0.004));
  }
  const g = merge(parts);
  g.computeVertexNormals();
  return g;                           // NOT unit-fitted: it must line up with the crown it replaces
}
function tuftGeo(seed) {
  const r = rng(seed), pos = [];
  for (let k = 0; k < 30; k++) {
    const a = r() * 6.283, lean = 0.18 + r() * 0.3, h = 0.65 + r() * 0.35, w = 0.03;
    const bx = Math.cos(a) * 0.06, bz = Math.sin(a) * 0.06;
    const tx = Math.cos(a) * lean, tz = Math.sin(a) * lean;
    const px = -Math.sin(a) * w, pz = Math.cos(a) * w;
    pos.push(bx - px, 0, bz - pz, bx + px, 0, bz + pz, tx, h, tz);
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  return unit(g);
}
function hedgeGeo() {
  const s = new THREE.Shape(), r = 0.24;               // profile: 1 wide, 1 high, rounded top corners
  s.moveTo(-0.5, 0); s.lineTo(0.5, 0); s.lineTo(0.5, 1 - r);
  s.quadraticCurveTo(0.5, 1, 0.5 - r, 1); s.lineTo(-0.5 + r, 1);
  s.quadraticCurveTo(-0.5, 1, -0.5, 1 - r); s.closePath();
  const g = new THREE.ExtrudeGeometry(s, { depth: 1, bevelEnabled: false, curveSegments: 3 });
  g.translate(0, 0, -0.5);
  g.rotateY(Math.PI / 2);                              // length along x, like the old box
  return unit(g.index ? g.toNonIndexed() : g);
}

/* ---------------------------------------------------------------- materials */
const M = {
  leaf:   new THREE.MeshStandardMaterial({ roughness: 0.92, metalness: 0, flatShading: true }),
  bark:   new THREE.MeshStandardMaterial({ roughness: 0.95, metalness: 0, flatShading: true }),
  blade:  new THREE.MeshStandardMaterial({ roughness: 0.9, metalness: 0, flatShading: true, side: THREE.DoubleSide }),
  twig:   new THREE.MeshStandardMaterial({ roughness: 1, metalness: 0, flatShading: true, transparent: true, opacity: 0.42, depthWrite: false }),
  dot:    new THREE.MeshStandardMaterial({ roughness: 0.75, metalness: 0, flatShading: true }),
};

/* ---------------------------------------------------------------- season model */
const lighten = (hex, k) => '#' + col(hex, k).getHexString();
function parseFl(v, defMode) {
  if (!v) return null;
  if (typeof v === 'string') return { cols: [v], mode: defMode };
  const a = v.slice();
  const mode = a[a.length - 1].startsWith('#') ? defMode : a.pop();
  return { cols: a, mode };
}
const BARE_DEFAULT = { tree: 'branches', conifer: 'branches', columnar: 'branches', shrub: 'twigs', row: 'twigs',
                       climber: 'twigs', hedge: 'twigs', tuft: 'straw', ground: 'hide', clump: 'hide' };
/** what a plant looks like in `month` (1..12) */
export function seasonOf(look, month, kind) {
  const L = look || {};
  const ever = L.winter === 'keep';
  const lv = L.leaves || [4, 10];
  const inLeaf = ever || (month >= lv[0] && month <= lv[1]);
  const fl = parseFl(L.flowers && L.flowers[month], kind === 'tuft' ? 'plume' : 'dots');
  const out = { crown: null, bare: null, fresh: false, flowers: null, fruit: (L.fruit && L.fruit[month]) || null };
  const leaf = L.leaf || '#6b8a45';
  if (inLeaf) {
    if (L.autumn && L.autumn[month]) out.crown = L.autumn[month];
    else if (!ever && month === lv[0]) { out.crown = L.spring || lighten(leaf, 0.08); out.fresh = true; }
    else if (ever && (month === 12 || month <= 2)) out.crown = lighten(leaf, -0.04);
    else out.crown = leaf;
  } else if (L.winter === 'marcescent') out.crown = L.wcolour || '#a8763f';
  else if (L.winter === 'straw') { out.crown = L.wcolour || '#c9b58a'; out.bare = 'straw'; }
  else out.bare = L.winter === 'hide' ? 'hide' : (BARE_DEFAULT[kind] || 'hide');
  if (fl && fl.mode === 'cover') { out.crown = fl.cols[0]; out.bare = null; out.fresh = false; }
  else out.flowers = fl;
  return out;
}

/* ---------------------------------------------------------------- instanced buckets */
class Bucket {
  constructor(geo, mat, cast = true) { this.geo = geo; this.mat = mat; this.cast = cast; this.n = 0; this.pick = []; }
  reserve(k = 1) { const i = this.n; this.n += k; return i; }
  build(group) {
    const m = new THREE.InstancedMesh(this.geo, this.mat, Math.max(1, this.n));
    m.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
    m.setColorAt(0, new THREE.Color(1, 1, 1));
    m.castShadow = this.cast; m.receiveShadow = true;
    m.frustumCulled = false;          // instances move with the sliders; a cached bounding sphere would cull them wrongly
    m.count = this.n;
    m.userData.pick = this.pick;
    this.mesh = m;
    group.add(m);
  }
}
const _m = new THREE.Matrix4(), _q = new THREE.Quaternion(), _p = new THREE.Vector3(), _s = new THREE.Vector3(), _c = new THREE.Color();
const Y = new THREE.Vector3(0, 1, 0);
const FADED = new THREE.Color('#d6d1c5');
let DIM = 0;                           // 0 = full colour; set per body while a highlight is on
function put(B, i, x, y, z, sx, sy, sz, ry, hex) {
  _p.set(x, y, z); _s.set(sx, sy, sz); _q.setFromAxisAngle(Y, ry || 0);
  _m.compose(_p, _q, _s); B.mesh.setMatrixAt(i, _m);
  if (hex) { _c.set(hex); if (DIM) _c.lerp(FADED, DIM); B.mesh.setColorAt(i, _c); }
}
function hide(B, i) { _m.makeScale(0, 0, 0); B.mesh.setMatrixAt(i, _m); }

/* ---------------------------------------------------------------- the plant system */
const TRUNK_FRAC = { round: 0.34, oval: 0.3, spread: 0.28, vase: 0.3, column: 0.1, pyramid: 0.18, airy: 0.32,
                     umbrella: 0.28, fir: 0.06, spire: 0.05 };
const WIDE = new Set(['round', 'oval', 'spread', 'vase', 'umbrella', 'airy', 'pyramid']);

export class Plants {
  constructor(d) {
    this.d = d;
    this.looks = d.looks || {};
    this.group = new THREE.Group(); this.group.name = 'plants';
    this.bodies = [];
    this.B = {};
    this.singles = [];
    this.pickables = [];
    this.hl = null;                    // predicate over bodies: the highlighted set, or null
    this.vis = null;                   // predicate over bodies: what is planted yet, or null = everything
    const G = (k, make, mat, cast) => (this.B[k] = this.B[k] || new Bucket(make(), mat, cast));
    this.bucket = G;
    this.collect();
    Object.values(this.B).forEach((b) => b.build(this.group));
    Object.values(this.B).forEach((b) => { if (b.pick.length) this.pickables.push(b.mesh); });   // dots and plumes never block a pick
    this.buildSingles();
  }

  crownKey(habit, seed) {
    const v = seed % 2, k = 'crown:' + habit + ':' + v;
    if (habit === 'fir') return this.bucket(k, () => coneTiers(4, 0.2, 11 + v), M.leaf);
    if (habit === 'spire') return this.bucket(k, () => coneTiers(6, 0.15, 21 + v), M.leaf);
    return this.bucket(k, () => lobeCrown(habit, 101 + v * 37 + habit.length * 7), M.leaf);
  }

  /** a body = one drawn plant; slots are filled lazily as buckets are known */
  add(p, pi, ptIdx, v, x, y, extra) {
    const look = this.looks[v.look] || null;
    const seed = hashStr(p.id + ':' + ptIdx + ':' + x.toFixed(2) + ':' + y.toFixed(2));
    const r = rng(seed);
    const kind = v.kind === 'columnar' ? 'tree' : v.kind;
    const habit = (look && look.habit) || (v.kind === 'conifer' ? 'fir' : v.kind === 'columnar' ? 'column' : kind === 'tree' ? 'round' : 'mound');
    const b = { plantIdx: pi, ptIdx, p, v, look, kind, habit, x, y, ground: groundAt(x, y), dia: v.dia, h: v.h,
                ry: r() * 6.283, seed, fixed: false, ...extra };
    if (kind === 'tree' || kind === 'conifer') {
      b.crownB = this.crownKey(habit, seed); b.crownI = b.crownB.reserve(); b.crownB.pick[b.crownI] = b;
      b.trunkB = this.bucket('trunk', () => unit(new THREE.CylinderGeometry(0.34, 0.5, 1, 7).toNonIndexed()), M.bark);
      b.trunkI = b.trunkB.reserve(); b.trunkB.pick[b.trunkI] = b;
      if (kind === 'tree') {
        const w = WIDE.has(habit) ? 'w' : 'n';
        b.branchB = this.bucket('branches:' + w, () => branches(w === 'w' ? 1 : 0.35, 5), M.bark);
        b.branchI = b.branchB.reserve(); b.branchB.pick[b.branchI] = b;
      }
      this.dots(b, Math.max(20, Math.min(110, Math.round(v.dia * v.dia * 2.4))), 0.2);
    } else if (kind === 'tuft') {
      b.crownB = this.bucket('tuft:' + (seed % 2), () => tuftGeo(300 + (seed % 2)), M.blade);
      b.crownI = b.crownB.reserve(); b.crownB.pick[b.crownI] = b;
      b.plumeB = this.bucket('plume', () => new THREE.IcosahedronGeometry(0.5, 1), M.dot, false);
      b.plumeI = b.plumeB.reserve(9);
      b.plumeU = Array.from({ length: 9 }, () => [r() * 6.283, 0.25 + r() * 0.2, r()]);
    } else if (kind === 'hedge') {
      b.crownB = this.bucket('hedge', hedgeGeo, M.leaf);
      b.crownI = b.crownB.reserve(); b.crownB.pick[b.crownI] = b;
    } else {
      // shrubs, rows, ground mounds, peony clumps, climbers
      const hb = kind === 'climber' ? 'column' : kind === 'ground' ? 'low' : (habit === 'low' ? 'low' : 'mound');
      b.habit = hb;
      b.crownB = this.crownKey(hb, seed); b.crownI = b.crownB.reserve(); b.crownB.pick[b.crownI] = b;
      if (kind !== 'ground') {
        b.twigB = this.bucket('twig:' + hb, () => lobeCrown(hb, 777), M.twig, false);
        b.twigI = b.twigB.reserve(); b.twigB.pick[b.twigI] = b;
      }
      const heads = look && look.flowers && Object.values(look.flowers).some((f) => Array.isArray(f) && f.includes('heads'));
      if (heads || kind === 'clump') {
        const n = kind === 'clump' ? 6 : Math.max(4, Math.min(24, Math.round(v.dia * v.dia * 7)));
        this.dots(b, n, kind === 'clump' ? 0.17 : (v.headSize || 0.26), 'head', true);
      } else {
        const n = kind === 'ground' ? 2 : kind === 'climber' ? 16 : kind === 'row' ? 4 : Math.max(6, Math.min(40, Math.round(v.dia * v.dia * 10)));
        this.dots(b, n, kind === 'ground' ? 0.08 : kind === 'climber' ? 0.12 : 0.12);
      }
    }
    this.bodies.push(b);
    return b;
  }

  /** reserve flower/fruit dots on the crown envelope (unit space), upper part only */
  dots(b, n, size, kind = 'dot', top = false) {
    const B = kind === 'head' ? this.bucket('head', () => new THREE.IcosahedronGeometry(0.5, 1), M.dot, false)
                              : this.bucket('dot', () => new THREE.IcosahedronGeometry(0.5, 0), M.dot, false);
    const r = rng(b.seed ^ 0x9e3779b9);
    b.dotB = B; b.dotI = B.reserve(n); b.dotN = n; b.dotSize = size;
    b.dotU = new Float32Array(n * 3);
    for (let k = 0; k < n; k++) {
      let dx, dy, dz;
      do { dx = r() * 2 - 1; dy = r() * 2 - 1; dz = r() * 2 - 1; } while (dx * dx + dy * dy + dz * dz > 1 || dy < (top ? 0.15 : -0.3));
      const L = Math.hypot(dx, dy, dz) || 1;
      b.dotU[k * 3] = (dx / L) * 0.52; b.dotU[k * 3 + 1] = 0.5 + (dy / L) * 0.52; b.dotU[k * 3 + 2] = (dz / L) * 0.52;
    }
  }

  collect() {
    const d = this.d;
    d.plants.forEach((p, pi) => {
      if (p.sym === 'drift') return;                               // painted on the lawn by ground.js
      const vOf = (k) => p.variants[p.ptVariant[k]] || p.variants[0];
      p.pts.forEach((pt, k) => {
        const v = vOf(k);
        if (v.kind === 'skip' || v.kind === 'volume') return;
        if (v.kind === 'arch' || v.kind === 'bench') { this.singles.push({ v, pi, pt }); return; }
        if (v.kind === 'ground' && v.dia > 1.2) {                  // a cover patch given as one point + diameter
          const r = rng(hashStr(p.id + k)), R = v.dia / 2, want = Math.round(Math.PI * R * R * 1.1);
          for (let n = 0, guard = 0; n < want && guard < want * 20; guard++) {
            const x = pt[0] + (r() * 2 - 1) * R, y = pt[1] + (r() * 2 - 1) * R;
            if (Math.hypot(x - pt[0], y - pt[1]) > R) continue;
            this.add(p, pi, k, { ...v, dia: 0.45 * (0.8 + r() * 0.5), h: 0.35 * (0.8 + r() * 0.4) }, x, y); n++;
          }
          return;
        }
        this.add(p, pi, k, v, pt[0], pt[1]);
      });
      const v0 = p.variants[0];
      if (p.rows.length && v0.kind !== 'skip') {
        p.rows.forEach((row) => {
          for (let s = 0; s < row.length - 1; s++) {
            const [x0, y0] = row[s], [x1, y1] = row[s + 1];
            const len = Math.hypot(x1 - x0, y1 - y0);
            const step = v0.kind === 'hedge' ? 1.2 : v0.kind === 'row' ? 0.45 : 0.5;
            const n = Math.max(1, Math.round(len / step));
            const ang = Math.atan2(-(y1 - y0), x1 - x0);
            for (let t = 0; t < n; t++) {
              const f = (t + 0.5) / n;
              const vv = v0.kind === 'hedge' ? { ...v0, len: len / n + 0.05 } : v0.kind === 'ground' ? { ...v0, dia: 0.45, h: 0.45 } : v0;
              const b = this.add(p, pi, -1, vv, x0 + (x1 - x0) * f, y0 + (y1 - y0) * f);
              if (v0.kind === 'hedge') b.ry = ang;
            }
          }
        });
      }
      if (p.areas.length && v0.kind !== 'volume' && v0.kind !== 'skip') {
        p.areas.forEach((poly, ai) => {
          let minx = Infinity, maxx = -Infinity, miny = Infinity, maxy = -Infinity;
          poly.forEach(([x, y]) => { minx = Math.min(minx, x); maxx = Math.max(maxx, x); miny = Math.min(miny, y); maxy = Math.max(maxy, y); });
          const want = Math.min(260, Math.max(6, Math.round(polyArea(poly) * 1.3)));
          const r = rng(1000 + pi * 31 + ai);
          for (let placed = 0, guard = 0; placed < want && guard < want * 40; guard++) {
            const x = minx + r() * (maxx - minx), y = miny + r() * (maxy - miny);
            if (!pointInPoly(x, y, poly)) continue;
            this.add(p, pi, -1, { ...v0, dia: v0.dia * (0.8 + r() * 0.6), h: v0.h * (0.75 + r() * 0.5) }, x, y);
            placed++;
          }
        });
      }
    });
    // trees that already stand on the site: full grown, the growth slider leaves them alone
    (d.markers || []).filter((m) => m.kind === 'tree').forEach((m, k) => {
      const b = this.add({ id: 'existing' + k, sym: 'tree' }, -1, -1,
        { name: m.name || m.label, kind: m.conifer ? 'conifer' : 'tree', dia: m.dia || 5, h: m.h || 10, look: m.look }, m.pt[0], m.pt[1]);
      b.fixed = true; b.site = { label: m.label, dims: m.note || '' };
    });
  }

  /** rose arches and the bench — posts-and-beams read far better than ellipsoids. Both carry the
      angle the scene gives them (variant.angle): arches span ACROSS their path, one leg either side of its axis */
  buildSingles() {
    const wood = new THREE.MeshStandardMaterial({ color: 0x8a6b45, roughness: 0.85 });
    const arches = new Map();
    this.singles.forEach(({ v, pi, pt }) => {
      const grp = new THREE.Group();
      const box = (w, h, dd, x, y, z) => {
        const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, dd), wood);
        m.position.set(x, y, z); m.castShadow = true; m.receiveShadow = true; grp.add(m); return m;
      };
      const w = v.dia, h = v.h;
      if (v.kind === 'arch') {
        for (const sx of [-w / 2, w / 2]) box(0.1, h, 0.1, sx, h / 2, 0);
        box(w + 0.1, 0.1, 0.09, 0, h - 0.05, 0);
        for (const f of [0.52, 0.82]) box(w, 0.06, 0.05, 0, h * f, 0);
      } else {
        box(w, 0.07, 0.45, 0, h * 0.52, 0);
        box(w, h * 0.4, 0.06, 0, h * 0.75, -0.2);
        for (const sx of [-w / 2 + 0.1, w / 2 - 0.1]) box(0.08, h * 0.52, 0.4, sx, h * 0.26, 0);
      }
      grp.position.set(pt[0] - S.CX, sceneY(groundAt(pt[0], pt[1])), pt[1] - S.CZ);
      grp.rotation.y = -(v.angle || 0);
      grp.traverse((c) => { if (c.isMesh) { c.userData.plantIdx = pi; this.pickables.push(c); } });
      this.group.add(grp);
      if (v.kind === 'arch') {
        if (!arches.has(pi)) arches.set(pi, []);
        arches.get(pi).push({ grp, w, h });
      }
    });
    // the plan's corridor: arches tied together at the top with slats into one tunnel
    arches.forEach((list, pi) => {
      if (list.length < 2) return;
      list.forEach((a) => a.grp.updateMatrixWorld());
      const along = new THREE.Vector3(0, 0, 1).applyQuaternion(list[0].grp.quaternion);
      list.sort((a, b) => a.grp.position.dot(along) - b.grp.position.dot(along));
      for (let k = 0; k < list.length - 1; k++) {
        const a = list[k], b = list[k + 1];
        for (const f of [-0.45, -0.22, 0, 0.22, 0.45]) {
          const p0 = a.grp.localToWorld(new THREE.Vector3(f * a.w, a.h + 0.04, 0));
          const p1 = b.grp.localToWorld(new THREE.Vector3(f * b.w, b.h + 0.04, 0));
          const L = p0.distanceTo(p1);
          const slat = new THREE.Mesh(new THREE.BoxGeometry(0.05, 0.04, L), wood);
          slat.position.copy(p0).add(p1).multiplyScalar(0.5);
          slat.quaternion.setFromUnitVectors(new THREE.Vector3(0, 0, 1), p1.clone().sub(p0).normalize());
          slat.castShadow = true; slat.userData.plantIdx = pi;
          this.pickables.push(slat);
          this.group.add(slat);
        }
      }
    });
  }

  /** lay everything out for growth fraction `f` (0..1 of the mature size) and `month` (1..12) */
  layout(f, month) {
    const st = new Map();
    const stateFor = (b) => {
      const k = (b.v.look || '') + ':' + b.kind;
      if (!st.has(k)) st.set(k, seasonOf(b.look, month, b.kind));
      return st.get(k);
    };
    for (const b of this.bodies) {
      if (this.vis && !b.fixed && !this.vis(b)) { this.hideBody(b); continue; }
      DIM = this.hl && !this.hl(b) ? 0.84 : 0;
      const s = stateFor(b);
      const x = b.x - S.CX, z = b.y - S.CZ, y0 = sceneY(b.ground);
      const gf = b.fixed ? 1 : b.kind === 'hedge' ? 0.55 + 0.45 * f : b.kind === 'ground' ? 0.6 + 0.4 * f
               : (b.kind === 'tuft' || b.kind === 'clump' || b.kind === 'row') ? Math.min(1, 0.45 + f) : f;
      const D = Math.max(0.15, b.dia * gf), H = Math.max(0.15, b.h * gf);
      let cy = y0, ch = H, cd = D, fresh = s.fresh ? 0.88 : 1;

      if (b.kind === 'tree' || b.kind === 'conifer') {
        const tf = TRUNK_FRAC[b.habit] ?? 0.3;
        const base = H * tf * 0.9;
        cy = y0 + base; ch = H - base;
        const tr = Math.max(0.05, Math.min(0.35, D * 0.04));
        const bark = (b.look && b.look.bark && b.habit === 'airy') ? b.look.bark : '#6b543a';
        put(b.trunkB, b.trunkI, x, y0, z, tr * 2, H * tf + ch * 0.35, tr * 2, b.ry, bark);
        if (s.crown) put(b.crownB, b.crownI, x, cy, z, cd * fresh, ch * fresh, cd * fresh, b.ry, s.crown);
        else hide(b.crownB, b.crownI);
        if (b.branchB) {
          if (!s.crown && s.bare === 'branches') {
            const twig = (b.look && b.look.bark) || '#7d6a58';
            put(b.branchB, b.branchI, x, cy, z, cd * 0.95, ch * 0.95, cd * 0.95, b.ry, twig);
          } else hide(b.branchB, b.branchI);
        }
      } else if (b.kind === 'tuft') {
        const fh = (b.look && b.look.fh) || 0.6;
        const hide_ = s.bare === 'hide';
        const straw = s.bare === 'straw';
        const fch = straw ? H * fh * 0.85 : H * fh;
        if (!hide_ && s.crown) put(b.crownB, b.crownI, x, y0, z, D, fch, D, b.ry, s.crown); else hide(b.crownB, b.crownI);
        const pl = s.flowers && s.flowers.mode === 'plume' ? s.flowers.cols[0] : straw && b.look && b.look.winterPlume ? s.crown : null;
        for (let k = 0; k < 9; k++) {
          if (!pl || hide_) { hide(b.plumeB, b.plumeI + k); continue; }
          const [a, rr, t] = b.plumeU[k];
          const ph = H * (1 - fh) * 0.6;
          put(b.plumeB, b.plumeI + k, x + Math.cos(a) * rr * D * 0.7, y0 + H * fh + ph * (0.3 + t * 0.4), z + Math.sin(a) * rr * D * 0.7,
              Math.max(0.05, D * 0.09), Math.max(0.1, ph), Math.max(0.05, D * 0.09), 0, pl);
        }
        continue;
      } else if (b.kind === 'hedge') {
        const w = Math.max(0.5, b.dia + 0.02) * (0.7 + 0.3 * gf);
        if (s.crown) put(b.crownB, b.crownI, x, y0, z, b.v.len || 1.2, H, w, b.ry, s.crown);
        else put(b.crownB, b.crownI, x, y0, z, b.v.len || 1.2, H, w, b.ry, '#8b7b68');
        continue;
      } else {
        if (s.crown && s.bare !== 'hide') {
          const sh = s.bare === 'straw' ? 0.7 : 1;
          put(b.crownB, b.crownI, x, y0, z, D * fresh, H * sh * fresh, D * fresh, b.ry, s.crown);
          if (b.twigB) hide(b.twigB, b.twigI);
        } else {
          hide(b.crownB, b.crownI);
          if (b.twigB) {
            if (s.bare === 'twigs') {
              const twig = (b.look && b.look.bark) || '#8b7b68';
              put(b.twigB, b.twigI, x, y0, z, D * 0.9, H * 0.9, D * 0.9, b.ry, twig);
            } else hide(b.twigB, b.twigI);
          }
        }
      }

      // flowers / fruit on the crown envelope
      if (b.dotB) {
        const fl = s.flowers && (s.flowers.mode === 'dots' || s.flowers.mode === 'heads' || s.flowers.mode === 'mix') ? s.flowers : null;
        const showCrown = !!s.crown || s.bare === 'branches';
        const fruit = !fl && s.fruit ? s.fruit : null;
        const cols = fl ? fl.cols : fruit ? [fruit] : null;
        const n = b.dotN;
        const shown = cols && showCrown ? (fruit ? Math.ceil(n * 0.6) : n) : 0;
        const size = b.dotSize * (fruit ? 0.45 : 1) * Math.max(0.55, Math.min(1, gf + 0.3));
        const elong = b.dotB === this.B.head ? (b.v.headLen || 1) : 1;
        for (let k = 0; k < n; k++) {
          if (k >= shown) { hide(b.dotB, b.dotI + k); continue; }
          const ux = b.dotU[k * 3] * cd, uy = b.dotU[k * 3 + 1] * ch, uz = b.dotU[k * 3 + 2] * cd;
          const c = Math.cos(b.ry), sn = Math.sin(b.ry);
          put(b.dotB, b.dotI + k, x + ux * c + uz * sn, cy + uy, z - ux * sn + uz * c, size, size * elong, size, 0, cols[(k + b.seed) % cols.length]);
        }
      }
    }
    DIM = 0;
    Object.values(this.B).forEach((B) => {
      B.mesh.instanceMatrix.needsUpdate = true;
      if (B.mesh.instanceColor) B.mesh.instanceColor.needsUpdate = true;
      B.mesh.boundingSphere = null; B.mesh.boundingBox = null;    // raycasting recomputes from the new matrices
    });
  }

  /** take one plant off the stage altogether (not planted yet) */
  hideBody(b) {
    for (const [B, i, n] of [[b.crownB, b.crownI, 1], [b.trunkB, b.trunkI, 1], [b.branchB, b.branchI, 1], [b.twigB, b.twigI, 1],
                             [b.plumeB, b.plumeI, 9], [b.dotB, b.dotI, b.dotN]])
      if (B) for (let k = 0; k < n; k++) hide(B, i + k);
  }
  /** show only the bodies `fn` accepts (planting stages); null shows everything. Call layout() afterwards. */
  setVisible(fn) { this.vis = fn || null; }
  /** crowns that cast a shadow at growth `f` in `month`: site x, y, horizontal radius a, vertical semi-axis b,
      centre height hc — leafless trees and anything under 0,5 m cast none */
  shadowBodies(f, month) {
    const out = [];
    for (const b of this.bodies) {
      if (this.vis && !b.fixed && !this.vis(b)) continue;
      if (b.kind === 'ground' || b.kind === 'clump') continue;
      const s = seasonOf(b.look, month, b.kind);
      if (!s.crown || s.bare === 'hide') continue;
      const gf = b.fixed ? 1 : b.kind === 'hedge' ? 0.55 + 0.45 * f : (b.kind === 'tuft' || b.kind === 'row') ? Math.min(1, 0.45 + f) : f;
      const D = Math.max(0.15, b.dia * gf), H = Math.max(0.15, b.h * gf);
      if (H < 0.5) continue;
      if (b.kind === 'tree' || b.kind === 'conifer') {
        const base = H * (TRUNK_FRAC[b.habit] ?? 0.3) * 0.9, ch = H - base;
        out.push({ x: b.x, y: b.y, a: D * 0.44, b: ch / 2, hc: base + ch / 2 });
      } else if (b.kind === 'hedge') out.push({ x: b.x, y: b.y, a: Math.max(0.45, (b.v.len || 1.2) / 2), b: H / 2, hc: H / 2 });
      else out.push({ x: b.x, y: b.y, a: D * 0.45, b: H / 2, hc: H / 2 });
    }
    return out;
  }

  /** highlight the bodies `fn` accepts (everything else fades); null clears. Call layout() afterwards. */
  setHighlight(fn) { this.hl = fn || null; }
  /** scene-space points of the bodies `fn` accepts, for framing them */
  pointsOf(fn) {
    return this.bodies.filter(fn).map((b) => new THREE.Vector3(b.x - S.CX, sceneY(b.ground) + Math.min(3, b.h * 0.5), b.y - S.CZ));
  }

  /** what flowers, fruits and colours in `month`, for the panel list */
  calendar(month) {
    const out = { flowers: new Map(), fruit: new Map(), autumn: new Map() };
    const add = (map, key, name, colour, p) => {
      if (!map.has(key)) map.set(key, { key, name, colour, ids: new Set(), plantIdx: this.d.plants.indexOf(p) });
      map.get(key).ids.add(p.id);
    };
    this.d.plants.forEach((p) => {
      p.variants.forEach((v) => {
        const L = this.looks[v.look]; if (!L) return;
        const name = v.label || v.name;
        const f = L.flowers && L.flowers[month];
        if (f) {
          const pf = parseFl(f, 'dots');
          add(out.flowers, v.look, name, pf.cols[0], p);
        }
        if (L.fruit && L.fruit[month]) add(out.fruit, v.look, name, L.fruit[month], p);
        if (L.autumn && L.autumn[month]) add(out.autumn, v.look, name, L.autumn[month], p);
      });
    });
    return out;
  }
}
