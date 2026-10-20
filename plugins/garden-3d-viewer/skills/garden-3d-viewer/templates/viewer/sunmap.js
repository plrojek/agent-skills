/* Hours of direct sun on the ground for one day (the 21st of a month), as a painted map.
   Every half hour or so between sunrise and sunset the shadows of the house, the built volumes and
   the plant crowns are stamped onto a small canvas as flat shapes; the stamps are summed and the
   sum turned into a colour ramp. The ground is treated as flat and fences cast no shadow — good
   for "is this bed in sun or in shade", not a survey. No three.js here. */

import { sunPosition, sunTimes, dayOfYear } from './sun.js';

export const RAMP = [[0, '#34407f'], [3, '#3f8f8a'], [6, '#d8c348'], [9, '#e88a2e'], [12, '#d5432b']];   // hours -> colour
const hex = (h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
function ramp(hours) {
  for (let i = 1; i < RAMP.length; i++) {
    if (hours <= RAMP[i][0] || i === RAMP.length - 1) {
      const [h0, c0] = RAMP[i - 1], [h1, c1] = RAMP[i], t = Math.max(0, Math.min(1, (hours - h0) / (h1 - h0)));
      const a = hex(c0), b = hex(c1);
      return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t];
    }
  }
  return hex(RAMP[0][1]);
}

/** d: scene; north: radians; crowns: [{ x, y, a, b, hc }] (site metres: horizontal radius, vertical
    semi-axis, centre height). Returns { canvas, dayHours } — the canvas covers the fine terrain grid. */
export function sunHours(d, north, month, crowns, ppm = 4, samples = 30) {
  const g = d.grid, site = d.meta.site;
  const W = Math.round((g.nx - 1) * g.step * ppm), H = Math.round((g.ny - 1) * g.step * ppm);
  const mk = () => { const c = document.createElement('canvas'); c.width = W; c.height = H; return c; };
  const acc = mk(), tmp = mk(), out = mk();
  const A = acc.getContext('2d', { willReadFrequently: true }), S = tmp.getContext('2d');
  A.fillStyle = '#000'; A.fillRect(0, 0, W, H);
  const doy = dayOfYear(month), t = sunTimes(site.lat, site.lon, doy);
  if (!t) return { canvas: out, dayHours: 0 };
  const X = (x) => (x - g.x0) * ppm, Y = (y) => (y - g.y0) * ppm;
  // prisms: [polygon, height]; roof facets: [[x, y, h], ...]
  const prisms = d.buildings.filter((b) => b.kind === 'house').map((b) => [b.poly, b.h])
    .concat(((d.house && d.house.posts) || []).map((p) => [p.poly, p.h]))
    .concat((d.structures || []).filter((s) => !s.glass).map((s) => [s.poly, s.h]));
  const facets = ((d.house && d.house.roofs) || []).flatMap((r) => r.facets);
  let used = 0;
  for (let k = 0; k < samples; k++) {
    const p = sunPosition(site.lat, site.lon, doy, t.rise + ((k + 0.5) / samples) * (t.set - t.rise));
    if (p.el < 0.05) continue;                               // under 3°: shadows without end, and no warmth
    used++;
    const a = p.az + north, kk = 1 / Math.tan(p.el);
    const sx = -Math.sin(a) * kk, sy = Math.cos(a) * kk;       // ground shift per metre of height, away from the sun
    const rot = Math.atan2(sy, sx);
    S.clearRect(0, 0, W, H); S.fillStyle = '#fff';
    const poly = (pts) => { S.beginPath(); pts.forEach(([x, y], i) => (i ? S.lineTo(X(x), Y(y)) : S.moveTo(X(x), Y(y)))); S.closePath(); S.fill(); };
    prisms.forEach(([pg, h]) => {
      const top = pg.map(([x, y]) => [x + sx * h, y + sy * h]);
      poly(pg); poly(top);
      for (let i = 0; i < pg.length; i++) { const j = (i + 1) % pg.length; poly([pg[i], pg[j], top[j], top[i]]); }
    });
    facets.forEach((f) => poly(f.map(([x, y, h]) => [x + sx * h, y + sy * h])));
    crowns.forEach((c) => {
      S.beginPath();
      S.ellipse(X(c.x + sx * c.hc), Y(c.y + sy * c.hc), Math.hypot(c.a, c.b * kk) * ppm, c.a * ppm, rot, 0, 6.2832);
      S.fill();
    });
    A.globalCompositeOperation = 'lighter'; A.globalAlpha = 1 / samples;
    A.drawImage(tmp, 0, 0);
  }
  const dayHours = (t.set - t.rise) * (used / samples);
  const src = A.getImageData(0, 0, W, H), O = out.getContext('2d'), dst = O.createImageData(W, H);
  for (let i = 0; i < W * H; i++) {
    const shade = Math.min(1, src.data[i * 4] / (255 * (used / samples) || 1));
    const c = ramp((1 - shade) * dayHours);
    dst.data[i * 4] = c[0]; dst.data[i * 4 + 1] = c[1]; dst.data[i * 4 + 2] = c[2]; dst.data[i * 4 + 3] = 255;
  }
  O.putImageData(dst, 0, 0);
  return { canvas: out, dayHours };
}
