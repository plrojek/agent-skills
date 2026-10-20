/* Built things for the garden viewer: the house (extruded walls, posts, hip roofs given as facets
   with overhang, soffit and fascia, PV panels, exterior doors and windows), terrace and porch
   slabs, fences, playground kit and other site furniture, garden structures. */

import * as THREE from './vendor/three.module.min.js';
import { S, groundAt, sceneY, onGround } from './site.js';
import { seasonOf } from './plants.js';

const std = (color, o = {}) => new THREE.MeshStandardMaterial({ color, roughness: 0.85, metalness: 0, ...o });
const MAT = {
  wall: std(0xf0ebe2, { roughness: 0.9 }),
  slab: std(0xcfc3ab), porch: std(0xd6cdb9),
  frame: std(0x3a3d41, { roughness: 0.6 }),
  glass: std(0x4d6273, { roughness: 0.08, metalness: 0.15, envMapIntensity: 1.4 }),
  door: std(0x5b4332, { roughness: 0.7 }),
  garage: std(0xc4bfb6, { roughness: 0.7 }), groove: std(0x9a948a),
  soffit: std(0xebe6dc, { side: THREE.BackSide }), fascia: std(0xe7e1d6),
  wood: std(0x8a6b45), metal: std(0xb9bcc0, { roughness: 0.5, metalness: 0.3 }),
  chute: std(0xe0a52c, { roughness: 0.6 }), sand: std(0xdfc99a),
};

function extrudeAt(poly, h, mat, y0) {
  const shape = new THREE.Shape(poly.map(([x, y]) => new THREE.Vector2(x - S.CX, -(y - S.CZ))));
  const geo = new THREE.ExtrudeGeometry(shape, { depth: h, bevelEnabled: false });
  geo.rotateX(-Math.PI / 2);
  const m = new THREE.Mesh(geo, mat);
  m.position.y = y0;
  m.castShadow = true; m.receiveShadow = true;
  return m;
}

/* ---------------------------------------------------------------- roof */
function tileTexture() {
  const c = document.createElement('canvas'); c.width = c.height = 256;
  const x = c.getContext('2d');
  x.fillStyle = '#93553a'; x.fillRect(0, 0, 256, 256);
  const rows = 8, cols = 8, th = 256 / rows, tw = 256 / cols;
  for (let r = 0; r < rows; r++) for (let k = 0; k < cols; k++) {
    const off = (r % 2) * tw / 2, v = ((r * 7 + k * 13) % 9) / 9;
    x.fillStyle = `rgba(${120 + v * 25},${62 + v * 12},${40 + v * 8},.55)`;
    x.fillRect(k * tw + off, r * th, tw - 1, th - 1);
    if (off) x.fillRect(k * tw - tw / 2, r * th, tw / 2 - 1, th - 1);
  }
  x.fillStyle = 'rgba(40,20,10,.35)';
  for (let r = 0; r < rows; r++) x.fillRect(0, r * th + th - 3, 256, 3);       // shadow line under each course
  const t = new THREE.CanvasTexture(c);
  t.wrapS = t.wrapT = THREE.RepeatWrapping; t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8;
  return t;
}
const TILE_PATCH = [2.4, 2.8];        // metres covered by one texture repeat (8 tiles x 8 courses)

function roofMesh(roof, y0) {
  const tri = [], uv = [], sof = [];
  const sin30 = Math.sin(Math.PI / 6);
  roof.facets.forEach((fc) => {
    const eave = fc.filter((p) => Math.abs(p[2] - roof.hEave) < 1e-3);
    const e0 = eave[0], e1 = eave[1];
    const ux = e1[0] - e0[0], uy = e1[1] - e0[1], L = Math.hypot(ux, uy);
    const toUV = (p) => [((p[0] - e0[0]) * ux + (p[1] - e0[1]) * uy) / L / TILE_PATCH[0],
                         ((p[2] - roof.hEave) / sin30) / TILE_PATCH[1]];
    const V = (p, dy = 0) => [p[0] - S.CX, y0 + p[2] + dy, p[1] - S.CZ];
    const tris = fc.length === 4 ? [[0, 1, 2], [0, 2, 3]] : [[0, 1, 2]];
    tris.forEach((t) => {
      // whatever winding the exporter used, make sure every triangle faces up
      let [a, b, c] = t.map((i) => fc[i]);
      const A = V(a), B = V(b), C = V(c);
      const n = new THREE.Vector3().crossVectors(new THREE.Vector3(...B).sub(new THREE.Vector3(...A)), new THREE.Vector3(...C).sub(new THREE.Vector3(...A)));
      if (n.y < 0) [b, c] = [c, b];
      [a, b, c].forEach((p) => { tri.push(...V(p)); uv.push(...toUV(p)); sof.push(...V(p, -0.22)); });
    });
  });
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(tri, 3));
  g.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2));
  g.computeVertexNormals();
  const top = new THREE.Mesh(g, new THREE.MeshStandardMaterial({ map: TILES, roughness: 0.8, metalness: 0 }));
  top.castShadow = true; top.receiveShadow = true;
  const gs = new THREE.BufferGeometry();
  gs.setAttribute('position', new THREE.Float32BufferAttribute(sof, 3));
  gs.computeVertexNormals();
  const soffit = new THREE.Mesh(gs, MAT.soffit);
  soffit.receiveShadow = true;
  // fascia board along the eave rectangle
  const fq = [];
  const e = roof.eave;
  for (let i = 0; i < e.length; i++) {
    const p = e[i], q = e[(i + 1) % e.length];
    const a = [p[0] - S.CX, y0 + roof.hEave - 0.24, p[1] - S.CZ], b = [q[0] - S.CX, y0 + roof.hEave - 0.24, q[1] - S.CZ];
    const c = [q[0] - S.CX, y0 + roof.hEave + 0.02, q[1] - S.CZ], d = [p[0] - S.CX, y0 + roof.hEave + 0.02, p[1] - S.CZ];
    fq.push(...a, ...b, ...c, ...a, ...c, ...d);
  }
  const gf = new THREE.BufferGeometry();
  gf.setAttribute('position', new THREE.Float32BufferAttribute(fq, 3));
  gf.computeVertexNormals();
  const fascia = new THREE.Mesh(gf, new THREE.MeshStandardMaterial({ color: 0xe7e1d6, roughness: 0.85, side: THREE.DoubleSide }));
  fascia.castShadow = true;
  const grp = new THREE.Group(); grp.add(top, soffit, fascia);
  return grp;
}
let TILES = null;

function pvMesh(panels, y0) {
  const c = document.createElement('canvas'); c.width = 64; c.height = 128;
  const x = c.getContext('2d');
  x.fillStyle = '#1f2b3d'; x.fillRect(0, 0, 64, 128);
  x.strokeStyle = 'rgba(160,175,200,.35)'; x.lineWidth = 1;
  for (let i = 1; i < 6; i++) { x.beginPath(); x.moveTo(i * 64 / 6, 0); x.lineTo(i * 64 / 6, 128); x.stroke(); }
  for (let j = 1; j < 10; j++) { x.beginPath(); x.moveTo(0, j * 12.8); x.lineTo(64, j * 12.8); x.stroke(); }
  x.strokeStyle = '#c8ccd2'; x.lineWidth = 3; x.strokeRect(0, 0, 64, 128);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace;
  const pos = [], uv = [];
  panels.forEach((q) => {
    const V = (p) => [p[0] - S.CX, y0 + p[2] + 0.02, p[1] - S.CZ];
    const U = [[0, 0], [1, 0], [1, 1], [0, 1]];
    [[0, 1, 2], [0, 2, 3]].forEach((t3) => {
      let idx = t3.slice();
      const A = new THREE.Vector3(...V(q[idx[0]])), B = new THREE.Vector3(...V(q[idx[1]])), C = new THREE.Vector3(...V(q[idx[2]]));
      if (new THREE.Vector3().crossVectors(B.sub(A), C.sub(A)).y < 0) idx = [idx[0], idx[2], idx[1]];
      idx.forEach((i) => { pos.push(...V(q[i])); uv.push(...U[i]); });
    });
  });
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  g.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2));
  g.computeVertexNormals();
  const m = new THREE.Mesh(g, new THREE.MeshStandardMaterial({ map: t, roughness: 0.3, metalness: 0.25, envMapIntensity: 1.2 }));
  m.receiveShadow = true;
  return m;
}

/* ---------------------------------------------------------------- doors and windows */
function opening(o, y0) {
  const g = new THREE.Group();
  const [ax, ay] = o.a, [bx, by] = o.b;
  const w = Math.hypot(bx - ax, by - ay), h = o.h;
  const box = (mat, bw, bh, bd, x, y, z) => {
    const m = new THREE.Mesh(new THREE.BoxGeometry(bw, bh, bd), mat);
    m.position.set(x, y, z); g.add(m); return m;
  };
  if (o.kind === 'garage') {
    box(MAT.frame, w + 0.08, h + 0.06, 0.04, 0, h / 2, 0);
    box(MAT.garage, w - 0.04, h - 0.04, 0.05, 0, h / 2, 0.01);
    for (let k = 1; k < 5; k++) box(MAT.groove, w - 0.06, 0.025, 0.06, 0, (h * k) / 5, 0.01);
  } else if (o.kind === 'door') {
    box(MAT.frame, w + 0.06, h + 0.06, 0.04, 0, h / 2, 0);
    box(MAT.door, w - 0.3, h - 0.06, 0.05, -0.12, h / 2, 0.01);
    box(MAT.glass, 0.2, h - 0.2, 0.05, w / 2 - 0.16, h / 2, 0.012);
  } else {
    box(MAT.frame, w, h, 0.04, 0, o.sill + h / 2, 0);
    box(MAT.glass, w - 0.1, h - 0.1, 0.05, 0, o.sill + h / 2, 0.01);
    const bars = o.kind === 'slider' ? Math.max(1, Math.round(w / 1.6)) : w > 1.2 ? 1 : 0;
    for (let k = 1; k <= bars; k++) box(MAT.frame, 0.06, h, 0.07, -w / 2 + (w * k) / (bars + 1), o.sill + h / 2, 0.01);
  }
  const mx = (ax + bx) / 2, my = (ay + by) / 2;
  g.position.set(mx - S.CX + o.n[0] * 0.015, y0, my - S.CZ + o.n[1] * 0.015);
  g.rotation.y = -Math.atan2(by - ay, bx - ax);
  // box depth runs along local z; after the rotation local z is perpendicular to the wall either way
  g.traverse((c) => { if (c.isMesh) { c.castShadow = false; c.receiveShadow = true; } });
  return g;
}

/* ---------------------------------------------------------------- fences */
function fenceRun(line, h, colour, postStep, panelColour) {
  const g = new THREE.Group();
  const solid = std(colour, { roughness: 0.6 });
  const panel = new THREE.MeshStandardMaterial({ color: panelColour ?? colour, transparent: true, opacity: 0.28,
                                                 side: THREE.DoubleSide, depthWrite: false, roughness: 0.8 });
  const at = (x, y, up) => onGround(x, y, up);
  for (let i = 0; i < line.length - 1; i++) {
    const [x0, y0] = line[i], [x1, y1] = line[i + 1];
    const len = Math.hypot(x1 - x0, y1 - y0);
    if (len < 0.01) continue;
    const ang = -Math.atan2(y1 - y0, x1 - x0);
    const q = new THREE.BufferGeometry();
    const a = at(x0, y0, 0.08), b = at(x1, y1, 0.08), c = at(x1, y1, h), dd = at(x0, y0, h);
    q.setAttribute('position', new THREE.Float32BufferAttribute(
      [a.x, a.y, a.z, b.x, b.y, b.z, c.x, c.y, c.z, a.x, a.y, a.z, c.x, c.y, c.z, dd.x, dd.y, dd.z], 3));
    q.computeVertexNormals();
    g.add(new THREE.Mesh(q, panel));
    for (const up of [h - 0.06, 0.22]) {
      const r = new THREE.Mesh(new THREE.BoxGeometry(len, 0.05, 0.04), solid);
      r.position.copy(at(x0, y0, up)).add(at(x1, y1, up)).multiplyScalar(0.5);
      r.rotation.y = ang; r.castShadow = true; g.add(r);
    }
    const n = Math.max(1, Math.round(len / postStep));
    for (let k = 0; k <= n; k++) {
      if (k === n && i < line.length - 2) continue;
      const f = k / n, x = x0 + (x1 - x0) * f, y = y0 + (y1 - y0) * f;
      const post = new THREE.Mesh(new THREE.BoxGeometry(0.08, h + 0.08, 0.08), solid);
      post.position.copy(at(x, y, (h + 0.08) / 2)); post.rotation.y = ang; post.castShadow = true;
      g.add(post);
    }
  }
  return g;
}

/* ---------------------------------------------------------------- site kit */
function siteObject(o) {
  const g = new THREE.Group();
  const box = (mat, w, h, dd, x, y, z) => {
    const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, dd), mat);
    m.position.set(x, y, z); m.castShadow = true; m.receiveShadow = true; g.add(m); return m;
  };
  const cyl = (mat, r, h, x, y, z, seg = 8) => {
    const m = new THREE.Mesh(new THREE.CylinderGeometry(r, r, h, seg), mat);
    m.position.set(x, y, z); m.castShadow = true; g.add(m); return m;
  };
  if (o.kind === 'swing') {
    const w = o.w, h = o.h, dd = o.d;
    for (const sx of [-w / 2, w / 2]) for (const sz of [-dd / 2, dd / 2]) {
      const leg = cyl(MAT.metal, 0.045, h * 1.04, sx * 0.92, h / 2, sz * 0.7);
      leg.rotation.x = sz > 0 ? 0.25 : -0.25;
    }
    box(MAT.metal, w + 0.1, 0.09, 0.09, 0, h, 0);
    for (const sx of [-w / 4, w / 4]) {
      box(MAT.metal, 0.02, h * 0.55, 0.02, sx - 0.18, h - h * 0.275, 0);
      box(MAT.metal, 0.02, h * 0.55, 0.02, sx + 0.18, h - h * 0.275, 0);
      box(MAT.chute, 0.45, 0.05, 0.2, sx, h - h * 0.55, 0);
    }
  } else if (o.kind === 'slide') {
    const h = o.h;
    box(MAT.wood, 0.8, 0.08, o.d, -o.w / 2 + 0.4, h * 0.88, 0);
    for (const sx of [-o.w / 2 + 0.06, -o.w / 2 + 0.74]) for (const sz of [-o.d / 2 + 0.05, o.d / 2 - 0.05]) cyl(MAT.wood, 0.04, h * 0.88, sx, h * 0.44, sz, 6);
    const run = o.w - 0.8, drop = h * 0.88 - 0.12;
    const ch = box(MAT.chute, Math.hypot(run, drop), 0.05, o.d * 0.75, -o.w / 2 + 0.8 + run / 2, h * 0.88 - drop / 2, 0);
    ch.rotation.z = -Math.atan2(drop, run);
  } else if (o.kind === 'pergola') {
    const w = o.w, dd = o.d, h = o.h;
    for (const sx of [-w / 2 + 0.1, w / 2 - 0.1]) for (const sz of [-dd / 2 + 0.1, dd / 2 - 0.1]) box(MAT.wood, 0.14, h, 0.14, sx, h / 2, sz);
    for (const sz of [-dd / 2 + 0.1, dd / 2 - 0.1]) box(MAT.wood, w, 0.14, 0.1, 0, h - 0.07, sz);
    for (let k = 0; k <= 9; k++) box(MAT.wood, 0.06, 0.1, dd, -w / 2 + (w * k) / 9, h + 0.03, 0);
    const vine = new THREE.Mesh(new THREE.IcosahedronGeometry(0.5, 1), new THREE.MeshStandardMaterial({ color: 0x7d8f56, roughness: 0.9, flatShading: true }));
    vine.scale.set(w * 0.8, 0.45, dd * 0.65); vine.position.y = h + 0.1; vine.castShadow = true;
    g.add(vine); g.userData.vine = vine;
  } else if (o.kind === 'bins') {
    const w = o.w, dd = o.d, h = o.h;
    box(MAT.wood, w, 0.06, dd, 0, 0.03, 0);
    for (const sx of [-w / 2, w / 2]) box(MAT.wood, 0.08, h, dd, sx, h / 2, 0);
    box(MAT.wood, w, h, 0.08, 0, h / 2, dd / 2 - 0.04);
    box(MAT.wood, w + 0.1, 0.08, dd + 0.1, 0, h + 0.04, 0);
    for (const sx of [-w / 3.2, 0, w / 3.2]) box(std(0x50704f), 0.56, h * 0.72, 0.6, sx, h * 0.36 + 0.06, 0);
  } else if (o.kind === 'heatpump') {
    box(std(0xdfe1e4), o.w, o.h * 0.86, o.d, 0, o.h * 0.57, 0);
    box(std(0x6d7176), o.w * 0.9, o.h * 0.14, o.d * 0.8, 0, o.h * 0.07, 0);
    const fan = cyl(std(0x3b3f44), o.w * 0.3, 0.04, 0, o.h * 0.6, -o.d / 2 - 0.01, 16);
    fan.rotation.x = Math.PI / 2;
  } else if (o.kind === 'car') {
    const L = o.w, W = o.d;
    const prof = [[-L / 2, 0.3], [-L / 2, 0.92], [-L / 2 + 0.3, 1.0], [-L / 2 + 1.0, 1.03], [-L / 2 + 1.5, 1.42],
                  [0.3, 1.46], [L / 2 - 1.45, 1.02], [L / 2 - 0.25, 0.9], [L / 2, 0.74], [L / 2, 0.3]];
    const sh = new THREE.Shape(prof.map(([x, y]) => new THREE.Vector2(x, y)));
    const body = new THREE.Mesh(new THREE.ExtrudeGeometry(sh, { depth: W, bevelEnabled: true, bevelSize: 0.04, bevelThickness: 0.04, bevelSegments: 2 }),
                                std(0x56626e, { roughness: 0.35, metalness: 0.4 }));
    body.position.z = -W / 2; body.castShadow = true; g.add(body);
    const glassProf = [[-L / 2 + 1.08, 1.05], [-L / 2 + 1.52, 1.38], [0.3, 1.41], [L / 2 - 1.5, 1.05]];
    const gl = new THREE.Mesh(new THREE.ExtrudeGeometry(new THREE.Shape(glassProf.map(([x, y]) => new THREE.Vector2(x, y))), { depth: W + 0.1, bevelEnabled: false }), MAT.glass);
    gl.position.z = -(W + 0.1) / 2; g.add(gl);
    for (const sx of [-1.42, 1.42]) for (const sz of [-W / 2 + 0.05, W / 2 - 0.05]) {
      const wh = cyl(std(0x1e1e20, { roughness: 0.9 }), 0.33, 0.24, sx, 0.33, sz, 16); wh.rotation.x = Math.PI / 2;
    }
  } else if (o.kind === 'sandpit') {
    box(MAT.sand, o.w, o.h * 0.7, o.d, 0, o.h * 0.35, 0);
    for (const [x, z, bw, bd] of [[0, -o.d / 2, o.w, 0.16], [0, o.d / 2, o.w, 0.16], [-o.w / 2, 0, 0.16, o.d], [o.w / 2, 0, 0.16, o.d]])
      box(MAT.wood, bw, o.h, bd, x, o.h / 2, z);
  }
  return g;
}

/* ---------------------------------------------------------------- build */
export class Built {
  constructor(d) {
    this.d = d;
    this.pickables = [];
    this.layers = { buildings: new THREE.Group(), fences: new THREE.Group(), site: new THREE.Group(), structures: new THREE.Group(), irrigation: new THREE.Group() };
    TILES = TILES || tileTexture();
    const y0 = sceneY(S.BASE) + 0.02;           // ground floor = plateau + 2 cm (terrain.HOUSE_ZERO)
    const B = this.layers.buildings;

    d.buildings.forEach((b) => {
      const mat = b.kind === 'house' ? MAT.wall : b.kind === 'porch' ? MAT.porch : MAT.slab;
      B.add(extrudeAt(b.poly, b.h, mat, b.kind === 'house' ? y0 : y0 - 0.02));
    });
    const h = d.house;
    if (h) {
      h.posts.forEach((p) => B.add(extrudeAt(p.poly, p.h, MAT.wall, y0)));
      h.roofs.forEach((r) => B.add(roofMesh(r, y0)));
      if (h.pv && h.pv.length) B.add(pvMesh(h.pv, y0));
      h.openings.forEach((o) => {
        const m = opening(o, y0);
        m.traverse((c) => { if (c.isMesh) { c.userData.site = { label: o.label, dims: '' }; this.pickables.push(c); } });
        B.add(m);
      });
    }

    // fences: boundary runs, plus lighter mesh runs given as lines of kind "mesh"
    const F = this.layers.fences;
    (d.fences || []).forEach((f) => F.add(fenceRun(f.line, f.h, 0x44464a, 2.5, 0x6b6f74)));
    d.lines.filter((l) => l.kind === 'mesh').forEach((l) => {
      const run = fenceRun(l.line, 1.0, 0x66705f, 2.5, 0x8d9a86);
      const idx = l.plant ? d.plants.findIndex((q) => q.id === l.plant) : -1;
      if (idx >= 0) run.traverse((c) => { if (c.isMesh) { c.userData.plantIdx = idx; this.pickables.push(c); } });
      F.add(run);
    });

    // playground kit, pergola, bins, heat pump, car; gate and wicket posts
    const Si = this.layers.site;
    this.vine = null;
    (d.site || []).forEach((o) => {
      const m = siteObject(o);
      m.position.copy(onGround(o.pt[0], o.pt[1]));
      m.rotation.y = -o.angle;
      const info = { label: o.label, dims: String(o.w).replace('.', ',') + ' × ' + String(o.d).replace('.', ',') + ' × ' + String(o.h).replace('.', ',') + ' m' };
      m.traverse((c) => { if (c.isMesh) { c.userData.site = info; this.pickables.push(c); } });
      if (m.userData.vine) { this.vine = m.userData.vine; this.vineLook = o.vineLook || null; }
      Si.add(m);
    });
    (d.markers || []).filter((mk) => mk.kind !== 'tree').forEach((mk) => {
      const post = new THREE.Mesh(new THREE.BoxGeometry(0.14, 1.7, 0.14), std(0x3f4145, { roughness: 0.6 }));
      post.position.copy(onGround(mk.pt[0], mk.pt[1], 0.85));
      post.castShadow = true;
      post.userData.site = { label: mk.label, dims: '' };
      this.pickables.push(post);
      Si.add(post);
    });

    // irrigation hardware above ground: tank lid, valve box, taps, the mains well
    const Ir = this.layers.irrigation; Ir.visible = false;
    ((d.irrigation && d.irrigation.sources) || []).forEach((q) => {
      let m;
      if (q.kind === 'tank') { m = new THREE.Mesh(new THREE.CylinderGeometry(q.r || 1, q.r || 1, 0.08, 24), std(0x3f5f4a, { roughness: 0.7 })); m.position.copy(onGround(q.pt[0], q.pt[1], 0.04)); }
      else if (q.kind === 'mains') { m = new THREE.Mesh(new THREE.CylinderGeometry(0.6, 0.6, 0.08, 20), std(0x6d7176)); m.position.copy(onGround(q.pt[0], q.pt[1], 0.04)); }
      else if (q.kind === 'valves') { m = new THREE.Mesh(new THREE.BoxGeometry(0.6, 0.1, 0.42), std(0x2f6b3d, { roughness: 0.7 })); m.position.copy(onGround(q.pt[0], q.pt[1], 0.05)); }
      else { m = new THREE.Mesh(new THREE.BoxGeometry(0.1, 0.7, 0.1), std(0x2f7fb8, { roughness: 0.5 })); m.position.copy(onGround(q.pt[0], q.pt[1], 0.35)); }
      m.castShadow = true; m.receiveShadow = true;
      m.userData.site = { label: q.label, dims: '' };
      this.pickables.push(m); Ir.add(m);
    });

    // greenhouse, raised beds, compost, shed — real footprints
    const St = this.layers.structures;
    (d.structures || []).forEach((st) => {
      const pi = d.plants.findIndex((q) => q.id === st.plant);
      const glass = !!st.glass, colour = st.color || '#9a8b6f';
      const mat = glass ? new THREE.MeshStandardMaterial({ color: colour, transparent: true, opacity: 0.45, roughness: 0.1, metalness: 0.1 })
                        : std(colour);
      const yb = sceneY(groundAt(st.poly[0][0], st.poly[0][1])) + 0.02;
      const m = extrudeAt(st.poly, st.h, mat, yb);
      if (glass) {
        m.castShadow = false;
        const edges = new THREE.LineSegments(new THREE.EdgesGeometry(m.geometry), new THREE.LineBasicMaterial({ color: 0x7c8a8e }));
        edges.position.y = yb; St.add(edges);
      }
      if (st.soil) {                            // raised beds: a soil surface just under the rim
        St.add(extrudeAt(st.poly, 0.01, std(st.soil, { roughness: 1 }), yb + st.h - 0.03));
      }
      m.userData.plantIdx = pi;
      this.pickables.push(m);
      St.add(m);
    });
  }

  /** the climber on the pergola follows the season of its look (site object field `vineLook`) */
  setMonth(month, looks) {
    if (!this.vine) return;
    const s = seasonOf(looks && looks[this.vineLook], month, 'climber');
    const fl = s.flowers && s.flowers.cols[0];
    this.vine.visible = !!(s.crown || fl);
    this.vine.material.color.set(fl || s.crown || '#7d8f56');
  }
}
