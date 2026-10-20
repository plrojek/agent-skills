/* Interactive garden plan — renderer, cameras, controls and UI.
   Everything drawn comes from garden-scene.json, written by the plan's exporter: nothing here
   invents a position, a size or a species, and the seasonal looks come from the scene's `looks`.

   Modules: site.js (frame + helpers), ground.js (terrain, painted plan, orthophoto ring),
   plants.js (foliage, season model), house.js (house, fences, site kit), sun.js (solar position),
   sunmap.js (hours-of-sun map), this file. Rendering is on demand — nothing redraws while nothing changes. */

import * as THREE from './vendor/three.module.min.js';
import { EffectComposer } from './vendor/addons/postprocessing/EffectComposer.js';
import { RenderPass } from './vendor/addons/postprocessing/RenderPass.js';
import { GTAOPass } from './vendor/addons/postprocessing/GTAOPass.js';
import { OutputPass } from './vendor/addons/postprocessing/OutputPass.js';
import { RoomEnvironment } from './vendor/addons/environments/RoomEnvironment.js';
import { S, setupSite, groundAt, sceneY, labelPoint, pointInPoly, MONTHS, MONTHS_GEN, MONTHS_OF, ROMAN } from './site.js';
import { Ground } from './ground.js';
import { Plants } from './plants.js';
import { Built } from './house.js';
import { sunPosition, sunTimes, dayOfYear, clockOffset } from './sun.js';
import { sunHours, RAMP } from './sunmap.js';

const $ = (s) => document.querySelector(s);
const PAPER = 0xebe6da;

/* every sentence the viewer writes itself (index.html holds the static labels) */
const T = {
  orbitHint: 'Przeciągnij, żeby obrócić · kółko = zoom · kliknij roślinę · ← → zmienia miesiąc',
  planHint: 'Przeciągnij, żeby przesunąć · kółko = zoom · kliknij roślinę · ← → zmienia miesiąc',
  walkHint: 'W A S D lub strzałki = chodzenie · przeciągnij, żeby się rozejrzeć · Shift = szybciej',
  walkHintTouch: 'Kółko po lewej = chodzenie · przeciągnij, żeby się rozejrzeć',
  measureHint: 'Klikaj punkty na ziemi · Esc czyści',
  aerial: 'Z lotu ptaka', plan: 'Plan', walk: 'Spacer',
  siteObject: 'Obiekt terenowy', dims: 'Wymiary', zone: 'strefa',
  pieces: 'Sztuk', stock: 'Materiał', when: 'Termin', price: 'Cena', perPiece: '/szt.', mature: 'Docelowo',
  flowers: 'Kwitnie', fruit: 'Owoce', autumn: 'Jesienią', autumnHead: 'Barwy jesienne',
  nothing: 'Nic nie kwitnie — spoczynek zimowy.', inMonth: 'W ',
  play: 'Odtwórz rok', pause: 'Zatrzymaj',
  entries: 'Pozycji planu', positions: 'Miejsc sadzenia', total: 'Sztuk razem', plateau: 'Poziom terenu', asl: ' m n.p.m.',
  layers: { plants: 'Nasadzenia', buildings: 'Dom i taras', slopes: 'Skarpy i korona', gas: 'Sieci i strefy ochronne',
            fences: 'Ogrodzenia', site: 'Obiekty w ogrodzie', zones: 'Strefy (kolor)', ortho: 'Ortofotomapa wokół', labels: 'Etykiety na planie',
            irrigation: 'Nawadnianie', hose: 'Zasięg węża z kranów', sunmap: 'Nasłonecznienie (godz. słońca)' },
  sunrise: 'wschód', sunset: 'zachód', night: 'noc', studio: 'światło stałe',
  byZone: 'wg stref', byYear: 'wg roku', noDate: 'bez terminu', sum: 'Razem', costNote: 'Widełki cen z planu × liczba sztuk.',
  segment: 'odcinek', path: 'razem', area: 'pole', clear: 'Wyczyść',
  highlighted: 'Podświetlone: ',
  all: 'całość', upTo: 'do ', notYet: ' — jeszcze nieposadzone',
  sunmapNote: (day, st) => 'Bezpośrednie słońce ' + day + ', wzrost: ' + st + '. Teren liczony jako płaski, bez cienia ogrodzeń.',
  irr: { section: 'Nawadnianie · sekcja ', tank: 'ze zbiornika na deszczówkę', mains: 'z sieci wodociągowej', line: 'Linia kroplująca', emitters: 'Emitery',
         heads: 'Zraszacze', flow: 'Przepływ', demand: 'Zapotrzebowanie (lipiec)', run: 'Czas pracy', trench: 'Wykop', sleeve: 'Przepust', surface: 'Na powierzchni',
         feeds: 'Dojścia 16 mm', perWeek: ' l/tydz.', minWeek: ' min/tydz.', temporary: (n) => 'tymczasowa — ' + n + ' sezony', optional: 'opcja',
         week: 'Kroplowanie, lipiec', autonomy: 'Zbiornik bez deszczu', days: ' dni', roof: 'Dopływ z dachu (lipiec)', lawn: 'Trawniki (z sieci)',
         cost: 'Nawadnianie', costOpt: 'nawadnianie — opcje', plants: 'Pozycje planu: ' },
  csv: { name: 'zakupy', head: ['grupa', 'kod', 'strefa', 'nazwa łacińska', 'nazwa', 'odmiana', 'sztuk', 'materiał', 'termin', 'rok', 'cena jedn.', 'koszt od', 'koszt do'],
         irr: 'nawadnianie', irrOpt: 'nawadnianie — opcje' },
  ctxLost: 'przeglądarka odebrała stronie grafikę 3D (WebGL) — odśwież stronę',
  loadFail: 'Nie udało się wczytać sceny: ',
  subtitle: (c, v) => c.entries + ' pozycji · ' + c.pieces + ' szt.' + (v ? ' · plan ' + v : ''),
};
const num = (v, d = 1) => v.toFixed(d).replace('.', ',');
const money = (v) => (Math.round(v / 10) * 10).toLocaleString('pl-PL');
const clock = (h) => { const m = Math.round(((h % 24) + 24) % 24 * 60); return Math.floor(m / 60) + ':' + String(m % 60).padStart(2, '0'); };

/* growth stages — crown size as a fraction of the mature figure in the plan */
const STAGES = [
  { label: 'po posadzeniu', f: 0.22 },
  { label: 'rok 1',         f: 0.30 },
  { label: 'rok 5',         f: 0.55 },
  { label: 'rok 10',        f: 0.75 },
  { label: 'docelowo',      f: 1.00 },
];

/* ---------------------------------------------------------------- renderer */
S.mobile = matchMedia('(max-width: 820px), (pointer: coarse)').matches;
const stage = $('#stage');
const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' });
renderer.setPixelRatio(Math.min(devicePixelRatio, S.mobile ? 2 : 1.75));
renderer.setSize(innerWidth, innerHeight);
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.NeutralToneMapping;
renderer.toneMappingExposure = 1.0;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
stage.appendChild(renderer.domElement);

// Float colour buffers back both the room environment (PMREM) and the AO composer. Safari hides
// them in some modes (private windows with fingerprinting protection) and older phones lack them:
// without them the scene still renders, just without reflections and AO, instead of not at all.
const FLOAT_RT = renderer.capabilities.isWebGL2 &&
  (renderer.extensions.has('EXT_color_buffer_float') || renderer.extensions.has('EXT_color_buffer_half_float'));

const scene = new THREE.Scene();
scene.background = new THREE.Color(PAPER);
if (FLOAT_RT) {
  try {
    const pmrem = new THREE.PMREMGenerator(renderer);
    scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
    scene.environmentIntensity = 0.42;
    pmrem.dispose();
  } catch (e) { console.warn('garden: no room environment', e); scene.environment = null; }
}

const HEMI = FLOAT_RT ? 0.85 : 1.15;                 // makes up for the missing environment light
const hemi = new THREE.HemisphereLight(0xf1efe8, 0x7f7c62, HEMI);
scene.add(hemi);
const sun = new THREE.DirectionalLight(0xfff0d8, 2.45);
sun.castShadow = true;
sun.shadow.mapSize.set(S.mobile ? 2048 : 4096, S.mobile ? 2048 : 4096);
sun.shadow.bias = -0.0004;
sun.shadow.normalBias = 0.03;
scene.add(sun, sun.target);

const persp = new THREE.PerspectiveCamera(40, innerWidth / innerHeight, 0.5, 1500);
const ortho = new THREE.OrthographicCamera(-1, 1, 1, -1, 1, 1200);
let camera = persp;

/* ambient occlusion on desktops only: it is the single biggest "model" cue (shrubs sit on the
   ground, the house meets the terrace), and the single biggest cost on a phone GPU */
let composer = null, gtao = null, renderPass = null;
const AO = !S.mobile && FLOAT_RT;
if (AO) try {
  const rt = new THREE.WebGLRenderTarget(1, 1, { type: THREE.HalfFloatType, samples: 4 });
  composer = new EffectComposer(renderer, rt);
  renderPass = new RenderPass(scene, persp);
  composer.addPass(renderPass);
  gtao = new GTAOPass(scene, persp, innerWidth, innerHeight);
  gtao.updateGtaoMaterial({ radius: 1.1, distanceExponent: 1.4, thickness: 1.6, scale: 1.25, samples: 16, distanceFallOff: 1.0 });
  gtao.updatePdMaterial({ lumaPhi: 10, depthPhi: 2, normalPhi: 3, radius: 6, rings: 2, samples: 16 });
  gtao.blendIntensity = 0.85;
  composer.addPass(gtao);
  composer.addPass(new OutputPass());
  composer.setPixelRatio(renderer.getPixelRatio());
  composer.setSize(innerWidth, innerHeight);
} catch (e) { console.warn('garden: AO off', e); composer = null; gtao = null; renderPass = null; }

let dirty = true;
const requestRender = () => { dirty = true; };
// a GPU reset or memory pressure takes the context away: say so, and redraw if the browser gives it back
renderer.domElement.addEventListener('webglcontextlost', (e) => {
  e.preventDefault();
  window.__gardenReady = false;
  window.__gardenFail && window.__gardenFail(T.ctxLost);
});
renderer.domElement.addEventListener('webglcontextrestored', () => { $('#load').hidden = true; requestRender(); });
// console handle for checking the scene by hand (no state is read back from it)
window.__garden = { renderer, scene, gtao, composer, S, get camera() { return camera; }, render: () => requestRender(),
  /** look at site point (x, y) from azimuth / polar angle / distance — for checking a detail by hand */
  look(x, y, a, p, d) { plan.on = false; walk.on = false; tween = null; target.set(x - S.CX, sceneY(groundAt(x, y)) + 1, y - S.CZ); azim = a; polar = p; dist = d; applyCam(); } };

/* ---------------------------------------------------------------- state */
let DATA = null, ground = null, plants = null, built = null;
let growth = 2, month = new Date().getMonth() + 1;
const layerOn = { plants: true, buildings: true, slopes: true, gas: true, fences: true, site: true, zones: false, ortho: true, labels: true,
                  irrigation: false, hose: false, sunmap: false };
let irrFocus = null;                                   // irrigation section picked in the panel
let phase = null;                                      // planting stage: show what is planted up to this year (null = all)
const zonesOn = new Set();
const pickables = [];

/* ---------------------------------------------------------------- camera control */
const target = new THREE.Vector3();
let azim = -2.15, polar = 0.95, dist = 110;
let plan = { on: false, cx: 0, cz: 0, mpp: 0.1 };      // orthographic plan: centre and metres per pixel
let planMoved = false;                                 // the plan was panned or zoomed since it was fitted
let exporting = false;                                 // a picture is being rendered: no UI to keep clear of
const walk = { on: false, x: 0, y: 0, yaw: 0, pitch: 0, fov: 62 };     // eye-level walk: site position, look angles
const EYE = 1.65;
const SAFE = () => exporting ? { left: 12, right: 12, top: 12, bottom: 12 } : ({   // screen margins kept clear of the UI
  left: NARROW() ? 12 : ($('#panel').offsetWidth + 28), right: 16,
  top: $('header').offsetHeight + 6, bottom: $('#dock').offsetHeight + (NARROW() ? 18 : 26),
});
const NARROW = () => innerWidth <= 820;                // the CSS breakpoint: panel becomes a sheet, the dock shows one slider
/** tell the stylesheet how tall the pinned header and dock are, so everything else stacks clear of them */
function layoutVars() {
  const st = document.documentElement.style;
  st.setProperty('--headh', ($('header').offsetHeight + 4) + 'px');
  st.setProperty('--dockh', ($('#dock').offsetHeight + 10) + 'px');
}

function applyCam() {
  const W = innerWidth, H = innerHeight, m = SAFE();
  // shift the projection centre into the free area right of the panel and between header / season bar
  const cxOff = (m.left - m.right) / 2, cyOff = (m.top - m.bottom) / 2;
  if (plan.on) {
    camera = ortho;
    const hw = (W / 2) * plan.mpp, hh = (H / 2) * plan.mpp;
    ortho.left = -hw - cxOff * plan.mpp; ortho.right = hw - cxOff * plan.mpp;
    ortho.top = hh + cyOff * plan.mpp; ortho.bottom = -hh + cyOff * plan.mpp;
    ortho.position.set(plan.cx, 400, plan.cz);
    ortho.up.set(0, 0, -1);
    ortho.lookAt(plan.cx, 0, plan.cz);
    ortho.updateProjectionMatrix();
  } else {
    camera = persp;
    persp.setViewOffset(W + Math.abs(2 * cxOff), H + Math.abs(2 * cyOff), cxOff < 0 ? 2 * -cxOff : 0, cyOff < 0 ? 2 * -cyOff : 0, W, H);
    persp.aspect = (W + Math.abs(2 * cxOff)) / (H + Math.abs(2 * cyOff));
    persp.fov = walk.on ? walk.fov : 40; persp.near = walk.on ? 0.15 : 0.5;
    persp.up.set(0, 1, 0);
  }
  if (!plan.on && walk.on) {
    walk.pitch = Math.max(-1.2, Math.min(1.2, walk.pitch));
    const ex = walk.x - S.CX, ez = walk.y - S.CZ, ey = sceneY(groundAt(walk.x, walk.y)) + EYE, cp = Math.cos(walk.pitch);
    persp.position.set(ex, ey, ez);
    persp.lookAt(ex + cp * Math.cos(walk.yaw), ey + Math.sin(walk.pitch), ez + cp * Math.sin(walk.yaw));
    persp.updateProjectionMatrix();
  } else if (!plan.on) {
    polar = Math.max(0.03, Math.min(Math.PI / 2 - 0.02, polar));
    dist = Math.max(4, Math.min(600, dist));
    persp.position.set(
      target.x + dist * Math.sin(polar) * Math.cos(azim),
      target.y + dist * Math.cos(polar),
      target.z + dist * Math.sin(polar) * Math.sin(azim));
    persp.lookAt(target);
    persp.updateProjectionMatrix();
  }
  if (renderPass) { renderPass.camera = camera; gtao.camera = camera; }
  requestRender();
}

/** points that must fit on screen in an overview: plot corners at ground level and at tree height */
function fitPoints() {
  const pts = [];
  DATA.plot.forEach(([x, y]) => {
    const g = sceneY(groundAt(x, y));
    pts.push(new THREE.Vector3(x - S.CX, g, y - S.CZ), new THREE.Vector3(x - S.CX, g + 7, y - S.CZ));
  });
  return pts;
}
/** closest distance at which the whole plot sits inside the free area (not under the panel,
    the header or the season bar) — on a portrait phone that is far further back than on a desktop */
function fitDist() {
  const pts = fitPoints(), v = new THREE.Vector3(), m = SAFE(), W = innerWidth, H = innerHeight;
  let lo = 8, hi = 800;
  for (let k = 0; k < 30; k++) {
    dist = (lo + hi) / 2; applyCam(); persp.updateMatrixWorld();
    const ok = pts.every((p) => {
      v.copy(p).project(persp);
      const px = ((v.x + 1) / 2) * W, py = ((1 - v.y) / 2) * H;
      return v.z < 1 && px > m.left + 6 && px < W - m.right - 6 && py > m.top + 6 && py < H - m.bottom - 6;
    });
    if (ok) hi = dist; else lo = dist;
  }
  dist = hi;
}
function fitPlan() {
  const m = SAFE();
  let minx = Infinity, maxx = -Infinity, minz = Infinity, maxz = -Infinity;
  DATA.plot.forEach(([x, y]) => { minx = Math.min(minx, x); maxx = Math.max(maxx, x); minz = Math.min(minz, y); maxz = Math.max(maxz, y); });
  const W = innerWidth - m.left - m.right, H = innerHeight - m.top - m.bottom;
  plan.mpp = Math.max((maxx - minx + 6) / W, (maxz - minz + 6) / H);
  plan.cx = (minx + maxx) / 2 - S.CX; plan.cz = (minz + maxz) / 2 - S.CZ;
}

/* views: computed from the geometry, so the labels mean what they say */
const VIEWS = {
  aerial: { azim: -2.15, polar: 0.95, fit: true, t: [0, 0, 0] },
  plan:   { plan: true },
  walk:   { walk: true },
};                                     // + one eye-level view per entry of the scene's `views`
function eyeView(from, to, step) {
  let fx = from[0], fy = from[1];
  if (step) {
    const dx = to[0] - fx, dy = to[1] - fy, L = Math.hypot(dx, dy) || 1;
    fx += (dx / L) * step; fy += (dy / L) * step;
  }
  const cx = fx - S.CX, cz = fy - S.CZ, cy = sceneY(groundAt(fx, fy)) + 1.6;
  const tx = to[0] - S.CX, tz = to[1] - S.CZ, ty = sceneY(groundAt(to[0], to[1])) + 1.2;
  const dx = cx - tx, dy = cy - ty, dz = cz - tz, d = Math.hypot(dx, dy, dz);
  return { azim: Math.atan2(dz, dx), polar: Math.acos(dy / d), dist: d, t: [tx, ty, tz] };
}

let currentView = 'aerial', tween = null;
function markView(name) {
  currentView = name;
  document.querySelectorAll('[data-view]').forEach((b) => b.classList.toggle('on', b.dataset.view === name));
  setHint();
}
function setHint() {
  $('#hint').textContent = measure.on ? T.measureHint : walk.on ? (S.mobile ? T.walkHintTouch : T.walkHint) : plan.on ? T.planHint : T.orbitHint;
  $('#stick').hidden = !walk.on;
  el.style.cursor = measure.on ? 'crosshair' : '';
}
/** stand at a site point looking at another (both [x, y]) */
function standAt(from, to) {
  walk.x = from[0]; walk.y = from[1]; walk.pitch = 0;
  walk.yaw = Math.atan2(to[1] - from[1], to[0] - from[0]);
}
function goView(name, animate = true) {
  const v = VIEWS[name]; if (!v) return;
  if (v.walk) {
    // start where the first eye-level view stands (usually the gate), else in the middle of the plot
    if (!walk.on) { const e = DATA.views && DATA.views[DATA.views.length - 1]; standAt(e ? e.from : [S.CX, S.CZ], e ? e.to : [S.CX, S.CZ - 1]); }
    tween = null; plan.on = false; walk.on = true; markView(name); applyCam(); updateOverlay(); return;
  }
  const wasWalk = walk.on;
  walk.on = false;
  markView(name);
  if (v.plan) {
    tween = null; fitPlan(); planMoved = false; plan.on = true; applyCam(); updateOverlay(); return;
  }
  const from = { azim, polar, dist, t: target.clone() };
  const wasPlan = plan.on || wasWalk;
  plan.on = false;
  let to;
  if (v.fit) {
    azim = v.azim; polar = v.polar; target.set(...v.t); fitDist();
    to = { azim, polar, dist, t: target.clone() };
  } else to = { azim: v.azim, polar: v.polar, dist: v.dist, t: new THREE.Vector3(...v.t) };
  if (!animate || wasPlan) { azim = to.azim; polar = to.polar; dist = to.dist; target.copy(to.t); applyCam(); return; }
  // shortest way round
  let da = to.azim - from.azim; da = Math.atan2(Math.sin(da), Math.cos(da));
  tween = { t0: performance.now(), dur: 900, from, to: { ...to, azim: from.azim + da } };
  azim = from.azim; polar = from.polar; dist = from.dist; target.copy(from.t);
}
function stepTween(now) {
  if (!tween) return;
  const k = Math.min(1, (now - tween.t0) / tween.dur), e = k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2;
  const a = tween.from, b = tween.to;
  azim = a.azim + (b.azim - a.azim) * e; polar = a.polar + (b.polar - a.polar) * e;
  dist = Math.exp(Math.log(a.dist) + (Math.log(b.dist) - Math.log(a.dist)) * e);
  target.lerpVectors(a.t, b.t, e);
  applyCam();
  if (k >= 1) tween = null;
}

/* pointer: orbit / pan / pinch in 3D, pan / zoom on the plan */
const ptrs = new Map();
let mode = null, last = null, pinch0 = 0, moved = 0;
const el = renderer.domElement;
el.addEventListener('pointerdown', (e) => {
  try { el.setPointerCapture(e.pointerId); } catch { /* stale or synthetic pointer id */ }
  ptrs.set(e.pointerId, { x: e.clientX, y: e.clientY });
  moved = 0; tween = null;
  if (ptrs.size === 1) { mode = walk.on ? 'look' : (e.button === 2 || e.shiftKey || plan.on) ? 'pan' : 'orbit'; last = { x: e.clientX, y: e.clientY }; }
  else if (ptrs.size === 2) {
    const [a, b] = [...ptrs.values()];
    pinch0 = Math.hypot(a.x - b.x, a.y - b.y); mode = 'pinch';
    last = { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 };
  }
});
el.addEventListener('pointermove', (e) => {
  if (!ptrs.has(e.pointerId)) { hover(e); return; }
  ptrs.set(e.pointerId, { x: e.clientX, y: e.clientY });
  if (mode === 'pinch' && ptrs.size === 2) {
    const [a, b] = [...ptrs.values()];
    const d2 = Math.hypot(a.x - b.x, a.y - b.y);
    const mid = { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 };
    if (pinch0 > 0) zoomBy(pinch0 / Math.max(1, d2), mid.x, mid.y);
    pinch0 = d2;
    panBy(mid.x - last.x, mid.y - last.y);
    last = mid; applyCam(); updateOverlay();
    return;
  }
  if (!last) return;
  const dx = e.clientX - last.x, dy = e.clientY - last.y;
  moved += Math.abs(dx) + Math.abs(dy);
  if (mode === 'look') { walk.yaw -= dx * 0.004; walk.pitch += dy * 0.004; }
  else if (mode === 'orbit') { azim += dx * 0.006; polar -= dy * 0.006; if (currentView) markView(null); }
  else panBy(dx, dy);
  last = { x: e.clientX, y: e.clientY };
  applyCam(); updateOverlay();
});
function panBy(dx, dy) {
  if (walk.on) return;
  if (plan.on) { plan.cx -= dx * plan.mpp; plan.cz -= dy * plan.mpp; planMoved = true; return; }
  const k = dist * 0.0014;
  const right = new THREE.Vector3(-Math.sin(azim - Math.PI / 2), 0, Math.cos(azim - Math.PI / 2));
  const fwd = new THREE.Vector3(-Math.cos(azim), 0, -Math.sin(azim));
  target.addScaledVector(right, -dx * k);
  target.addScaledVector(fwd, -dy * k);
  if (currentView) markView(null);
}
function zoomBy(f, mx, my) {
  if (plan.on) {
    // keep the point under the cursor in place
    const W = innerWidth, H = innerHeight, m = SAFE();
    const ox = mx - W / 2 - (m.left - m.right) / 2, oy = my - H / 2 - (m.top - m.bottom) / 2;
    const nm = Math.max(0.006, Math.min(0.5, plan.mpp * f));
    plan.cx += ox * (plan.mpp - nm); plan.cz += oy * (plan.mpp - nm); plan.mpp = nm; planMoved = true;
    return;
  }
  if (walk.on) { walk.fov = Math.max(30, Math.min(80, walk.fov * f)); return; }
  dist *= f; if (currentView) markView(null);
}
function endPtr(e) {
  ptrs.delete(e.pointerId);
  if (ptrs.size === 0) { if (moved < 6) (measure.on ? measureClick(e) : pick(e)); mode = null; last = null; }
  else if (ptrs.size === 1) { mode = walk.on ? 'look' : plan.on ? 'pan' : 'orbit'; const p = [...ptrs.values()][0]; last = { x: p.x, y: p.y }; }
}
el.addEventListener('pointerup', endPtr);
el.addEventListener('pointercancel', (e) => { ptrs.delete(e.pointerId); mode = null; last = null; });
el.addEventListener('contextmenu', (e) => e.preventDefault());
el.addEventListener('wheel', (e) => {
  e.preventDefault(); tween = null;
  zoomBy(Math.exp(e.deltaY * 0.0012), e.clientX, e.clientY); applyCam(); updateOverlay();
}, { passive: false });

/* ---------------------------------------------------------------- picking */
const ray = new THREE.Raycaster();
const ndc = new THREE.Vector2();
function hit(ev) {
  ndc.set((ev.clientX / innerWidth) * 2 - 1, -(ev.clientY / innerHeight) * 2 + 1);
  ray.setFromCamera(ndc, camera);
  const vis = (o) => { for (let p = o; p; p = p.parent) if (!p.visible) return false; return true; };
  const hits = ray.intersectObjects(pickables.filter(vis), false);
  for (const h of hits) {
    const u = h.object.userData;
    if (u.pick) {
      const b = u.pick[h.instanceId];
      if (!b) continue;
      _m4.identity(); h.object.getMatrixAt(h.instanceId, _m4);
      if (_m4.elements[0] === 0 && _m4.elements[5] === 0) continue;       // hidden instance (scale 0)
      if (b.site) return { site: b.site };
      return { plantIdx: b.plantIdx, ptIdx: b.ptIdx, v: b.v };
    }
    if (u.plantIdx != null && u.plantIdx >= 0) return { plantIdx: u.plantIdx, ptIdx: -1 };
    if (u.site) return { site: u.site };
  }
  return null;
}
const _m4 = new THREE.Matrix4();
function pick(ev) {
  const b = hit(ev);
  if (!b) { $('#info').hidden = true; setHighlight(null); if (irrFocus) { irrFocus = null; document.querySelectorAll('#irr tr.on').forEach((r) => r.classList.remove('on')); paintGround(); } return; }
  if (b.site) { setHighlight(null); return showSiteInfo(b.site); }
  const p = DATA.plants[b.plantIdx];
  showInfo(p, b);
  setHighlight(p.id + ' · ' + p.polish.split('—')[0].trim(), (q) => q.plantIdx === b.plantIdx, false);
}
let tipTimer = 0;
function hover(ev) {
  if (S.mobile || measure.on) return;
  cancelAnimationFrame(tipTimer);
  tipTimer = requestAnimationFrame(() => {
    const b = hit(ev), tip = $('#tip');
    if (!b) { tip.hidden = true; el.style.cursor = plan.on ? 'move' : 'grab'; return; }
    const p = b.site ? null : DATA.plants[b.plantIdx];
    tip.textContent = b.site ? b.site.label : p.id + ' · ' + (b.v && b.v.name && p.variants.length > 1 ? (b.v.label || b.v.name) : p.polish.split('—')[0].trim());
    tip.style.left = ev.clientX + 'px'; tip.style.top = ev.clientY + 'px';
    tip.hidden = false; el.style.cursor = 'pointer';
  });
}

/** month keys of a look table -> 'IV–V, VII' */
function monthsText(obj) {
  const ms = Object.keys(obj || {}).map(Number).sort((a, b) => a - b);
  const out = [];
  for (let i = 0; i < ms.length; i++) {
    let j = i; while (j + 1 < ms.length && ms[j + 1] === ms[j] + 1) j++;
    out.push(i === j ? ROMAN[ms[i] - 1] : ROMAN[ms[i] - 1] + '–' + ROMAN[ms[j] - 1]); i = j;
  }
  return out.join(', ');
}
function showSiteInfo(o) {
  $('#i-code').textContent = T.siteObject;
  $('#i-name').textContent = o.label;
  $('#i-lat').textContent = '';
  $('#i-dl').innerHTML = o.dims ? '<dt>' + (/\d ×/.test(o.dims) ? T.dims : '') + '</dt><dd>' + o.dims + '</dd>' : '';
  $('#i-where').textContent = ''; $('#i-notes').textContent = '';
  $('#info').hidden = false;
}
function showInfo(p, b) {
  const zone = DATA.zones.find((z) => z.id === p.zone);
  $('#i-code').textContent = p.id + ' · ' + T.zone + ' ' + p.zone + (zone ? ' — ' + zone.name : '');
  $('#i-name').textContent = p.polish;
  const v = b && b.v ? b.v : (b && b.ptIdx >= 0 ? p.variants[p.ptVariant[b.ptIdx]] : p.variants[0]);
  $('#i-lat').textContent = p.variants.length > 1 && v ? v.name : p.latin + (p.cultivar ? ' ' + p.cultivar : '');
  const rows = [[T.pieces, p.qty], [T.stock, p.size], [T.when, p.when], [T.price, p.price ? p.price + ' ' + CUR + T.perPiece : '']];
  if (v && v.h && v.kind !== 'ground') rows.push([T.mature, num(v.h) + ' m' + (v.dia ? ' · Ø ' + num(v.dia) + ' m' : '')]);
  const L = v && DATA.looks[v.look];
  if (L && L.flowers) rows.push([T.flowers, monthsText(L.flowers)]);
  if (L && L.fruit) rows.push([T.fruit, monthsText(L.fruit)]);
  if (L && L.autumn) rows.push([T.autumn, '<span class="swatch" style="background:' + Object.values(L.autumn)[0] + '"></span>' + monthsText(L.autumn)]);
  $('#i-dl').innerHTML = rows.filter((r) => r[1] !== '' && r[1] != null)
    .map((r) => '<dt>' + r[0] + '</dt><dd>' + String(r[1]) + '</dd>').join('');
  $('#i-where').textContent = p.where;
  $('#i-notes').textContent = p.notes;
  $('#info').hidden = false;
}

/* ---------------------------------------------------------------- plan overlay: labels, compass, scale bar */
let labels = [];
function buildLabels() {
  const box = $('#labels'); box.innerHTML = ''; labels = [];
  const add = (x, y, text, cls) => {
    const e = document.createElement('div'); e.className = 'lb ' + cls; e.textContent = text; box.appendChild(e);
    labels.push({ e, p: new THREE.Vector3(x - S.CX, sceneY(groundAt(x, y)), y - S.CZ), cls });
  };
  DATA.zones.forEach((z) => {
    if (!z.polys.length) return;
    const big = z.polys.reduce((a, q) => (q.length > a.length ? q : a), z.polys[0]);
    const [x, y] = labelPoint(big); add(x, y, z.id, 'zone');
  });
  DATA.plants.forEach((p) => {
    if (p.sym === 'none') return;
    const clusters = [];
    p.pts.forEach(([x, y]) => {
      const c = clusters.find((q) => Math.hypot(q.x / q.n - x, q.y / q.n - y) < 5);
      if (c) { c.x += x; c.y += y; c.n++; } else clusters.push({ x, y, n: 1 });
    });
    p.rows.forEach((r) => { const m = r[Math.floor(r.length / 2)]; clusters.push({ x: m[0], y: m[1], n: 1 }); });
    p.areas.forEach((a) => { const [x, y] = labelPoint(a); clusters.push({ x, y, n: 1 }); });
    clusters.forEach((c) => add(c.x / c.n, c.y / c.n, p.id, 'plant'));
  });
}
const _v = new THREE.Vector3();
function updateOverlay() {
  const show = plan.on && layerOn.labels;
  $('#labels').hidden = !show;
  if (show) {
    const W = innerWidth, H = innerHeight, detail = plan.mpp < 0.075;
    camera.updateMatrixWorld();
    labels.forEach((l) => {
      if (l.cls === 'plant' && !detail) { l.e.style.display = 'none'; return; }
      _v.copy(l.p).project(camera);
      l.e.style.display = '';
      l.e.style.transform = `translate(${((_v.x + 1) / 2) * W}px, ${((1 - _v.y) / 2) * H}px) translate(-50%, -50%)`;
    });
  }
  // compass: where north (-z) points on screen
  camera.updateMatrixWorld();
  const a = new THREE.Vector3(target.x, 0, target.z);
  if (plan.on) a.set(plan.cx, 0, plan.cz);
  else if (walk.on) a.set(walk.x - S.CX + 12 * Math.cos(walk.yaw), sceneY(groundAt(walk.x, walk.y)), walk.y - S.CZ + 12 * Math.sin(walk.yaw));
  const b = a.clone().add(new THREE.Vector3(Math.sin(NORTH) * 8, 0, -Math.cos(NORTH) * 8));
  a.project(camera); b.project(camera);
  const ang = Math.atan2((b.x - a.x) * innerWidth, (b.y - a.y) * innerHeight);
  $('#compass svg').style.transform = `rotate(${ang}rad)`;
  // scale bar on the plan
  const sb = $('#scalebar');
  sb.hidden = !plan.on;
  if (plan.on) {
    const nice = [1, 2, 5, 10, 20, 50].find((m) => m / plan.mpp >= 70) || 50;
    sb.querySelector('i').style.width = Math.round(nice / plan.mpp) + 'px';
    sb.querySelector('span').textContent = nice + ' m';
  }
  drawMeasure();
}

/* ---------------------------------------------------------------- tape measure: points on the ground, lengths in the site plane */
const measure = { on: false, pts: [] };                 // pts: site [x, y]
const SVGNS = 'http://www.w3.org/2000/svg';
function groundHit(ev) {
  ndc.set((ev.clientX / innerWidth) * 2 - 1, -(ev.clientY / innerHeight) * 2 + 1);
  ray.setFromCamera(ndc, camera);
  const objs = [ground.mesh]; if (ground.context && ground.context.visible) objs.push(ground.context);
  const h = ray.intersectObjects(objs, false)[0];
  return h ? [h.point.x + S.CX, h.point.z + S.CZ] : null;
}
function measureClick(ev) {
  const p = groundHit(ev); if (!p) return;
  measure.pts.push(p); updateOverlay();
}
function setMeasure(on) {
  measure.on = on; if (!on) measure.pts = [];
  $('#b-measure').classList.toggle('on', on);
  $('#tip').hidden = true; setHint(); updateOverlay();
}
const segLen = (a, b) => Math.hypot(b[0] - a[0], b[1] - a[1]);
function measureText() {
  const p = measure.pts; if (p.length < 2) return '';
  let sum = 0; for (let i = 1; i < p.length; i++) sum += segLen(p[i - 1], p[i]);
  let t = p.length === 2 ? num(sum, 2) + ' m' : T.path + ' ' + num(sum, 2) + ' m';
  if (p.length >= 3) {
    let a2 = 0; p.forEach(([x, y], i) => { const [x2, y2] = p[(i + 1) % p.length]; a2 += x * y2 - x2 * y; });
    t += ' · ' + T.area + ' ' + num(Math.abs(a2) / 2, 1) + ' m²';
  }
  return t;
}
/** measure points -> screen positions in a W x H picture ([x, y, inFront]) */
function measureScreen(W, H) {
  return measure.pts.map(([x, y]) => {
    _v.set(x - S.CX, sceneY(groundAt(x, y)) + 0.05, y - S.CZ).project(camera);
    return [((_v.x + 1) / 2) * W, ((1 - _v.y) / 2) * H, _v.z < 1];
  });
}
function drawMeasure() {
  const svg = $('#msvg'), read = $('#mread');
  svg.hidden = read.hidden = !(measure.on && measure.pts.length);
  if (svg.hidden) return;
  const P = measureScreen(innerWidth, innerHeight);
  let h = '';
  for (let i = 1; i < P.length; i++) {
    if (!P[i][2] || !P[i - 1][2]) continue;
    h += `<line x1="${P[i - 1][0]}" y1="${P[i - 1][1]}" x2="${P[i][0]}" y2="${P[i][1]}"/>`;
    h += `<text x="${(P[i - 1][0] + P[i][0]) / 2}" y="${(P[i - 1][1] + P[i][1]) / 2 - 6}">${num(segLen(measure.pts[i - 1], measure.pts[i]), 2)} m</text>`;
  }
  P.forEach((q) => { if (q[2]) h += `<circle cx="${q[0]}" cy="${q[1]}" r="4"/>`; });
  svg.innerHTML = h;
  $('#mtext').textContent = measureText() || '…';
}

/* ---------------------------------------------------------------- highlight: one species, one zone, one planting season */
let hlOn = false;
function setHighlight(label, fn, fly) {
  hlOn = !!fn;
  plants.setHighlight(fn || null);
  plants.layout(STAGES[growth].f, month);
  $('#hl').hidden = !fn;
  if (fn) { $('#hltext').textContent = T.highlighted + label; if (fly) focusOn(plants.pointsOf(fn)); }
  else document.querySelectorAll('#costs tr.on').forEach((r) => r.classList.remove('on'));
  requestRender();
}
/** bring a set of scene points into view: recentre the plan, or fly the orbit camera over them */
function focusOn(pts) {
  if (!pts.length || walk.on) return;
  const box = new THREE.Box3().setFromPoints(pts), c = box.getCenter(new THREE.Vector3());
  const r = pts.reduce((m, p) => Math.max(m, Math.hypot(p.x - c.x, p.z - c.z)), 0);
  if (plan.on) {
    const m = SAFE(), free = Math.min(innerWidth - m.left - m.right, innerHeight - m.top - m.bottom);
    fitPlan();
    plan.mpp = Math.max(0.02, Math.min(plan.mpp, (2 * r + 12) / free));
    plan.cx = c.x; plan.cz = c.z; planMoved = true; applyCam(); updateOverlay(); return;
  }
  const from = { azim, polar, dist, t: target.clone() };
  tween = { t0: performance.now(), dur: 800, from, to: { azim, polar: Math.min(polar, 1.0), dist: Math.max(26, r * 2.5 + 20), t: c } };
  markView(null);
}

/* ---------------------------------------------------------------- sun: real position for the month and the hour */
let sunOn = true, hour = 13, dayTimer = 0, NORTH = 0;
const STUDIO = new THREE.Vector3(-0.42, 0.78, 0.46).normalize();       // from the south-south-west, high
const smooth = (a, b, x) => { const t = Math.max(0, Math.min(1, (x - a) / (b - a))); return t * t * (3 - 2 * t); };
const SUN_HIGH = new THREE.Color(0xfff0d8), SUN_LOW = new THREE.Color(0xffb26a);
function applySun() {
  const site = DATA.meta.site, dir = STUDIO.clone();
  let k = 1, low = 0, sky = 1, note = T.studio;
  if (sunOn && site) {
    const doy = dayOfYear(month), off = clockOffset(site, month);
    const p = sunPosition(site.lat, site.lon, doy, hour - off);
    const a = p.az + NORTH, ce = Math.cos(p.el);
    dir.set(Math.sin(a) * ce, Math.max(0.02, Math.sin(p.el)), -Math.cos(a) * ce).normalize();
    k = smooth(-0.01, 0.14, p.el); low = 1 - smooth(0.05, 0.5, p.el); sky = 0.38 + 0.62 * smooth(-0.1, 0.2, p.el);
    const t = sunTimes(site.lat, site.lon, doy);
    note = '21 ' + MONTHS_OF[month - 1] + (t ? ' · ' + T.sunrise + ' ' + clock(t.rise + off) + ' · ' + T.sunset + ' ' + clock(t.set + off) : '')
         + (p.el <= 0 ? ' · ' + T.night : ' · ' + Math.round(p.el * 180 / Math.PI) + '°');
  }
  sun.position.copy(dir).multiplyScalar(140); sun.target.position.set(0, 0, 0);
  // a model, not a photometer: lift a low sun so the ground stays readable and its long shadows show
  sun.intensity = 2.45 * k * Math.min(1.5, STUDIO.y / Math.max(dir.y, 0.2)); sun.color.copy(SUN_HIGH).lerp(SUN_LOW, low);
  sun.castShadow = k > 0.02;
  hemi.intensity = HEMI * sky;
  if (scene.environment) scene.environmentIntensity = 0.42 * sky;
  $('#sunval').textContent = $('#t-hour').textContent = sunOn && site ? clock(hour) : '—';
  $('#sunmeta').textContent = note;
  requestRender();
}
function setDayPlaying(on) {
  clearInterval(dayTimer); dayTimer = 0;
  $('#dayplay').textContent = on ? '❚❚' : '▶';
  if (on) dayTimer = setInterval(() => {
    const site = DATA.meta.site, t = site && sunTimes(site.lat, site.lon, dayOfYear(month)), off = site ? clockOffset(site, month) : 0;
    const lo = t ? Math.floor((t.rise + off) * 4) / 4 - 0.5 : 4, hi = t ? Math.ceil((t.set + off) * 4) / 4 + 0.5 : 22;
    hour = hour + 0.25 > hi || hour < lo ? lo : hour + 0.25;
    $('#hour').value = hour; applySun();
  }, 140);
}

/* ---------------------------------------------------------------- picture: the current view as a PNG */
function savePNG() {
  const W = innerWidth, H = innerHeight, want = plan.on ? 3 : 2;
  const cap = Math.min(8192, renderer.capabilities.maxTextureSize);
  const k = Math.max(1, Math.min(want, Math.floor((cap / Math.max(W, H)) * 4) / 4));
  const pr = renderer.getPixelRatio();
  exporting = true;
  const keep = { ...plan };
  if (plan.on && !planMoved) fitPlan();              // the untouched plan fills the sheet; a panned or zoomed one stays as framed
  renderer.setPixelRatio(k); renderer.setSize(W, H);
  applyCam(); camera.updateMatrixWorld();
  renderer.render(scene, camera);
  const out = document.createElement('canvas'); out.width = Math.round(W * k); out.height = Math.round(H * k);
  const c = out.getContext('2d');
  c.drawImage(renderer.domElement, 0, 0, out.width, out.height);     // same task as the render: the buffer is still there
  c.textBaseline = 'middle'; c.textAlign = 'center';
  const serif = "Georgia, 'Iowan Old Style', serif";
  if (plan.on && layerOn.labels) {
    const codes = plan.mpp / k < 0.045;
    labels.forEach((l) => {
      if (l.cls === 'plant' && !codes) return;
      _v.copy(l.p).project(camera);
      const x = ((_v.x + 1) / 2) * out.width, y = ((1 - _v.y) / 2) * out.height;
      if (l.cls === 'zone') {
        const r = 6.5 * k;
        c.fillStyle = '#a02c17'; c.beginPath(); c.arc(x, y, r, 0, 6.2832); c.fill();
        c.fillStyle = '#fcf9f2'; c.font = `600 ${8.5 * k}px ${serif}`; c.fillText(l.e.textContent, x, y + 0.5 * k);
      } else {
        c.font = `600 ${5.2 * k}px ${serif}`;
        const w = c.measureText(l.e.textContent).width + 3 * k;
        c.fillStyle = 'rgba(252,249,242,.85)'; c.fillRect(x - w / 2, y - 3.6 * k, w, 7.2 * k);
        c.fillStyle = '#211b14'; c.fillText(l.e.textContent, x, y + 0.3 * k);
      }
    });
  }
  if (measure.on && measure.pts.length) {
    const P = measureScreen(out.width, out.height);
    c.strokeStyle = '#a02c17'; c.fillStyle = '#a02c17'; c.lineWidth = 1.6 * k; c.font = `600 ${11 * k}px ${serif}`;
    for (let i = 1; i < P.length; i++) {
      c.beginPath(); c.moveTo(P[i - 1][0], P[i - 1][1]); c.lineTo(P[i][0], P[i][1]); c.stroke();
      c.fillText(num(segLen(measure.pts[i - 1], measure.pts[i]), 2) + ' m', (P[i - 1][0] + P[i][0]) / 2, (P[i - 1][1] + P[i][1]) / 2 - 8 * k);
    }
  }
  // caption, and on the plan a scale bar and a north arrow
  const cap2 = (DATA.meta.ui && DATA.meta.ui.title || document.title) + ' · ' + MONTHS[month - 1] + ' · ' + STAGES[growth].label;
  c.font = `600 ${12 * k}px ${serif}`; c.textAlign = 'left';
  const tw = c.measureText(cap2).width;
  c.fillStyle = 'rgba(252,249,242,.9)'; c.fillRect(10 * k, out.height - 34 * k, tw + 20 * k, 24 * k);
  c.fillStyle = '#211b14'; c.fillText(cap2, 20 * k, out.height - 22 * k);
  if (plan.on) {
    const nice = [1, 2, 5, 10, 20, 50].find((m) => m / plan.mpp >= 70) || 50, len = (nice / plan.mpp) * k;
    const x0 = out.width - 20 * k - len, y0 = out.height - 22 * k;
    c.fillStyle = 'rgba(252,249,242,.9)'; c.fillRect(x0 - 44 * k, y0 - 26 * k, len + 54 * k, 40 * k);
    c.strokeStyle = '#211b14'; c.lineWidth = 1.5 * k; c.beginPath();
    c.moveTo(x0, y0 - 4 * k); c.lineTo(x0, y0 + 2 * k); c.lineTo(x0 + len, y0 + 2 * k); c.lineTo(x0 + len, y0 - 4 * k); c.stroke();
    c.fillStyle = '#211b14'; c.textAlign = 'center'; c.font = `${10 * k}px ${serif}`; c.fillText(nice + ' m', x0 + len / 2, y0 - 9 * k);
    c.save(); c.translate(x0 - 24 * k, y0 - 6 * k); c.rotate(NORTH);
    c.fillStyle = '#a02c17'; c.beginPath(); c.moveTo(0, -14 * k); c.lineTo(5 * k, 6 * k); c.lineTo(0, 2 * k); c.lineTo(-5 * k, 6 * k); c.closePath(); c.fill();
    c.restore(); c.font = `600 ${8 * k}px ${serif}`; c.fillStyle = '#211b14'; c.fillText('N', x0 - 24 * k, y0 + 12 * k);
  }
  exporting = false;
  Object.assign(plan, keep);
  renderer.setPixelRatio(pr); renderer.setSize(W, H);
  applyCam(); updateOverlay();
  out.toBlob((blob) => {
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'garden-' + (currentView || 'view') + '-' + String(month).padStart(2, '0') + '.png';
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 4000);
  }, 'image/png');
}

/* ---------------------------------------------------------------- shopping list: pieces and cost by zone or by year */
let costMode = 'zone', CUR = '', costList = [];
/** the shopping list as a spreadsheet: semicolons and a BOM, which is what a Polish Excel opens cleanly */
function saveCSV() {
  const q = (v) => { const t = v == null ? '' : String(v).replace(/"/g, '""'); return /[;"\n]/.test(t) ? '"' + t + '"' : t; };
  const dec = (v) => (v == null ? '' : String(Math.round(v * 100) / 100).replace('.', ','));
  const rows = [T.csv.head];
  costList.forEach((g) => [...g.idx].forEach((pi) => {
    const p = DATA.plants[pi];
    rows.push([g.label, p.id, p.zone, p.latin, p.polish, p.cultivar, p.qty, p.size, p.when, p.year || '', p.price,
               dec(p.priceLo != null ? p.qty * p.priceLo : null), dec(p.priceHi != null ? p.qty * p.priceHi : null)]);
  }));
  const I = DATA.irrigation;
  if (I) [[T.csv.irr, I.bom], [T.csv.irrOpt, I.bomOptional]].forEach(([label, list]) => (list || []).forEach((b) =>
    rows.push([label, '', '', '', b.item, '', b.qty + ' ' + b.unit, '', '', '', dec(b.lo) + '–' + dec(b.hi), dec(b.qty * b.lo), dec(b.qty * b.hi)])));
  const blob = new Blob(['\ufeff' + rows.map((r) => r.map(q).join(';')).join('\r\n')], { type: 'text/csv;charset=utf-8' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob); a.download = T.csv.name + '-' + costMode + '.csv';
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 4000);
}

/* ---------------------------------------------------------------- irrigation: sections in the panel, one in focus on the ground */
function showIrrigationInfo(s) {
  const I = T.irr, nf = (v) => Math.round(v).toLocaleString('pl-PL');
  $('#i-code').textContent = I.section + s.id + (s.optional ? ' · ' + I.optional : '') + (s.temporary ? ' · ' + I.temporary(s.temporary) : '');
  $('#i-name').textContent = s.name;
  $('#i-lat').textContent = s.source === 'mains' ? I.mains : I.tank;
  const rows = s.heads.length ? [[I.heads, s.heads.length + (s.groups > 1 ? ' (' + s.groups + ' grup)' : '')]]
                              : [[I.line, num(s.lineM, 0) + ' m'], [I.emitters, s.emitters], [I.feeds, num(s.feedM || 0, 0) + ' m']];
  rows.push([I.flow, nf(s.flow) + ' l/h'], [I.demand, nf(s.demand) + I.perWeek], [I.run, s.minutes + I.minWeek]);
  [['trench', I.trench], ['sleeve', I.sleeve], ['surface', I.surface]].forEach(([k, l]) => { if (s.trunkM[k]) rows.push([l, num(s.trunkM[k], 0) + ' m']); });
  $('#i-dl').innerHTML = rows.map((r) => '<dt>' + r[0] + '</dt><dd>' + r[1] + '</dd>').join('');
  $('#i-where').textContent = s.note || '';
  $('#i-notes').textContent = s.plants.length ? I.plants + s.plants.join(', ') : '';
  $('#info').hidden = false;
}
function focusIrrigation(id) {
  const I = DATA.irrigation, s = id && I.sections.find((q) => q.id === id);
  irrFocus = s ? id : null;
  document.querySelectorAll('#irr tr[data-s]').forEach((r) => r.classList.toggle('on', r.dataset.s === irrFocus));
  if (s) {
    if (!layerOn.irrigation) {
      const k = LAYER_LABELS.findIndex((q) => q[0] === 'irrigation'), cb = [...$('#layers').querySelectorAll('input')][k];
      if (cb) cb.checked = true; setLayer('irrigation', true);
    }
    const ids = new Set(s.plants);
    showIrrigationInfo(s);
    if (ids.size) setHighlight(s.id + ' · ' + s.name, (b) => ids.has(b.p.id), true); else setHighlight(null);
  } else { $('#info').hidden = true; setHighlight(null); }
  paintGround();
}
function renderIrrigation() {
  const I = DATA.irrigation, box = $('#irrbox');
  if (!I) { box.remove(); return; }
  const nf = (v) => Math.round(v).toLocaleString('pl-PL'), B = I.budget, L = T.irr;
  $('#irr').innerHTML = '<table>' + I.sections.map((s) =>
    '<tr data-s="' + s.id + '" title="' + s.name.replace(/"/g, '') + '"><td><span class="swatch" style="background:' + s.color + '"></span>' + s.id + ' ' + s.name + '</td><td>' +
    nf(s.demand) + ' l</td><td>' + s.minutes + ' min</td></tr>').join('') + '</table>' +
    '<div class="stat"><span>' + L.week + '</span><b>' + nf(B.week) + L.perWeek + '</b></div>' +
    '<div class="stat"><span>' + L.autonomy + '</span><b>' + num(B.autonomyDays) + L.days + '</b></div>' +
    '<div class="stat"><span>' + L.roof + '</span><b>' + nf(B.roofWeek) + L.perWeek + '</b></div>' +
    '<div class="stat"><span>' + L.lawn + '</span><b>' + nf(B.lawnWeek) + L.perWeek + '</b></div>';
  $('#irr').querySelectorAll('tr[data-s]').forEach((tr) => tr.addEventListener('click', () => focusIrrigation(tr.dataset.s === irrFocus ? null : tr.dataset.s)));
}
function renderCosts() {
  const groups = new Map();
  DATA.plants.forEach((p, pi) => {
    const key = costMode === 'zone' ? p.zone : (p.year || 0);
    if (!groups.has(key)) {
      const z = costMode === 'zone' && DATA.zones.find((q) => q.id === key);
      groups.set(key, { key, label: costMode === 'zone' ? key + (z ? ' — ' + z.name : '') : (key ? String(key) : T.noDate), qty: 0, lo: 0, hi: 0, idx: new Set() });
    }
    const g = groups.get(key);
    g.qty += p.qty || 0; g.idx.add(pi);
    if (p.priceLo != null) { g.lo += p.qty * p.priceLo; g.hi += p.qty * p.priceHi; }
  });
  const list = [...groups.values()].sort((a, b) => costMode === 'zone' ? String(a.key).localeCompare(String(b.key)) : (a.key || 9999) - (b.key || 9999));
  const range = (g) => g.hi ? (money(g.lo) === money(g.hi) ? money(g.lo) : money(g.lo) + '–' + money(g.hi)) + ' ' + CUR : '—';
  const tot = list.reduce((a, g) => ({ qty: a.qty + g.qty, lo: a.lo + g.lo, hi: a.hi + g.hi }), { qty: 0, lo: 0, hi: 0 });
  $('#costs').innerHTML = '<table>' + list.map((g, i) =>
    '<tr data-g="' + i + '" title="' + g.label.replace(/"/g, '') + '"><td>' + g.label + '</td><td>' + g.qty + '</td><td>' + range(g) + '</td></tr>').join('') +
    '<tr class="sum"><td>' + T.sum + '</td><td>' + tot.qty + '</td><td>' + range(tot) + '</td></tr>' +
    (DATA.irrigation ? '<tr class="extra"><td>' + T.irr.cost + '</td><td></td><td>' + range({ lo: DATA.irrigation.cost[0], hi: DATA.irrigation.cost[1] }) + '</td></tr>' +
      (DATA.irrigation.costOptional[1] ? '<tr class="extra"><td>' + T.irr.costOpt + '</td><td></td><td>' + range({ lo: DATA.irrigation.costOptional[0], hi: DATA.irrigation.costOptional[1] }) + '</td></tr>' : '') : '') +
    '</table><p class="credit">' + T.costNote + '</p>';
  costList = list;
  $('#costs').querySelectorAll('tr[data-g]').forEach((tr) => tr.addEventListener('click', () => {
    const g = list[+tr.dataset.g], was = tr.classList.contains('on');
    $('#info').hidden = true;
    setHighlight(was ? null : g.label, was ? null : (b) => g.idx.has(b.plantIdx), true);
    if (!was) tr.classList.add('on');
  }));
  document.querySelectorAll('[data-cost]').forEach((b) => b.classList.toggle('on', b.dataset.cost === costMode));
}

/* ---------------------------------------------------------------- season + growth */
function applySeason() {
  plants.layout(STAGES[growth].f, month);
  built.setMonth(month, DATA.looks);
  paintGround();
  applySun();
  $('#monthval').textContent = $('#t-month').textContent = MONTHS[month - 1];
  $('#month').value = month;
  renderCalendar();
  requestRender();
}
let sunMap = null, sunMapKey = '';
function paintGround() {
  if (layerOn.sunmap && DATA.meta.site) {
    const key = month + ':' + growth + ':' + phase;
    if (key !== sunMapKey) { sunMap = sunHours(DATA, NORTH, month, plants.shadowBodies(STAGES[growth].f, month)); sunMapKey = key; }
    $('#sunlegend').hidden = false;
    $('#sunlegend-note').textContent = T.sunmapNote('21 ' + MONTHS_OF[month - 1], STAGES[growth].label);
  } else $('#sunlegend').hidden = true;
  ground.paint({ month, ortho: layerOn.ortho, gas: layerOn.gas, slopes: layerOn.slopes,
                 zones: layerOn.zones ? zonesOn : new Set(), looks: DATA.looks,
                 sunmap: layerOn.sunmap && sunMap ? sunMap.canvas : null,
                 irrigation: (layerOn.irrigation || layerOn.hose) && DATA.irrigation
                   ? { focus: layerOn.irrigation ? irrFocus : '-', hose: layerOn.hose, lines: layerOn.irrigation } : null });
  if (ground.context) ground.context.visible = layerOn.ortho && !!ground.ortho;
  requestRender();
}
function renderCalendar() {
  const cal = plants.calendar(month);
  const chip = (it) => '<button class="chip" type="button" data-pi="' + it.plantIdx + '" data-look="' + it.key.replace(/"/g, '') + '" title="' + [...it.ids].join(', ') + '">' +
    '<span class="swatch" style="background:' + it.colour + '"></span>' + it.name + ' <em>' + [...it.ids].join(' ') + '</em></button>';
  const block = (title, map) => map.size ? '<div class="cal-h">' + title + '</div>' + [...map.values()].map(chip).join('') : '';
  const html = block(T.flowers, cal.flowers) + block(T.fruit, cal.fruit) + block(T.autumnHead, cal.autumn);
  $('#calendar').innerHTML = html || '<p class="quiet">' + T.nothing + '</p>';
  $('#cal-title').textContent = T.inMonth + MONTHS_GEN[month - 1];
  $('#calendar').querySelectorAll('.chip').forEach((c) => c.addEventListener('click', () => {
    const p = DATA.plants[+c.dataset.pi]; if (!p) return;
    const look = c.dataset.look, v = p.variants.find((q) => q.look === look);
    showInfo(p, v ? { v, ptIdx: -1 } : null);
    setHighlight(c.textContent.replace(/\s+[A-Z]\d+( [A-Z]\d+)*$/, '').trim(), (b) => b.v.look === look, true);
  }));
}
let playTimer = 0;
function setPlaying(on) {
  clearInterval(playTimer); playTimer = 0;
  $('#play').textContent = on ? '❚❚' : '▶';
  $('#play').setAttribute('aria-label', on ? T.pause : T.play);
  if (on) playTimer = setInterval(() => { month = month % 12 + 1; applySeason(); }, 1100);
}

/* ---------------------------------------------------------------- UI */
const LAYER_SWATCH = { plants: '#5c7a3a', buildings: '#ece5d8', slopes: '#7c4f22', gas: '#b03a1a', fences: '#6b7566',
                       site: '#e0a52c', zones: '#b9d09a', ortho: '#9aa583', labels: '#a02c17',
                       irrigation: '#2f7fb8', hose: '#7fb6dc', sunmap: '#e9b949' };
let LAYER_LABELS = [];
function setLayer(key, on) {
  layerOn[key] = on;
  if (key === 'plants') plants.group.visible = on;
  else if (key === 'buildings') built.layers.buildings.visible = on;
  else if (key === 'fences') built.layers.fences.visible = on;
  else if (key === 'site') { built.layers.site.visible = on; built.layers.structures.visible = on; }
  else if (key === 'labels') updateOverlay();
  else {
    if (key === 'irrigation') built.layers.irrigation.visible = on;
    paintGround();
  }
  requestRender();
}
function buildUI(d) {
  const ui = d.meta.ui || {};
  CUR = ui.currency || '';
  if (ui.title) { document.title = ui.title; $('h1').textContent = ui.title; $('#load .t').textContent = ui.title; }
  LAYER_LABELS = Object.keys(LAYER_SWATCH)
    .filter((k) => (k !== 'irrigation' && k !== 'hose' || d.irrigation) && (k !== 'sunmap' || d.meta.site))
    .filter((k) => (k !== 'gas' || (d.pipes || []).length) && (k !== 'slopes' || (d.lines || []).some((l) => l.kind === 'crest') || (d.slopes || []).length))
    .map((k) => [k, (ui.layers && ui.layers[k]) || T.layers[k], LAYER_SWATCH[k]]);

  // view buttons: overview, plan, one per eye-level view of the scene, and the walk
  const VB = $('#views');
  [['aerial', T.aerial], ['plan', T.plan], ...(d.views || []).map((v) => [v.id, v.label]), ['walk', T.walk]].forEach(([id, label]) => {
    const b = document.createElement('button');
    b.className = 'btn'; b.type = 'button'; b.dataset.view = id; b.textContent = label;
    VB.appendChild(b);
  });

  const L = $('#layers');
  LAYER_LABELS.forEach(([key, label, colour]) => {
    if (key === 'ortho' && !d.ortho) return;
    const row = document.createElement('label');
    row.className = 'row';
    row.innerHTML = '<input type="checkbox"' + (layerOn[key] ? ' checked' : '') + '><span class="sw" style="background:' + colour + '"></span><span>' + label + '</span>';
    row.querySelector('input').addEventListener('change', (e) => setLayer(key, e.target.checked));
    L.appendChild(row);
  });

  const Z = $('#zones');
  d.zones.forEach((z) => {
    const row = document.createElement('label');
    row.className = 'row zone'; row.title = z.desc;
    const has = z.polys.length > 0;
    row.innerHTML = '<input type="checkbox"' + (has ? '' : ' disabled') + '><span class="sw" style="background:' + z.color + '"></span><span>' + z.id + ' — ' + z.name + '</span>';
    row.querySelector('input').addEventListener('change', (e) => {
      if (e.target.checked) zonesOn.add(z.id); else zonesOn.delete(z.id);
      layerOn.zones = zonesOn.size > 0;
      const master = [...$('#layers').querySelectorAll('input')][LAYER_LABELS.findIndex((q) => q[0] === 'zones')];
      if (master) master.checked = layerOn.zones;
      paintGround();
    });
    Z.appendChild(row);
  });
  // the master "Strefy" switch turns every zone with an outline on or off
  const zi = LAYER_LABELS.findIndex((q) => q[0] === 'zones');
  const master = [...L.querySelectorAll('input')][zi];
  master.addEventListener('change', (e) => {
    zonesOn.clear();
    Z.querySelectorAll('input').forEach((cb, i) => {
      const z = d.zones[i]; if (!z.polys.length) return;
      cb.checked = e.target.checked; if (e.target.checked) zonesOn.add(z.id);
    });
    paintGround();
  }, true);

  const c = d.meta.counts;
  $('#stats').innerHTML =
    '<div class="stat"><span>' + T.entries + '</span><b>' + c.entries + '</b></div>' +
    '<div class="stat"><span>' + T.positions + '</span><b>' + c.positions + '</b></div>' +
    '<div class="stat"><span>' + T.total + '</span><b>' + c.pieces + '</b></div>' +
    '<div class="stat"><span>' + T.plateau + '</span><b>' + num(d.meta.plateau, 2) + T.asl + '</b></div>' +
    (d.ortho && ui.credit ? '<p class="credit">' + ui.credit + '</p>' : '');

  const yr = $('#year');
  yr.value = growth;
  yr.addEventListener('input', () => { growth = +yr.value; $('#yearval').textContent = $('#t-growth').textContent = STAGES[growth].label; plants.layout(STAGES[growth].f, month); if (layerOn.sunmap) paintGround(); requestRender(); });
  $('#yearval').textContent = $('#t-growth').textContent = STAGES[growth].label;
  // planting stages: one stop per planting year in the plan, and "everything"
  const years = [...new Set(d.plants.map((p) => p.year).filter(Boolean))].sort();
  const ph = $('#phase');
  if (years.length < 2) $('#phasebox').remove();
  else {
    ph.max = years.length; ph.value = years.length;
    $('#phaseticks').innerHTML = years.map((y) => '<span>' + y + '</span>').join('') + '<span>' + T.all + '</span>';
    const show = () => { $('#phaseval').textContent = phase ? T.upTo + phase : T.all; };
    ph.addEventListener('input', () => {
      phase = +ph.value < years.length ? years[+ph.value] : null;
      plants.setVisible(phase ? (b) => !b.p.year || b.p.year <= phase : null);
      plants.layout(STAGES[growth].f, month); show(); paintGround();
    });
    show();
  }
  // phone: one slider at a time, the other two show their value on their tab
  document.querySelectorAll('#dock .tabs button').forEach((b) => b.addEventListener('click', () => {
    $('#dock').dataset.tab = b.dataset.tab; layoutVars(); applyCam();
  }));

  const mo = $('#month');
  mo.addEventListener('input', () => { month = +mo.value; setPlaying(false); applySeason(); });
  $('#play').addEventListener('click', () => setPlaying(!playTimer));
  addEventListener('keydown', (e) => {
    if (e.target.closest && e.target.closest('input[type=checkbox]')) return;
    if (e.key === 'Escape') { if (measure.on) { measure.pts = []; updateOverlay(); } else if (hlOn) setHighlight(null); return; }
    if (walk.on && e.target.tagName !== 'INPUT') { keys.add(e.key.length === 1 ? e.key.toLowerCase() : e.key); if (e.key.startsWith('Arrow')) e.preventDefault(); return; }
    if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
      if (e.target.type === 'range') return;                       // sliders handle their own arrows
      month = (month + (e.key === 'ArrowRight' ? 0 : 10)) % 12 + 1; setPlaying(false); applySeason();
    }
  });

  document.querySelectorAll('[data-view]').forEach((b) => b.addEventListener('click', () => goView(b.dataset.view)));
  $('#infoclose').addEventListener('click', () => { $('#info').hidden = true; setHighlight(null); });
  $('#hlclose').addEventListener('click', () => setHighlight(null));
  addEventListener('keyup', (e) => keys.delete(e.key.length === 1 ? e.key.toLowerCase() : e.key));
  addEventListener('blur', () => keys.clear());

  // sun
  const hr = $('#hour'), so = $('#sunon');
  if (!d.meta.site) { so.checked = sunOn = false; so.disabled = true; }
  hr.value = hour; hr.disabled = !sunOn; $('#dayplay').disabled = !sunOn;
  hr.addEventListener('input', () => { hour = +hr.value; setDayPlaying(false); applySun(); });
  so.addEventListener('change', () => { sunOn = so.checked; hr.disabled = !sunOn; $('#dayplay').disabled = !sunOn; setDayPlaying(false); applySun(); });
  $('#dayplay').addEventListener('click', () => setDayPlaying(!dayTimer));

  // tools
  $('#b-measure').addEventListener('click', () => setMeasure(!measure.on));
  $('#mclear').addEventListener('click', () => { measure.pts = []; updateOverlay(); });
  $('#b-png').addEventListener('click', savePNG);
  $('#b-csv').addEventListener('click', saveCSV);
  renderIrrigation();
  $('#sunramp').style.background = 'linear-gradient(90deg,' + RAMP.map(([h, c]) => c + ' ' + (h / RAMP[RAMP.length - 1][0]) * 100 + '%').join(',') + ')';
  $('#sunticks').innerHTML = RAMP.map(([h], i) => '<span>' + h + (i === RAMP.length - 1 ? '+ h' : '') + '</span>').join('');
  document.querySelectorAll('[data-cost]').forEach((b) => b.addEventListener('click', () => { costMode = b.dataset.cost; setHighlight(null); renderCosts(); }));
  renderCosts();

  // walk stick (touch and mouse): a thumb pad, vector in [-1, 1]
  const pad = $('#stick'), knob = pad.firstElementChild;
  const move = (e) => {
    const r = pad.getBoundingClientRect(), R = r.width / 2;
    let x = (e.clientX - r.left - R) / R, y = (e.clientY - r.top - R) / R; const L = Math.hypot(x, y);
    if (L > 1) { x /= L; y /= L; }
    stick.x = x; stick.y = y; knob.style.transform = `translate(${x * R * 0.55}px, ${y * R * 0.55}px)`;
  };
  pad.addEventListener('pointerdown', (e) => { pad.setPointerCapture(e.pointerId); stick.on = true; move(e); });
  pad.addEventListener('pointermove', (e) => { if (stick.on) move(e); });
  const stop = () => { stick.on = false; stick.x = stick.y = 0; knob.style.transform = ''; };
  pad.addEventListener('pointerup', stop); pad.addEventListener('pointercancel', stop);
  $('#menubtn').addEventListener('click', () => $('#panel').classList.toggle('open'));
}

/* ---------------------------------------------------------------- build + go */
function buildScene(d) {
  DATA = d;
  setupSite(d);
  NORTH = ((d.meta.site && d.meta.site.north) || 0) * Math.PI / 180;    // true north, clockwise from the site's -y axis
  const R = S.plotRadius + 10;
  Object.assign(sun.shadow.camera, { left: -R, right: R, top: R, bottom: -R, near: 20, far: 300 });
  sun.shadow.camera.updateProjectionMatrix();

  // AO only around the plot: the context ring is flat photo, and its faded-out edge would otherwise
  // pick up occlusion against the empty background
  if (gtao) {
    const R = S.plotRadius + 25;
    gtao.setSceneClipBox(new THREE.Box3(new THREE.Vector3(-R, -30, -R), new THREE.Vector3(R, 40, R)));
  }

  ground = new Ground(d, renderer);
  scene.add(ground.mesh);
  if (ground.context) scene.add(ground.context);
  pickables.length = 0;

  built = new Built(d);
  Object.values(built.layers).forEach((g) => scene.add(g));
  pickables.push(...built.pickables);

  plants = new Plants(d);
  scene.add(plants.group);
  pickables.push(...plants.pickables);

  (d.views || []).forEach((v) => { VIEWS[v.id] = eyeView(v.from, v.to, v.step || 0); });
  // where a walk cannot go: through the house and through built volumes
  solids = d.buildings.filter((q) => q.kind === 'house').map((q) => q.poly).concat((d.structures || []).map((q) => q.poly));
  buildLabels();
}

addEventListener('resize', () => {
  layoutVars();
  renderer.setSize(innerWidth, innerHeight);
  if (composer) { composer.setSize(innerWidth, innerHeight); }
  if (currentView && VIEWS[currentView] && !walk.on) goView(currentView, false); else applyCam();
  updateOverlay();
});

/* walking: keys or the thumb pad move the eye over the ground, 3 m/s, never through a wall */
const keys = new Set(), stick = { on: false, x: 0, y: 0 };
let solids = [], lastT = 0;
function stepWalk(now) {
  const dt = Math.min(0.1, (now - lastT) / 1000); lastT = now;
  if (!walk.on) return;
  let f = (keys.has('w') || keys.has('ArrowUp') ? 1 : 0) - (keys.has('s') || keys.has('ArrowDown') ? 1 : 0) - stick.y;
  let r = (keys.has('d') || keys.has('ArrowRight') ? 1 : 0) - (keys.has('a') || keys.has('ArrowLeft') ? 1 : 0) + stick.x;
  if (Math.abs(f) < 0.05 && Math.abs(r) < 0.05) return;
  const L = Math.hypot(f, r); if (L > 1) { f /= L; r /= L; }
  const v = (keys.has('Shift') ? 7 : 3) * dt, c = Math.cos(walk.yaw), s = Math.sin(walk.yaw);
  const g = S.G, free = (x, y) => x > g.x0 + 1 && y > g.y0 + 1 && x < g.x0 + (g.nx - 1) * g.step - 1 && y < g.y0 + (g.ny - 1) * g.step - 1
    && !solids.some((p) => pointInPoly(x, y, p));
  const nx = walk.x + (c * f - s * r) * v, ny = walk.y + (s * f + c * r) * v;
  if (free(nx, ny)) { walk.x = nx; walk.y = ny; }
  else if (free(nx, walk.y)) walk.x = nx;                           // slide along the wall
  else if (free(walk.x, ny)) walk.y = ny;
  applyCam();
}

function frame(now) {
  requestAnimationFrame(frame);
  stepTween(now);
  stepWalk(now);
  if (!dirty) return;
  dirty = false;
  if (tween) dirty = true;
  if (composer && !plan.on) {
    try { composer.render(); } catch (e) { console.warn('garden: AO failed, plain render from now on', e); composer = null; renderer.render(scene, camera); }
  } else renderer.render(scene, camera);
  updateOverlay();
}

fetch('garden-scene.json', { cache: 'default' })
  .then((r) => { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
  .then((d) => {
    buildScene(d);
    buildUI(d);
    layoutVars();
    applySeason();
    goView('aerial', false);
    $('#load').hidden = true;
    $('#sub').textContent = T.subtitle(d.meta.counts, d.meta.version);
    requestAnimationFrame(frame);
    window.__gardenReady = true;
    ground.loadOrtho(() => paintGround());
  })
  .catch((err) => {
    console.error(err);
    if (window.__gardenFail) window.__gardenFail(err.message + (err.stack ? ' — ' + String(err.stack).split('\n')[1] : ''));
    else $('#loadmsg').textContent = T.loadFail + err.message;
  });
