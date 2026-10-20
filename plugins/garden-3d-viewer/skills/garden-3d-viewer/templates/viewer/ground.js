/* Terrain for the garden viewer: the fine 0.5 m grid around the plot carries a painted plan
   texture (crisp polygons, not per-vertex colours — a 0.5 m colour grid smeared every path edge),
   and a coarse 2 m ring around it carries the orthophoto, fading out into the page. */

import * as THREE from './vendor/three.module.min.js';
import { S, groundAt, pointInPoly, rng, polyArea, mixHex } from './site.js';

const PPM = 14;                       // plan texture: canvas pixels per metre

const GROUND = {                      // ground classes of placement.ZONES
  lawn: '#7f9a55', drive: '#cfc6b2', bed: '#86725a', play: '#dccb9b', veg: '#8f7b5e',
  orchard: '#8a9e5c', meadow: '#909f60',
};
const PLOT_BASE = '#869c5b';          // plot ground no class claims
const NO_ORTHO = '#e3ddcf';           // around the plot when the orthophoto layer is off
// lawn through the year: dull and strawy in winter, fresh in May, a little tired in August
const LAWN_BY_MONTH = ['#8f8f6c', '#8e916b', '#88955f', '#7c9a53', '#779d50', '#7a9b51',
                       '#829953', '#879756', '#829854', '#849757', '#8b935f', '#8e906a'];
const PAVE = {
  // the footpath has to read apart from the drive it runs along: warmer, lighter slabs
  drive: { fill: '#c5beb0', joint: 'rgba(70,65,55,.18)', w: 0.6, h: 0.3 },
  apron: { fill: '#c2bbac', joint: 'rgba(70,65,55,.18)', w: 0.6, h: 0.3 },
  path:  { fill: '#e6d9bd', joint: 'rgba(120,95,60,.28)', w: 0.8, h: 0.4 },
  patio: { fill: '#cfc1a8', joint: 'rgba(90,80,60,.2)',  w: 0.6, h: 0.6 },
  sand:  { fill: '#e2d2a2' },
  greenhouse: { fill: '#d5d8d4', joint: 'rgba(90,90,90,.18)', w: 0.5, h: 0.5 },
};

export class Ground {
  constructor(d, renderer) {
    this.d = d;
    const g = d.grid;
    this.W = (g.nx - 1) * g.step; this.H = (g.ny - 1) * g.step;
    this.canvas = document.createElement('canvas');
    this.canvas.width = Math.round(this.W * PPM); this.canvas.height = Math.round(this.H * PPM);
    this.ctx = this.canvas.getContext('2d');
    this.tex = new THREE.CanvasTexture(this.canvas);
    this.tex.flipY = false;
    this.tex.colorSpace = THREE.SRGBColorSpace;
    this.tex.anisotropy = renderer.capabilities.getMaxAnisotropy();
    this.ortho = null;                // HTMLImageElement once loaded
    this.lawnPolys = d.ground.filter((q) => q.cls === 'lawn').map((q) => q.poly);
    // direction of mowing stripes and paving joints: meta.axis (radians, site frame), else the plot's first long side
    this.theta = d.meta.axis ?? Math.atan2(d.plot[2][1] - d.plot[0][1], d.plot[2][0] - d.plot[0][0]);
    this.steep = this.steepness();
    this.speckles = this.scatterSpeckles();

    this.mesh = this.fineMesh();
    this.context = d.context && d.ortho ? this.contextMesh() : null;
  }

  /* ------------------------------------------------------------ meshes */
  fineMesh() {
    const g = S.G, w = g.nx, h = g.ny;
    const pos = new Float32Array(w * h * 3), uv = new Float32Array(w * h * 2);
    for (let j = 0; j < h; j++) for (let i = 0; i < w; i++) {
      const n = j * w + i, x = g.x0 + i * g.step, y = g.y0 + j * g.step;
      pos[n * 3] = x - S.CX; pos[n * 3 + 1] = g.alt[n] / 100 + g.zbase - S.BASE; pos[n * 3 + 2] = y - S.CZ;
      uv[n * 2] = (x - g.x0) / this.W; uv[n * 2 + 1] = (y - g.y0) / this.H;
    }
    const idx = [];
    for (let j = 0; j < h - 1; j++) for (let i = 0; i < w - 1; i++) {
      const a = j * w + i, b = a + 1, c = a + w, dd = c + 1;
      idx.push(a, c, b, b, c, dd);
    }
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    geo.setAttribute('uv', new THREE.BufferAttribute(uv, 2));
    geo.setIndex(idx);
    geo.computeVertexNormals();
    const m = new THREE.Mesh(geo, new THREE.MeshStandardMaterial({ map: this.tex, roughness: 1, metalness: 0 }));
    m.receiveShadow = true;
    m.name = 'terrain';
    return m;
  }

  /** 2 m ring from the fine grid's edge out to the orthophoto's edge; the hole is exactly the fine
      grid (both sit on the same 2 m lattice), dropped 3 cm so the seam can never z-fight */
  contextMesh() {
    const c = S.C, g = S.G, o = this.d.ortho;
    const [A, B, C0, D, E, F0] = o.px2site, det = A * E - B * D;
    const gx1 = g.x0 + (g.nx - 1) * g.step, gy1 = g.y0 + (g.ny - 1) * g.step;
    const w = c.nx, h = c.ny;
    const pos = new Float32Array(w * h * 3), uv = new Float32Array(w * h * 2);
    for (let j = 0; j < h; j++) for (let i = 0; i < w; i++) {
      const n = j * w + i, x = c.x0 + i * c.step, y = c.y0 + j * c.step;
      pos[n * 3] = x - S.CX; pos[n * 3 + 1] = c.alt[n] / 100 + c.zbase - S.BASE - 0.03; pos[n * 3 + 2] = y - S.CZ;
      const col = (E * (x - C0) - B * (y - F0)) / det, row = (-D * (x - C0) + A * (y - F0)) / det;
      uv[n * 2] = col / o.width; uv[n * 2 + 1] = row / o.height;
    }
    const idx = [];
    const eps = 1e-6;
    for (let j = 0; j < h - 1; j++) for (let i = 0; i < w - 1; i++) {
      const x0 = c.x0 + i * c.step, y0 = c.y0 + j * c.step, x1 = x0 + c.step, y1 = y0 + c.step;
      if (x0 >= g.x0 - eps && x1 <= gx1 + eps && y0 >= g.y0 - eps && y1 <= gy1 + eps) continue;
      const a = j * w + i, b = a + 1, cc = a + w, dd = cc + 1;
      idx.push(a, cc, b, b, cc, dd);
    }
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    geo.setAttribute('uv', new THREE.BufferAttribute(uv, 2));
    geo.setIndex(idx);
    geo.computeVertexNormals();

    // radial fade in uv space, centred on the plot, so the ring dissolves into the page
    const fc = document.createElement('canvas'); fc.width = fc.height = 256;
    const fx = fc.getContext('2d');
    const pc = ((E * (S.CX - C0) - B * (S.CZ - F0)) / det) / o.width;
    const pr = ((-D * (S.CX - C0) + A * (S.CZ - F0)) / det) / o.height;
    const grad = fx.createRadialGradient(pc * 256, pr * 256, 256 * 0.26, pc * 256, pr * 256, 256 * 0.49);
    grad.addColorStop(0, '#fff'); grad.addColorStop(1, '#000');
    fx.fillStyle = grad; fx.fillRect(0, 0, 256, 256);
    const fade = new THREE.CanvasTexture(fc); fade.flipY = false;

    this.orthoTex = new THREE.Texture();
    this.orthoTex.flipY = false;
    this.orthoTex.colorSpace = THREE.SRGBColorSpace;
    const m = new THREE.Mesh(geo, new THREE.MeshStandardMaterial({
      map: this.orthoTex, alphaMap: fade, transparent: true, alphaTest: 0.02, roughness: 1, metalness: 0, depthWrite: true }));
    m.visible = false;                // until the photo arrives
    m.renderOrder = -1;
    m.name = 'context';
    return m;
  }

  loadOrtho(onReady) {
    if (!this.d.ortho) return;
    const img = new Image();
    img.decoding = 'async';
    img.onload = () => {
      this.ortho = img;
      if (this.orthoTex) { this.orthoTex.image = img; this.orthoTex.needsUpdate = true; this.context.visible = true; }
      onReady && onReady();
    };
    img.src = this.d.ortho.file;
  }

  /* ------------------------------------------------------------ precomputed layers */
  /** steepness per 0.5 m cell as a tiny RGBA canvas (earth tint, alpha by slope), scaled up when painted */
  steepness() {
    const g = S.G, c = document.createElement('canvas');
    c.width = g.nx; c.height = g.ny;
    const cx = c.getContext('2d'), img = cx.createImageData(g.nx, g.ny);
    const a = g.alt, w = g.nx;
    for (let j = 0; j < g.ny; j++) for (let i = 0; i < g.nx; i++) {
      const i0 = Math.max(0, i - 1), i1 = Math.min(g.nx - 1, i + 1), j0 = Math.max(0, j - 1), j1 = Math.min(g.ny - 1, j + 1);
      const dx = (a[j * w + i1] - a[j * w + i0]) / 100 / ((i1 - i0) * g.step);
      const dy = (a[j1 * w + i] - a[j0 * w + i]) / 100 / ((j1 - j0) * g.step);
      const s = Math.hypot(dx, dy);
      const k = Math.max(0, Math.min(1, (s - 0.12) / 0.55));
      const p = (j * g.nx + i) * 4;
      img.data[p] = 150; img.data[p + 1] = 132; img.data[p + 2] = 92; img.data[p + 3] = Math.round(k * 150);
    }
    cx.putImageData(img, 0, 0);
    return c;
  }

  /** fixed random points for flowers painted into the ground — shown only in their months */
  scatterSpeckles() {
    const r = rng(4242);
    const fill = (poly, per, list) => {
      let minx = Infinity, maxx = -Infinity, miny = Infinity, maxy = -Infinity;
      poly.forEach(([x, y]) => { minx = Math.min(minx, x); maxx = Math.max(maxx, x); miny = Math.min(miny, y); maxy = Math.max(maxy, y); });
      const want = Math.round(polyArea(poly) * per);
      let n = 0, guard = 0;
      while (n < want && guard++ < want * 30) {
        const x = minx + r() * (maxx - minx), y = miny + r() * (maxy - miny);
        if (!pointInPoly(x, y, poly)) continue;
        list.push([x, y, r(), r()]); n++;
      }
    };
    // d.scatter: [{ look, density (points per m2), share (0..1 of them shown), polys }]
    return (this.d.scatter || []).map((sc) => {
      const pts = [];
      sc.polys.forEach((p) => fill(p, sc.density || 3, pts));
      return { look: sc.look, share: sc.share ?? 1, pts };
    });
  }

  /* ------------------------------------------------------------ painting */
  path(poly) {
    const g = S.G, ctx = this.ctx;
    ctx.beginPath();
    poly.forEach(([x, y], i) => {
      const px = (x - g.x0) * PPM, py = (y - g.y0) * PPM;
      i ? ctx.lineTo(px, py) : ctx.moveTo(px, py);
    });
    ctx.closePath();
  }
  line(pts) {
    const g = S.G, ctx = this.ctx;
    ctx.beginPath();
    pts.forEach(([x, y], i) => {
      const px = (x - g.x0) * PPM, py = (y - g.y0) * PPM;
      i ? ctx.lineTo(px, py) : ctx.moveTo(px, py);
    });
  }
  px(x, y) { return [(x - S.G.x0) * PPM, (y - S.G.y0) * PPM]; }

  /** opts: { month (1..12), ortho, gas, slopes, zones: Set of zone ids to tint, looks,
      sunmap: canvas over the fine grid | null, irrigation: { lines: bool, focus: section id | null, hose: bool } | null } */
  paint(opts) {
    const ctx = this.ctx, d = this.d, g = S.G;
    const Wp = this.canvas.width, Hp = this.canvas.height;
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.globalAlpha = 1; ctx.globalCompositeOperation = 'source-over';

    // 1. surroundings: the orthophoto (or a plain board)
    if (opts.ortho && this.ortho) {
      const [A, B, C0, D, E, F0] = d.ortho.px2site;
      ctx.fillStyle = NO_ORTHO; ctx.fillRect(0, 0, Wp, Hp);
      ctx.setTransform(A * PPM, D * PPM, B * PPM, E * PPM, (C0 - g.x0) * PPM, (F0 - g.y0) * PPM);
      ctx.imageSmoothingQuality = 'high';
      ctx.drawImage(this.ortho, 0, 0);
      ctx.setTransform(1, 0, 0, 1, 0, 0);
    } else {
      ctx.fillStyle = NO_ORTHO; ctx.fillRect(0, 0, Wp, Hp);
    }

    // 2. the plot: ground classes, last listed first so the first match ends on top (zone_at order)
    const month = opts.month;
    const lawn = LAWN_BY_MONTH[month - 1];
    ctx.save();
    this.path(d.plot); ctx.clip();
    ctx.fillStyle = '#' + mixHex(PLOT_BASE, lawn, 0.6); ctx.fillRect(0, 0, Wp, Hp);
    for (let i = d.ground.length - 1; i >= 0; i--) {
      const q = d.ground[i];
      let c = GROUND[q.cls] || PLOT_BASE;
      if (q.cls === 'lawn') c = lawn;
      else if (q.cls === 'meadow' || q.cls === 'orchard') c = '#' + mixHex(c, lawn, 0.35);
      ctx.fillStyle = c; this.path(q.poly); ctx.fill();
    }
    // mowing stripes along the house axis, lawn only
    ctx.save();
    ctx.beginPath();
    this.lawnPolys.forEach((p) => { const g2 = S.G; p.forEach(([x, y], i) => { const X = (x - g2.x0) * PPM, Y = (y - g2.y0) * PPM; i ? ctx.lineTo(X, Y) : ctx.moveTo(X, Y); }); ctx.closePath(); });
    ctx.clip();
    ctx.translate(Wp / 2, Hp / 2); ctx.rotate(this.theta);
    const stripe = 1.6 * PPM, span = Math.hypot(Wp, Hp);
    ctx.fillStyle = 'rgba(255,255,235,.055)';
    for (let k = -span; k < span; k += stripe * 2) ctx.fillRect(-span, k, span * 2, stripe);
    ctx.restore();

    // mulch and soil get a little grain, sand a little sparkle
    const grain = rng(77);
    d.ground.filter((q) => q.cls === 'bed' || q.cls === 'veg' || q.cls === 'play').forEach((q) => {
      ctx.save(); this.path(q.poly); ctx.clip();
      const n = Math.round(polyArea(q.poly) * 14);
      let minx = Infinity, miny = Infinity, maxx = -Infinity, maxy = -Infinity;
      q.poly.forEach(([x, y]) => { minx = Math.min(minx, x); maxx = Math.max(maxx, x); miny = Math.min(miny, y); maxy = Math.max(maxy, y); });
      ctx.fillStyle = q.cls === 'play' ? 'rgba(255,250,230,.35)' : 'rgba(60,45,30,.22)';
      for (let k = 0; k < n; k++) {
        const [X, Y] = this.px(minx + grain() * (maxx - minx), miny + grain() * (maxy - miny));
        ctx.fillRect(X, Y, 1.5, 1.5);
      }
      ctx.restore();
    });

    // flowers in the sward (meadow mix, bulbs naturalised in the lawn), only in the months their look flowers
    this.speckles.forEach((sc) => {
      const L = opts.looks && opts.looks[sc.look];
      const f = L && L.flowers && L.flowers[month];
      if (!f) return;
      const cols = (Array.isArray(f) ? f : [f]).filter((c) => c.startsWith('#'));
      sc.pts.forEach(([x, y, a, b]) => {
        if (a > sc.share) return;
        const [X, Y] = this.px(x, y);
        ctx.fillStyle = cols[Math.floor(b * cols.length)];
        ctx.beginPath(); ctx.arc(X, Y, 0.9 + a * 0.8, 0, 6.2832); ctx.fill();
      });
    });

    // slope faces read earthier (coconut mat + young sward)
    if (opts.slopes) {
      ctx.imageSmoothingEnabled = true;
      ctx.drawImage(this.steep, 0, 0, g.nx, g.ny, -PPM * g.step / 2, -PPM * g.step / 2, Wp + PPM * g.step, Hp + PPM * g.step);
    }
    ctx.restore();                    // plot clip

    // 3. paving with joints and a kerb line
    d.paving.forEach((s) => {
      const P = PAVE[s.kind] || PAVE.drive;
      ctx.save(); this.path(s.poly); ctx.clip();
      ctx.fillStyle = P.fill; ctx.fillRect(0, 0, Wp, Hp);
      if (P.joint && P.h * PPM >= 4) {
        // joints in the house-axis frame, limited to the polygon's own extent in that frame
        const c = Math.cos(this.theta), sn = Math.sin(this.theta);
        let u0 = Infinity, u1 = -Infinity, v0 = Infinity, v1 = -Infinity;
        s.poly.forEach(([x, y]) => {
          const [X, Y] = this.px(x, y), u = X * c + Y * sn, v = -X * sn + Y * c;
          u0 = Math.min(u0, u); u1 = Math.max(u1, u); v0 = Math.min(v0, v); v1 = Math.max(v1, v);
        });
        ctx.rotate(this.theta);
        ctx.strokeStyle = P.joint; ctx.lineWidth = 1;
        const sw = P.w * PPM, sh = P.h * PPM;
        ctx.beginPath();
        for (let v = Math.floor(v0 / sh) * sh, row = 0; v < v1; v += sh, row++) {
          ctx.moveTo(u0, v); ctx.lineTo(u1, v);
          const off = (row % 2) * sw / 2;
          for (let u = Math.floor(u0 / sw) * sw + off; u < u1; u += sw) { ctx.moveTo(u, v); ctx.lineTo(u, v + sh); }
        }
        ctx.stroke();
      } else if (!P.joint) {
        const sp = rng(9);
        ctx.fillStyle = 'rgba(255,255,245,.45)';
        for (let k = 0; k < 1500; k++) ctx.fillRect(sp() * Wp, sp() * Hp, 1.2, 1.2);
      }
      ctx.restore();
      ctx.strokeStyle = 'rgba(95,85,70,.55)'; ctx.lineWidth = 0.07 * PPM;
      this.path(s.poly); ctx.stroke();
    });

    // 3b. hours of sun, over everything on the plot
    if (opts.sunmap) {
      ctx.save(); this.path(d.plot); ctx.clip();
      ctx.globalAlpha = 0.66; ctx.imageSmoothingEnabled = true; ctx.imageSmoothingQuality = 'high';
      ctx.drawImage(opts.sunmap, 0, 0, Wp, Hp);
      ctx.restore(); ctx.globalAlpha = 1;
    }

    // 4. zone tints
    if (opts.zones && opts.zones.size) {
      d.zones.forEach((z) => {
        if (!opts.zones.has(z.id)) return;
        z.polys.forEach((p) => {
          ctx.globalAlpha = 0.34; ctx.fillStyle = z.color; this.path(p); ctx.fill();
          ctx.globalAlpha = 0.9; ctx.strokeStyle = '#' + mixHex(z.color, '#3b3a2c', 0.55);
          ctx.lineWidth = 0.08 * PPM; ctx.setLineDash([0.5 * PPM, 0.3 * PPM]); ctx.stroke(); ctx.setLineDash([]);
        });
      });
      ctx.globalAlpha = 1;
    }

    // 5. utility lines: protection band hatched, live axes solid, disused ones dashed
    if (opts.gas) {
      d.pipes.forEach((p) => {
        if (!(p.zone > 0 && p.band)) return;
        const [a, b] = p.band, dx = b[0] - a[0], dy = b[1] - a[1], L = Math.hypot(dx, dy);
        const nx = (-dy / L) * p.zone, ny = (dx / L) * p.zone;
        const band = [[a[0] + nx, a[1] + ny], [b[0] + nx, b[1] + ny], [b[0] - nx, b[1] - ny], [a[0] - nx, a[1] - ny]];
        ctx.save(); this.path(band); ctx.clip();
        ctx.fillStyle = 'rgba(192,85,46,.12)'; ctx.fillRect(0, 0, Wp, Hp);
        ctx.strokeStyle = 'rgba(176,58,26,.42)'; ctx.lineWidth = 0.05 * PPM;
        ctx.beginPath();
        for (let k = -Hp; k < Wp + Hp; k += 0.55 * PPM) { ctx.moveTo(k, 0); ctx.lineTo(k - Hp, Hp); }
        ctx.stroke();
        ctx.restore();
      });
      d.pipes.forEach((p) => {
        ctx.strokeStyle = p.active ? (p.zone > 0 ? '#b03a1a' : '#8a2a16') : '#8e8a80';
        ctx.lineWidth = (p.zone > 0 ? 0.14 : 0.22) * PPM;
        ctx.setLineDash(p.active ? [] : [0.6 * PPM, 0.4 * PPM]);
        this.line(p.line); ctx.stroke();
      });
      ctx.setLineDash([]);
    }

    // 6. crest: dashed line with downhill ticks (the plan convention for a bank)
    if (opts.slopes) {
      d.lines.filter((l) => l.kind === 'crest').forEach((l) => {
        ctx.strokeStyle = 'rgba(110,72,34,.85)'; ctx.lineWidth = 0.09 * PPM;
        this.line(l.line); ctx.stroke();
        ctx.lineWidth = 0.05 * PPM; ctx.strokeStyle = 'rgba(110,72,34,.55)';
        ctx.beginPath();
        let k = 0;
        for (let s = 0; s < l.line.length - 1; s++) {
          const [x0, y0] = l.line[s], [x1, y1] = l.line[s + 1];
          const L = Math.hypot(x1 - x0, y1 - y0); if (L < 0.2) continue;
          const ux = (x1 - x0) / L, uy = (y1 - y0) / L;
          let nx = -uy, ny = ux;
          const mx = (x0 + x1) / 2, my = (y0 + y1) / 2;
          if (groundAt(mx + nx, my + ny) > groundAt(mx - nx, my - ny)) { nx = -nx; ny = -ny; }   // ticks run downhill
          for (let t = 0.4; t < L; t += 0.7, k++) {
            const x = x0 + ux * t, y = y0 + uy * t, len = k % 2 ? 0.55 : 1.1;
            const [X0, Y0] = this.px(x, y), [X1, Y1] = this.px(x + nx * len, y + ny * len);
            ctx.moveTo(X0, Y0); ctx.lineTo(X1, Y1);
          }
        }
        ctx.stroke();
      });
    }

    // 6b. irrigation: sprinkler reach, drip lines and rings, feeds, trunks; the focused section stands out
    const irr = opts.irrigation && d.irrigation;
    if (irr) {
      const lw = (m) => Math.max(1, m * PPM);
      const stroke = (pl) => { this.line(pl); ctx.stroke(); };
      const trunk = (list) => list.forEach((t) => {
        if (t.kind === 'sleeve') { ctx.strokeStyle = 'rgba(255,255,255,.9)'; ctx.lineWidth = lw(0.34); ctx.setLineDash([]); stroke(t.line); }
        ctx.strokeStyle = '#1d4f7a'; ctx.lineWidth = lw(0.15);
        ctx.setLineDash(t.kind === 'surface' ? [0.5 * PPM, 0.3 * PPM] : []);
        stroke(t.line);
      });
      ctx.lineCap = 'round'; ctx.lineJoin = 'round';
      if (opts.irrigation.lines) irr.sections.forEach((s) => {
        ctx.globalAlpha = opts.irrigation.focus && opts.irrigation.focus !== s.id ? 0.18 : 1;
        if (s.optional && opts.irrigation.focus !== s.id) ctx.globalAlpha *= 0.55;
        s.heads.forEach(([x, y, r]) => {
          const [X, Y] = this.px(x, y);
          ctx.fillStyle = 'rgba(74,163,216,.13)'; ctx.strokeStyle = 'rgba(47,127,184,.55)'; ctx.lineWidth = 1; ctx.setLineDash([]);
          ctx.beginPath(); ctx.arc(X, Y, r * PPM, 0, 6.2832); ctx.fill(); ctx.stroke();
          ctx.fillStyle = '#1d4f7a'; ctx.beginPath(); ctx.arc(X, Y, 0.12 * PPM, 0, 6.2832); ctx.fill();
        });
        ctx.strokeStyle = s.color; ctx.setLineDash([0.22 * PPM, 0.2 * PPM]); ctx.lineWidth = lw(0.06);
        (s.feeds || []).forEach(stroke);
        ctx.setLineDash([]); ctx.lineWidth = lw(0.09);
        s.laterals.forEach(stroke);
        s.rings.forEach(([x, y, r]) => { const [X, Y] = this.px(x, y); ctx.beginPath(); ctx.arc(X, Y, r * PPM, 0, 6.2832); ctx.stroke(); });
        trunk(s.trunk);
      });
      ctx.globalAlpha = opts.irrigation.focus ? 0.4 : 1;
      if (opts.irrigation.lines) trunk(irr.main || []);
      ctx.globalAlpha = 1; ctx.setLineDash([]);
      if (opts.irrigation.hose && irr.hose) irr.sources.filter((q) => q.kind === 'tap').forEach((q) => {
        const [X, Y] = this.px(q.pt[0], q.pt[1]);
        ctx.strokeStyle = 'rgba(29,79,122,.7)'; ctx.lineWidth = lw(0.07); ctx.setLineDash([0.6 * PPM, 0.4 * PPM]);
        ctx.beginPath(); ctx.arc(X, Y, irr.hose * PPM, 0, 6.2832); ctx.stroke();
        ctx.fillStyle = 'rgba(74,163,216,.05)'; ctx.fill();
      });
      ctx.setLineDash([]); ctx.lineCap = 'butt';
    }

    // 7. the property line itself
    ctx.strokeStyle = 'rgba(60,52,42,.7)'; ctx.lineWidth = 0.05 * PPM;
    this.path(d.plot); ctx.stroke();

    this.tex.needsUpdate = true;
  }
}

export { PPM };
