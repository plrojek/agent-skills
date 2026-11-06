import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";
import { EffectComposer } from "three/addons/postprocessing/EffectComposer.js";
import { RenderPass } from "three/addons/postprocessing/RenderPass.js";
import { UnrealBloomPass } from "three/addons/postprocessing/UnrealBloomPass.js";
import { OutputPass } from "three/addons/postprocessing/OutputPass.js";
import { createLabels } from "./labels.js";
import { palette } from "./ui.js";

const GOLD = 0xf6d49a;
const vector = node => new THREE.Vector3(node.x, node.y, node.z);

function disposeGroup(group) {
  const geometries = new Set(), materials = new Set();
  group.traverse(object => {
    if (object.geometry) geometries.add(object.geometry);
    for (const material of [].concat(object.material || [])) materials.add(material);
    if (object.isInstancedMesh) object.dispose();
  });
  for (const geometry of geometries) geometry.dispose();
  for (const material of materials) material.dispose();
  group.clear();
}

export function createScene(host, { portraits, onSelect, onCamera, onFailure, insets, obstructions }) {
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false, powerPreference: "high-performance" });
  renderer.setPixelRatio(Math.min(devicePixelRatio || 1, 2.5));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.15;
  const canvas = renderer.domElement;
  canvas.className = "atlas-canvas";
  canvas.tabIndex = 0;
  canvas.setAttribute("role", "img");
  canvas.setAttribute("aria-label", "Atlas rodziny w trzech wymiarach. Przeciągnij, aby obrócić, kółko przybliża. Wybierz punkt lub wyszukaj dwie osoby. Pełna trasa jest również dostępna jako lista.");
  host.prepend(canvas);
  const world = new THREE.Scene();
  const content = new THREE.Group();
  world.add(content);
  const background = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), new THREE.ShaderMaterial({
    depthWrite: false, depthTest: false,
    vertexShader: "varying vec2 vUv; void main(){vUv=uv;gl_Position=vec4(position.xy,1.0,1.0);}",
    fragmentShader: `varying vec2 vUv;
      void main(){
        vec3 base=vec3(0.012,0.019,0.038);
        float pool=exp(-length((vUv-vec2(0.56,0.48))*vec2(1.7,1.35))*3.8);
        float rim=exp(-length((vUv-vec2(0.82,0.75))*vec2(2.4,2.0))*4.0);
        float grain=fract(sin(dot(gl_FragCoord.xy,vec2(12.9898,78.233)))*43758.5453);
        gl_FragColor=vec4(base+vec3(0.027,0.049,0.084)*pool+vec3(0.035,0.022,0.052)*rim+(grain-0.5)*0.0018,1.0);
      }`
  }));
  background.frustumCulled = false;
  background.renderOrder = -1000;
  world.add(background);
  const environmentGenerator = new THREE.PMREMGenerator(renderer);
  const room = new RoomEnvironment();
  const environment = environmentGenerator.fromScene(room, 0.04);
  world.environment = environment.texture;
  world.environmentIntensity = 0.75;
  room.dispose(); environmentGenerator.dispose();
  world.add(new THREE.HemisphereLight(0xc5daff, 0x101329, 1.7));
  const key = new THREE.DirectionalLight(0xffeed9, 4.2);
  key.position.set(-180, 250, 300);
  world.add(key);
  const rim = new THREE.DirectionalLight(0x96b9ff, 3.6);
  rim.position.set(180, 70, -220);
  world.add(rim);
  const fill = new THREE.DirectionalLight(0xe3b7eb, 1.3);
  fill.position.set(-180, -100, 80);
  world.add(fill);
  const perspective = new THREE.PerspectiveCamera(36, 1, 0.5, 30000);
  const orthographic = new THREE.OrthographicCamera(-100, 100, 100, -100, 0.5, 30000);
  let camera = perspective;
  const renderTarget = new THREE.WebGLRenderTarget(1, 1, { type: THREE.HalfFloatType, samples: 4 });
  const composer = new EffectComposer(renderer, renderTarget);
  const renderPass = new RenderPass(world, camera);
  const bloom = new UnrealBloomPass(new THREE.Vector2(1, 1), 0.38, 0.55, 1.15);
  const output = new OutputPass();
  composer.addPass(renderPass); composer.addPass(bloom); composer.addPass(output);
  let controls, width = 1, height = 1, active = false, frame = 0, tween = null;
  let data = null, mesh = null, pickMesh = null, collars = null, nodeById = new Map(), edgeObjects = [];
  let flat = false, touchPan = false, selected = null, hovered = null, visibleLabels = 0;
  let selectedRing = null, hoverRing = null;
  const raycaster = new THREE.Raycaster(), pointer = new THREE.Vector2();
  const events = new AbortController();
  const reduced = matchMedia("(prefers-reduced-motion: reduce)");
  const labels = createLabels(host, portraits, onSelect, id => focus(id), obstructions);

  function invalidate() {
    if (!active || document.hidden || frame) return;
    frame = requestAnimationFrame(draw);
  }

  function draw(now) {
    frame = 0;
    if (!active || document.hidden) return;
    if (tween) {
      const progress = Math.min(1, (now - tween.start) / 950);
      const eased = progress < 0.5 ? 4 * progress ** 3 : 1 - (-2 * progress + 2) ** 3 / 2;
      camera.position.lerpVectors(tween.from, tween.to, eased);
      controls.target.lerpVectors(tween.oldTarget, tween.target, eased);
      controls.update();
      if (progress === 1) { tween = null; onCamera(); }
    } else controls.update();
    selectedRing?.quaternion.copy(camera.quaternion);
    hoverRing?.quaternion.copy(camera.quaternion);
    renderPass.camera = camera;
    composer.render();
    visibleLabels = labels.update(camera, width, height);
    if (tween) invalidate();
  }

  function bindControls() {
    controls?.dispose();
    controls = new OrbitControls(camera, canvas);
    controls.enableDamping = true;
    controls.dampingFactor = 0.12;
    controls.enableRotate = !flat;
    controls.minPolarAngle = 0.25;
    controls.maxPolarAngle = Math.PI - 0.25;
    controls.minDistance = 45;
    controls.maxDistance = 18000;
    controls.minZoom = 0.05;
    controls.maxZoom = 16;
    controls.rotateSpeed = 0.45;
    controls.zoomSpeed = 0.7;
    controls.panSpeed = 0.7;
    controls.screenSpacePanning = true;
    controls.touches.ONE = touchPan || flat ? THREE.TOUCH.PAN : THREE.TOUCH.ROTATE;
    controls.touches.TWO = THREE.TOUCH.DOLLY_PAN;
    controls.addEventListener("change", invalidate);
    controls.addEventListener("start", () => { tween = null; });
    controls.addEventListener("end", onCamera);
    controls.enabled = active;
  }
  perspective.position.set(80, 60, 500);
  bindControls();

  function resize() {
    const rect = host.getBoundingClientRect();
    if (rect.width < 1 || rect.height < 1) return;
    width = rect.width; height = rect.height;
    renderer.setSize(width, height, false);
    composer.setSize(width, height);
    perspective.aspect = width / height;
    perspective.updateProjectionMatrix();
    const halfHeight = orthographic.top || 100;
    orthographic.left = -halfHeight * width / height;
    orthographic.right = halfHeight * width / height;
    orthographic.updateProjectionMatrix();
    invalidate();
  }
  const observer = new ResizeObserver(resize);
  observer.observe(host);

  function moveCamera(target, position, animate) {
    tween = null;
    if (animate && !reduced.matches && active) {
      tween = { from: camera.position.clone(), to: position, oldTarget: controls.target.clone(), target, start: performance.now() };
    } else {
      camera.position.copy(position); controls.target.copy(target); controls.update(); onCamera();
    }
    invalidate();
  }

  function fit(animate = true) {
    if (!data?.nodes.length) return;
    resize();
    const targets = !data.fitAll && data.routeEdges.size ? data.nodes.filter(node => node.route) : data.nodes;
    const bounds = new THREE.Box3().setFromPoints(targets.map(vector));
    const center = bounds.getCenter(new THREE.Vector3());
    const direction = new THREE.Vector3(flat ? 0 : data.routeEdges.size ? 0.06 : 0.23, flat ? 0 : 0.12, 1).normalize();
    const right = new THREE.Vector3().crossVectors(new THREE.Vector3(0, 1, 0), direction).normalize();
    const up = new THREE.Vector3().crossVectors(direction, right).normalize();
    const offsets = insets();
    const usableWidth = Math.max(width * 0.32, width - offsets.left - offsets.right);
    const usableHeight = Math.max(height * 0.3, height - offsets.top - offsets.bottom);
    let extentX = 35, extentY = 35, extentZ = 0;
    for (const node of targets) {
      const relative = vector(node).sub(center);
      extentX = Math.max(extentX, Math.abs(relative.dot(right)) + 15);
      extentY = Math.max(extentY, Math.abs(relative.dot(up)) + 18);
      extentZ = Math.max(extentZ, relative.dot(direction));
    }
    const span = Math.max(extentY * 2 * height / usableHeight, extentX * 2 * height / usableWidth, 130);
    const distance = flat ? 5000 : span / (2 * Math.tan(THREE.MathUtils.degToRad(18))) + extentZ;
    const worldHeight = flat ? span : 2 * distance * Math.tan(THREE.MathUtils.degToRad(18));
    const target = center.clone().addScaledVector(right, -(offsets.left - offsets.right) / height * worldHeight / 2)
      .addScaledVector(up, (offsets.top - offsets.bottom) / height * worldHeight / 2);
    if (flat) {
      orthographic.top = span / 2; orthographic.bottom = -span / 2;
      orthographic.left = -span / 2 * width / height; orthographic.right = span / 2 * width / height;
      orthographic.zoom = 1; orthographic.updateProjectionMatrix();
    }
    moveCamera(target, target.clone().addScaledVector(direction, distance), animate);
  }

  function refreshEmphasis() {
    if (!mesh || !data) return;
    const emphasis = selected || hovered;
    const neighbors = new Set([emphasis]);
    for (const edge of data.edges) {
      if (edge.from === emphasis) neighbors.add(edge.to);
      if (edge.to === emphasis) neighbors.add(edge.from);
    }
    data.nodes.forEach((node, index) => {
      const color = new THREE.Color(node.route ? GOLD : palette[node.branch % palette.length]);
      if (emphasis && !neighbors.has(node.id) && !node.route) color.multiplyScalar(0.28);
      mesh.setColorAt(index, color);
    });
    mesh.instanceColor.needsUpdate = true;
    for (const entry of edgeObjects) {
      entry.object.material = emphasis && (entry.edge.from === emphasis || entry.edge.to === emphasis) && !data.routeEdges.has(entry.edge.id)
        ? entry.highlight : entry.base;
    }
    for (const [ring, id] of [[selectedRing, selected], [hoverRing, hovered]]) {
      const node = nodeById.get(id);
      ring.visible = Boolean(node);
      if (node) ring.position.copy(vector(node));
    }
    labels.select(selected); labels.hover(hovered);
    invalidate();
  }

  function setData(next, route, autoFit = true) {
    const initial = !data;
    data = next;
    for (const entry of edgeObjects) entry.object.material = entry.base;
    edgeObjects = [];
    if (pickMesh) { pickMesh.geometry.dispose(); pickMesh.material.dispose(); pickMesh.dispose(); }
    disposeGroup(content);
    nodeById = new Map(data.nodes.map(node => [node.id, node]));
    const material = new THREE.MeshPhysicalMaterial({ roughness: 0.22, metalness: 0.32,
      clearcoat: 1, clearcoatRoughness: 0.16, iridescence: 0.18, envMapIntensity: 1.6 });
    mesh = new THREE.InstancedMesh(new THREE.SphereGeometry(1, 28, 18), material, data.nodes.length);
    collars = new THREE.InstancedMesh(new THREE.TorusGeometry(1.24, 0.032, 6, 48),
      new THREE.MeshStandardMaterial({ color: 0xc8d6e9, metalness: 0.75, roughness: 0.24 }), data.nodes.length);
    pickMesh = new THREE.InstancedMesh(new THREE.SphereGeometry(1, 12, 8), new THREE.MeshBasicMaterial(), data.nodes.length);
    const transform = new THREE.Object3D();
    data.nodes.forEach((node, index) => {
      const radius = node.route ? 5.2 : 4.2;
      transform.position.copy(vector(node)); transform.rotation.set(0, 0, 0); transform.scale.setScalar(radius); transform.updateMatrix();
      mesh.setMatrixAt(index, transform.matrix);
      mesh.setColorAt(index, new THREE.Color(node.route ? GOLD : palette[node.branch % palette.length]));
      transform.rotation.set(0.65, 0.25, -0.3); transform.updateMatrix(); collars.setMatrixAt(index, transform.matrix);
      transform.scale.setScalar(radius + 3); transform.updateMatrix(); pickMesh.setMatrixAt(index, transform.matrix);
      if (node.route) {
        const bead = new THREE.Mesh(new THREE.SphereGeometry(1.6, 20, 12), new THREE.MeshBasicMaterial({ color: new THREE.Color(GOLD).multiplyScalar(2.2) }));
        bead.position.copy(vector(node)).add(new THREE.Vector3(0, 0, 4.4));
        content.add(bead);
      }
    });
    mesh.computeBoundingSphere(); collars.computeBoundingSphere(); pickMesh.computeBoundingSphere();
    content.add(mesh, collars);
    const familyMaterials = palette.map(color => new THREE.MeshStandardMaterial({ color,
      roughness: 0.5, metalness: 0.3, transparent: true, opacity: route ? 0.13 : 0.4, depthWrite: false }));
    const routeMaterial = new THREE.MeshStandardMaterial({ color: GOLD, emissive: GOLD, emissiveIntensity: 1.5, metalness: 0.3, roughness: 0.28 });
    const highlightMaterial = new THREE.MeshStandardMaterial({ color: 0xe2eaff, emissive: 0xabcaff, emissiveIntensity: 0.4, roughness: 0.4 });
    const dashedHighlight = new THREE.LineDashedMaterial({ color: 0xe2eaff, dashSize: 2, gapSize: 1.8 });
    const dashedMaterials = {
      spouse: new THREE.LineDashedMaterial({ color: 0xc8c4e8, transparent: true, opacity: route ? 0.18 : 0.48, dashSize: 2.2, gapSize: 2, depthWrite: false }),
      hypothesis: new THREE.LineDashedMaterial({ color: 0xbca6cf, transparent: true, opacity: 0.45, dashSize: 0.7, gapSize: 2, depthWrite: false })
    };
    const routeSteps = new Map((route?.steps || []).map(step => [step.edge.id, step]));
    for (const edge of data.edges) {
      const from = vector(nodeById.get(edge.from)), to = vector(nodeById.get(edge.to));
      const bend = Math.min(45, from.distanceTo(to) * 0.12);
      const curve = new THREE.CubicBezierCurve3(from,
        new THREE.Vector3(from.x, from.y + (to.y - from.y) * 0.55, from.z - bend),
        new THREE.Vector3(to.x, to.y - (to.y - from.y) * 0.55, to.z - bend), to);
      const isRoute = data.routeEdges.has(edge.id);
      if (edge.type === "spouse" || edge.hypothetical) {
        const base = isRoute ? new THREE.LineDashedMaterial({ color: GOLD, dashSize: edge.hypothetical ? 0.8 : 3, gapSize: 2, linewidth: 1 })
          : dashedMaterials[edge.hypothetical ? "hypothesis" : "spouse"];
        const line = new THREE.Line(new THREE.BufferGeometry().setFromPoints(curve.getPoints(64)), base);
        line.computeLineDistances(); content.add(line);
        edgeObjects.push({ edge, object: line, base, highlight: dashedHighlight });
      } else {
        const base = isRoute ? routeMaterial : familyMaterials[nodeById.get(edge.from).branch % palette.length];
        const tube = new THREE.Mesh(new THREE.TubeGeometry(curve, 32, isRoute ? 0.72 : 0.23, 7, false), base);
        content.add(tube); edgeObjects.push({ edge, object: tube, base, highlight: highlightMaterial });
      }
      if (isRoute) {
        const arrow = new THREE.Mesh(new THREE.ConeGeometry(1.8, 4.2, 12), routeMaterial);
        arrow.position.copy(curve.getPoint(0.55));
        const tangent = curve.getTangent(0.55).normalize().multiplyScalar(routeSteps.get(edge.id).from === edge.from ? 1 : -1);
        arrow.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), tangent);
        content.add(arrow);
      }
    }
    const resources = new THREE.Group();
    resources.visible = false;
    for (const resource of [...familyMaterials, ...Object.values(dashedMaterials), routeMaterial, highlightMaterial, dashedHighlight]) {
      const holder = new THREE.Object3D();
      holder.material = resource;
      resources.add(holder);
    }
    content.add(resources);
    selectedRing = new THREE.Mesh(new THREE.TorusGeometry(7, 0.23, 8, 72), new THREE.MeshBasicMaterial({ color: GOLD }));
    hoverRing = new THREE.Mesh(new THREE.TorusGeometry(5.8, 0.13, 6, 56), new THREE.MeshBasicMaterial({ color: 0xe4efff, transparent: true, opacity: 0.65 }));
    content.add(selectedRing, hoverRing);
    labels.setNodes(data.nodes, route);
    refreshEmphasis();
    if (autoFit) fit(!initial);
    invalidate();
  }

  function focus(id) {
    const node = nodeById.get(id);
    if (!node) return;
    const target = vector(node);
    const offset = camera.position.clone().sub(controls.target).normalize().multiplyScalar(flat ? 5000 : 230);
    if (flat) { orthographic.zoom = Math.max(1, orthographic.top / 90); orthographic.updateProjectionMatrix(); }
    moveCamera(target, target.clone().add(offset), true);
  }

  function hitAt(event) {
    if (!pickMesh) return null;
    const rect = canvas.getBoundingClientRect();
    pointer.set((event.clientX - rect.left) / rect.width * 2 - 1, -(event.clientY - rect.top) / rect.height * 2 + 1);
    raycaster.setFromCamera(pointer, camera);
    const hit = raycaster.intersectObject(pickMesh)[0];
    return hit ? data.nodes[hit.instanceId].id : null;
  }
  let down = null;
  canvas.addEventListener("pointerdown", event => { if (event.button === 0) down = { x: event.clientX, y: event.clientY, id: event.pointerId }; }, { signal: events.signal });
  canvas.addEventListener("pointercancel", () => { down = null; }, { signal: events.signal });
  canvas.addEventListener("pointerup", event => {
    const start = down; down = null;
    if (!start || start.id !== event.pointerId || Math.hypot(event.clientX - start.x, event.clientY - start.y) > 5) return;
    const id = hitAt(event);
    if (id) onSelect(id);
  }, { signal: events.signal });
  canvas.addEventListener("dblclick", event => { const id = hitAt(event); if (id) focus(id); }, { signal: events.signal });
  canvas.addEventListener("pointermove", event => {
    if (event.buttons || event.pointerType === "touch") return;
    const id = hitAt(event);
    canvas.style.cursor = id ? "pointer" : "grab";
    if (hovered !== id) { hovered = id; refreshEmphasis(); }
  }, { signal: events.signal });
  canvas.addEventListener("pointerleave", () => { hovered = null; refreshEmphasis(); }, { signal: events.signal });
  canvas.addEventListener("webglcontextlost", event => {
    event.preventDefault(); setActive(false);
    onFailure("Przeglądarka zwolniła kontekst 3D. Lista połączenia i karty osób nadal działają.");
  }, { signal: events.signal });
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) { cancelAnimationFrame(frame); frame = 0; tween = null; }
    else invalidate();
  }, { signal: events.signal });

  function setActive(value) {
    active = value; controls.enabled = value;
    if (value) { resize(); invalidate(); }
    else { cancelAnimationFrame(frame); frame = 0; tween = null; }
  }

  function setFlat(value) {
    flat = Boolean(value); camera = flat ? orthographic : perspective;
    bindControls(); fit(false);
  }

  return { setData, focus, fit, setActive, setFlat, redraw: invalidate,
    select(id) { selected = id; refreshEmphasis(); },
    setTouchPan(value) { touchPan = value; controls.touches.ONE = touchPan || flat ? THREE.TOUCH.PAN : THREE.TOUCH.ROTATE; },
    zoom(factor) {
      tween = null;
      if (flat) { camera.zoom = THREE.MathUtils.clamp(camera.zoom * factor, 0.05, 16); camera.updateProjectionMatrix(); }
      else {
        const direction = camera.position.clone().sub(controls.target);
        direction.setLength(THREE.MathUtils.clamp(direction.length() / factor, 45, 18000));
        camera.position.copy(controls.target).add(direction);
      }
      controls.update(); invalidate(); onCamera();
    },
    state() { return { flat, position: camera.position.toArray(), target: controls.target.toArray(), zoom: camera.zoom, span: orthographic.top }; },
    restore(state) {
      if (!state || !Array.isArray(state.position) || !Array.isArray(state.target)
        || state.position.length !== 3 || state.target.length !== 3 || ![...state.position, ...state.target].every(Number.isFinite)) return;
      if (Boolean(state.flat) !== flat) setFlat(state.flat);
      tween = null; camera.position.fromArray(state.position); controls.target.fromArray(state.target);
      camera.zoom = Number.isFinite(state.zoom) && state.zoom > 0 ? state.zoom : 1;
      if (flat && state.span > 0) { orthographic.top = state.span; orthographic.bottom = -state.span; resize(); }
      camera.updateProjectionMatrix(); controls.update(); invalidate();
    },
    diagnostics() { return { active, pendingFrame: Boolean(frame), nodes: data?.nodes.length || 0, labels: visibleLabels,
      calls: renderer.info.render.calls, geometries: renderer.info.memory.geometries, textures: renderer.info.memory.textures,
      triangles: renderer.info.render.triangles, postprocessing: "MSAA + bloom + ACES", pixelRatio: renderer.getPixelRatio() }; },
    dispose() {
      setActive(false); observer.disconnect(); controls.dispose(); events.abort(); labels.dispose();
      if (pickMesh) { pickMesh.geometry.dispose(); pickMesh.material.dispose(); pickMesh.dispose(); }
      for (const entry of edgeObjects) entry.object.material = entry.base;
      disposeGroup(content); disposeGroup(world); environment.dispose();
      bloom.dispose(); output.dispose(); renderPass.dispose(); composer.dispose(); renderer.dispose(); canvas.remove();
    }
  };
}
