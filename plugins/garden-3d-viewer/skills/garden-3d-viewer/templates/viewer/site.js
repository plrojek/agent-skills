/* Shared site frame for the garden viewer.
   Site frame -> scene frame: x east stays x, y south becomes z, altitude becomes y.
   The reference level (meta.plateau, metres a.s.l.) is scene y = 0, and the plot centroid is the origin. */

import * as THREE from './vendor/three.module.min.js';

export const S = {
  CX: 0, CZ: 0, BASE: 0,
  G: null,            // fine terrain grid (0.5 m) around the plot
  C: null,            // coarse context grid (2 m) under the orthophoto, may be null
  plotRadius: 45,
  mobile: false,
  data: null,
};

export function setupSite(d) {
  S.data = d;
  S.G = d.grid; S.C = d.context || null; S.BASE = d.meta.plateau;
  S.CX = d.plot.reduce((a, p) => a + p[0], 0) / d.plot.length;
  S.CZ = d.plot.reduce((a, p) => a + p[1], 0) / d.plot.length;
  S.plotRadius = Math.max(...d.plot.map(([x, y]) => Math.hypot(x - S.CX, y - S.CZ)));
}

function bilinear(g, x, y) {
  const fi = (x - g.x0) / g.step, fj = (y - g.y0) / g.step;
  const i = Math.max(0, Math.min(g.nx - 2, Math.floor(fi)));
  const j = Math.max(0, Math.min(g.ny - 2, Math.floor(fj)));
  const tx = Math.max(0, Math.min(1, fi - i)), ty = Math.max(0, Math.min(1, fj - j));
  const a = g.alt, w = g.nx;
  const v00 = a[j * w + i], v10 = a[j * w + i + 1], v01 = a[(j + 1) * w + i], v11 = a[(j + 1) * w + i + 1];
  return ((v00 * (1 - tx) + v10 * tx) * (1 - ty) + (v01 * (1 - tx) + v11 * tx) * ty) / 100 + g.zbase;
}
const inGrid = (g, x, y) => x >= g.x0 && y >= g.y0 && x <= g.x0 + (g.nx - 1) * g.step && y <= g.y0 + (g.ny - 1) * g.step;

/** site (x, y) -> ground altitude in metres; the fine grid wins, the context grid covers the rest */
export function groundAt(x, y) {
  if (inGrid(S.G, x, y) || !S.C) return bilinear(S.G, x, y);
  return bilinear(S.C, x, y);
}
export const sceneY = (alt) => alt - S.BASE;
export const sx = (x) => x - S.CX;
export const sz = (y) => y - S.CZ;
/** site point -> scene vector on the ground, lifted by `up` metres */
export function onGround(x, y, up = 0) {
  return new THREE.Vector3(x - S.CX, sceneY(groundAt(x, y)) + up, y - S.CZ);
}

/** deterministic PRNG so scattered plants land in the same place on every load */
export function rng(seed) {
  let s = (seed >>> 0) || 1;
  return () => { s = (s * 1664525 + 1013904223) >>> 0; return s / 4294967296; };
}
export function hashStr(str) {
  let h = 2166136261;
  for (let i = 0; i < str.length; i++) { h ^= str.charCodeAt(i); h = Math.imul(h, 16777619); }
  return h >>> 0;
}

export function pointInPoly(x, y, poly) {
  let inside = false;
  for (let i = 0, n = poly.length, j = n - 1; i < n; j = i++) {
    const [xi, yi] = poly[i], [xj, yj] = poly[j];
    if ((yi > y) !== (yj > y) && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) inside = !inside;
  }
  return inside;
}
export const centroidOf = (poly) => [poly.reduce((a, q) => a + q[0], 0) / poly.length,
                                     poly.reduce((a, q) => a + q[1], 0) / poly.length];
export function polyArea(poly) {
  return Math.abs(poly.reduce((a, [x, y], i) => {
    const [x2, y2] = poly[(i + 1) % poly.length]; return a + (x * y2 - x2 * y);
  }, 0) / 2);
}
function segDist(px, py, [ax, ay], [bx, by]) {
  const dx = bx - ax, dy = by - ay, L2 = dx * dx + dy * dy || 1;
  const t = Math.max(0, Math.min(1, ((px - ax) * dx + (py - ay) * dy) / L2));
  return Math.hypot(px - ax - t * dx, py - ay - t * dy);
}
/** a point well inside the polygon (for labels) — the centroid of an L or a crescent can fall outside */
export function labelPoint(poly) {
  let minx = Infinity, maxx = -Infinity, miny = Infinity, maxy = -Infinity;
  poly.forEach(([x, y]) => { minx = Math.min(minx, x); maxx = Math.max(maxx, x); miny = Math.min(miny, y); maxy = Math.max(maxy, y); });
  let best = centroidOf(poly), bestD = -1;
  const n = 24;
  for (let i = 0; i <= n; i++) for (let j = 0; j <= n; j++) {
    const x = minx + ((maxx - minx) * i) / n, y = miny + ((maxy - miny) * j) / n;
    if (!pointInPoly(x, y, poly)) continue;
    let d = Infinity;
    for (let k = 0; k < poly.length; k++) d = Math.min(d, segDist(x, y, poly[k], poly[(k + 1) % poly.length]));
    if (d > bestD) { bestD = d; best = [x, y]; }
  }
  return best;
}

const _c = new THREE.Color();
/** '#rrggbb' -> THREE.Color (a new one), optionally lightened (+) or darkened (-) in HSL lightness */
export function col(hex, dl = 0) {
  const c = new THREE.Color(hex);
  if (dl) { const h = {}; c.getHSL(h); c.setHSL(h.h, h.s, Math.max(0, Math.min(1, h.l + dl))); }
  return c;
}
export function mixHex(a, b, t) { return _c.set(a).lerp(new THREE.Color(b), t).getHexString(); }

export const MONTHS = ['styczeń', 'luty', 'marzec', 'kwiecień', 'maj', 'czerwiec',
                       'lipiec', 'sierpień', 'wrzesień', 'październik', 'listopad', 'grudzień'];
export const MONTHS_GEN = ['styczniu', 'lutym', 'marcu', 'kwietniu', 'maju', 'czerwcu',
                           'lipcu', 'sierpniu', 'wrześniu', 'październiku', 'listopadzie', 'grudniu'];
export const MONTHS_OF = ['stycznia', 'lutego', 'marca', 'kwietnia', 'maja', 'czerwca',
                          'lipca', 'sierpnia', 'września', 'października', 'listopada', 'grudnia'];
export const ROMAN = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X', 'XI', 'XII'];
