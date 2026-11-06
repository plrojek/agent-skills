// Poster configurator of pl-genealogy-tree-viewer. Made by Applied AI (https://appliedai.dev),
// https://github.com/plrojek/agent-skills. Posters themselves carry no credit; this page's footer does.
export const BACKGROUNDS = [
  { id: "akwarela", name: "Akwarela", file: "background1", description: "Lekka, świetlista korona" },
  { id: "botaniczny", name: "Botaniczne", file: "background2", description: "Głęboka zieleń i rozłożyste konary" },
  { id: "zloty", name: "Złoty dąb", file: "background3", description: "Ciepły papier i stare złoto" },
];

export const FORMATS = {
  panorama: { name: "Panorama", width: 841, height: 473.3 },
  a1: { name: "A1 poziomo", width: 841, height: 594 },
  a2: { name: "A2 poziomo", width: 594, height: 420 },
  a3: { name: "A3 poziomo", width: 420, height: 297 },
  custom: { name: "Własny format", width: 841, height: 473.3 },
};

export const FONTS = {
  klasyczna: "Georgia, 'Times New Roman', serif",
  ksiegowa: "'Iowan Old Style', Palatino, 'Palatino Linotype', serif",
  garamond: "'Baskerville', 'Garamond', Georgia, serif",
};

export const DEFAULT_CONFIG = {
  version: 1,
  root: "",                       // publish.py: the person the tree is for (<meta name="poster-root">)
  title: "Nasza rodzina",
  subtitle: "Historia zapisana w pokoleniach",
  dedication: "",
  footerText: "{people} osób · {generations} pokoleń · z rodzinnego archiwum",
  background: "akwarela",
  format: "panorama",
  width: 841,
  height: 473.3,
  generations: 5,
  labelStyle: "kartusz",
  font: "klasyczna",
  ink: "#3c3525",
  titleColor: "#3c3525",
  subtitleColor: "#3c3525",
  titleMargin: 0.024,
  accent: "#8a7845",
  paper: "#fff9e9",
  labelOpacity: 0.95,
  labelScale: 1,
  haloShape: "oval",
  haloDecay: 1,
  haloBlur: 0.06,
  spread: 0.86,
  verticalSpread: 1,
  bend: 0,
  rootDrop: 0,
  compact: 0.5,
  lineColors: "rodziny",
  lineWidth: 1.5,
  lineOpacity: 0.85,
  lineCasing: 0.5,
  showDates: true,
  showUnknown: false,
  showConnections: true,
  showFrame: true,
  showGuides: true,
  showFooter: true,
  showSiblings: false,
  generationSettings: {},
  generationScale: {},
  cardSettings: {},
  positions: {},
};

function bounded(value, fallback, minimum, maximum) {
  return typeof value === "number" && Number.isFinite(value)
    ? Math.max(minimum, Math.min(maximum, value)) : fallback;
}

function isCardKey(key) {
  return /^[1-9]\d{0,2}$/.test(key) && Number(key) <= 511 || /^sibling:@[\w-]{1,72}@$/.test(key);
}

export function normalizeConfig(input = {}) {
  if (!input || typeof input !== "object" || Array.isArray(input)) throw new Error("Konfiguracja musi być obiektem JSON.");
  if (input.version !== undefined && input.version !== 1) throw new Error("Nieobsługiwana wersja konfiguracji.");
  const config = { ...DEFAULT_CONFIG };
  for (const key of ["root", "title", "subtitle", "dedication", "footerText"]) {
    if (typeof input[key] === "string") config[key] = input[key].slice(0, key === "root" ? 80 : key === "footerText" ? 300 : 150);
  }
  if (input.footerText === undefined && config.dedication) config.footerText = config.dedication;
  for (const [key, values] of Object.entries({
    background: BACKGROUNDS.map(background => background.id),
    format: Object.keys(FORMATS), labelStyle: ["kartusz", "lisc", "tekst", "halo"],
    haloShape: ["oval", "circle"], font: Object.keys(FONTS), lineColors: ["rodziny", "jeden"],
  })) if (values.includes(input[key])) config[key] = input[key];
  for (const key of ["ink", "accent", "paper", "titleColor", "subtitleColor"]) {
    if (typeof input[key] === "string" && /^#[\da-f]{6}$/i.test(input[key])) config[key] = input[key];
  }
  for (const key of ["titleColor", "subtitleColor"]) if (input[key] === undefined) config[key] = config.ink;
  if (input.showGuides === undefined && typeof input.showFrame === "boolean") config.showGuides = input.showFrame;
  for (const key of ["showDates", "showUnknown", "showConnections", "showFrame", "showGuides", "showFooter", "showSiblings"]) {
    if (typeof input[key] === "boolean") config[key] = input[key];
  }
  for (const [key, limits] of Object.entries({
    width: [200, 1600], height: [150, 1200], generations: [2, 9], labelOpacity: [0, 1],
    labelScale: [0.65, 1.5], spread: [0.55, 0.95], verticalSpread: [0.25, 2],
    haloDecay: [0.2, 4], haloBlur: [0, 0.25], bend: [-2, 2],
    titleMargin: [0, 0.2], rootDrop: [0, 0.1], compact: [0, 1],
    lineWidth: [0.5, 5], lineOpacity: [0.3, 1], lineCasing: [0, 1],
  })) config[key] = bounded(input[key], config[key], ...limits);
  config.generations = Math.round(config.generations);
  if (config.format !== "custom") Object.assign(config, {
    width: FORMATS[config.format].width, height: FORMATS[config.format].height,
  });
  config.generationSettings = {};
  for (let generation = 0; generation < 9; generation++) {
    const setting = input.generationSettings?.[generation];
    if (!setting || typeof setting !== "object" || Array.isArray(setting)) continue;
    const normalized = {};
    for (const key of ["showGivenName", "showSurname", "showBirth", "showDeath"]) {
      if (typeof setting[key] === "boolean") normalized[key] = setting[key];
    }
    if (typeof setting.fontSize === "number" && Number.isFinite(setting.fontSize)) normalized.fontSize = bounded(setting.fontSize, 12, 3, 72);
    if (typeof setting.width === "number" && Number.isFinite(setting.width)) normalized.width = bounded(setting.width, 60, 5, 300);
    config.generationSettings[generation] = normalized;
  }
  // Suwak „Wielkość wybranych pokoleń”: mnożnik pisma i miejsca w pionie dla pokolenia (indeks 0–8, jak generationSettings).
  config.generationScale = {};
  if (input.generationScale && typeof input.generationScale === "object" && !Array.isArray(input.generationScale)) {
    for (let generation = 0; generation < 9; generation++) {
      const scale = input.generationScale[generation];
      if (typeof scale === "number" && Number.isFinite(scale) && Math.abs(scale - 1) > 0.001) config.generationScale[generation] = bounded(scale, 1, 0.5, 2.5);
    }
  }
  config.positions = {};
  if (input.positions && typeof input.positions === "object" && !Array.isArray(input.positions)) {
    for (const [key, position] of Object.entries(input.positions).slice(0, 1024)) {
      if (!isCardKey(key) || !position || typeof position !== "object") continue;
      config.positions[key] = {
        x: bounded(position.x, 0, -0.45, 0.45), y: bounded(position.y, 0, -0.45, 0.45),
      };
    }
  }
  config.cardSettings = {};
  if (input.cardSettings && typeof input.cardSettings === "object" && !Array.isArray(input.cardSettings)) {
    for (const [key, setting] of Object.entries(input.cardSettings).slice(0, 1024)) {
      if (!isCardKey(key) || !setting || typeof setting !== "object" || Array.isArray(setting)) continue;
      const normalized = { scale: bounded(setting.scale, 1, 0.5, 2) };
      if (typeof setting.fontSize === "number" && Number.isFinite(setting.fontSize)) normalized.fontSize = bounded(setting.fontSize, 12, 3, 72);
      config.cardSettings[key] = normalized;
    }
  }
  return config;
}

export function generationSettings(config, generation) {
  return {
    showGivenName: true, showSurname: true, showBirth: config.showDates, showDeath: config.showDates,
    fontSize: null, width: null, ...config.generationSettings[generation],
  };
}

export function rootSiblings(people, root) {
  const parents = (people[root]?.parents || []).filter(Boolean);
  return Object.entries(people).filter(([personId, person]) => personId !== root
    && person.parents?.some(parentId => parentId && parents.includes(parentId)))
    .sort(([leftId, left], [rightId, right]) => (left.born || "9999").localeCompare(right.born || "9999")
      || left.name.localeCompare(right.name, "pl") || leftId.localeCompare(rightId));
}

export function collectAncestors(people, config) {
  if (!Object.hasOwn(people, config.root)) throw new Error("Nie znaleziono wybranej osoby w drzewie.");
  const nodes = [];
  function visit(personId, number, generation, seen) {
    const person = people[personId];
    if (!person && !config.showUnknown) return;
    nodes.push({ number, personId, person, generation });
    if (generation + 1 >= config.generations || !person || seen.has(personId)) return;
    const visited = new Set([...seen, personId]);
    for (const [index, parentId] of (person.parents || [null, null]).entries()) {
      visit(parentId, number * 2 + index, generation + 1, visited);
    }
  }
  visit(config.root, 1, 0, new Set());
  if (config.showSiblings) {
    for (const [personId, person] of rootSiblings(people, config.root)) {
      nodes.push({ number: `sibling:${personId}`, personId, person, generation: 0, isSibling: true });
    }
  }
  return nodes;
}

function labelLines(node, settings) {
  if (!node.person) return [{ text: "Nieznany przodek", scale: 1 }];
  const { name, surname, born, died } = node.person;
  const given = surname && name.endsWith(surname) ? name.slice(0, -surname.length).trim() : name;
  const lines = [];
  if (settings.showGivenName && given) lines.push({ text: given, scale: 1 });
  if (settings.showSurname && surname) lines.push({ text: surname, scale: 1, bold: true });
  const birth = settings.showBirth && born;
  const death = settings.showDeath && died;
  const dates = birth && death ? `${birth}–${death}` : birth ? `ur. ${birth}` : death ? `zm. ${death}` : "";
  if (dates) lines.push({ text: dates, scale: 0.7, dates: true });
  return lines;
}

const LANE = 10;   // wolny pas na linie między pokoleniami (jednostki rysunku × artScale, ok. 5 mm na panoramie)

// Wysokość pokoleń dzielona według potrzeb: pierwszy przebieg mierzy, ile każde pokolenie naprawdę zajmuje;
// pokolenia, których pismo ogranicza szerokość (albo reguła „dalsze ≤ bliższe”), oddają nadmiar tym,
// które ogranicza wysokość. Dzięki temu nie ma długich pustych linii, a gęste pokolenia mają większe pismo.
// Kolory linii „każda rodzina w innym kolorze”: stonowane barwy pasujące do akwareli. Obie linie od dziecka
// do jego rodziców mają ten sam kolor; sąsiednie dzieci w rzędzie zawsze różne, więc wiązki linii da się rozróżnić.
export const LINE_COLORS = ["#4a6a8c", "#a4553c", "#4f7a3a", "#7a4f7c", "#9a7a2c"];

export function layoutPoster(people, input, fit = null) {
  if (fit === null) {
    let state = { weights: {}, lanes: {}, crowded: {} };
    let layout = layoutPoster(people, input, state);
    for (let pass = 0; pass < 5; pass++) {
      const next = { weights: {}, lanes: { ...state.lanes }, crowded: { ...state.crowded } };
      let changed = false;
      for (const [generation, plan] of layout.plans) {
        const edges = layout.rowEdges.get(generation);
        if (generation < 2 || !edges) continue;
        const band = layout.bandOf(generation);
        // ciasny rząd w jednym rzędzie potrzebuje wysokości na drugi (wtedy podpisy mogą stać nad swoimi dziećmi);
        // raz ciasny zostaje ciasny do końca dopasowania, żeby przebiegi się nie przerzucały
        // suwak „Większe pismo ↔ Krótsze linie” (compact 0–1): od kiedy rząd uznajemy za ciasny i ile mu dajemy
        const compact = layout.config.compact;
        const crowded = compact > 0 && (Boolean(state.crowded[generation]) || (plan.tiers === 1 && plan.packed > 0.95 - 0.35 * compact));
        if (crowded && !state.crowded[generation]) { next.crowded[generation] = true; changed = true; }
        const doubled = crowded && plan.tiers === 1;   // dwa rzędy już są: zmierzona wysokość je obejmuje
        const need = (edges.bottom - edges.top) * (doubled ? 2 : 1) + (doubled ? 4 : 0) * layout.artScale + plan.lane + 10 * layout.artScale;
        const limited = plan.heightCap !== Infinity && plan.font >= 0.97 * plan.heightCap;
        const current = state.weights[generation] ?? 1;
        next.weights[generation] = doubled ? Math.min(1 + compact, Math.max(current, current * need / band)) : limited ? current : Math.max(0.35, Math.min(current, current * need / band));
        if (Math.abs(next.weights[generation] - current) > 0.02) changed = true;
        // zmierzony odstęp między podpisami tego i niższego pokolenia, które stoją nad sobą (z wygięciem);
        // za mały = szerszy pas przy następnym przebiegu (pomijamy ręcznie przesunięte podpisy)
        const lower = layout.nodes.filter(node => node.generation === generation - 1 && !layout.config.positions[node.number]);
        const upper = layout.nodes.filter(node => node.generation === generation && !layout.config.positions[node.number]);
        let clearance = Infinity;
        for (const a of lower) for (const b of upper) {
          if (Math.abs(a.x - b.x) < (a.width + b.width) / 2) clearance = Math.min(clearance, (a.y - a.height / 2) - (b.y + b.height / 2));
        }
        const wanted = LANE * 0.8 * layout.artScale;
        if (clearance < wanted - 0.5) { next.lanes[generation] = (state.lanes[generation] ?? 0) + (wanted - clearance); changed = true; }

      }
      if (!changed) break;
      state = next;
      layout = layoutPoster(people, input, state);
    }
    return layout;
  }
  const config = normalizeConfig(input);
  const nodes = collectAncestors(people, config);
  const byNumber = new Map(nodes.map(node => [node.number, node]));
  const width = 1800;
  const height = width * config.height / config.width;
  const artWidth = Math.min(width, height * 5016 / 2823);
  const artHeight = artWidth * 2823 / 5016;
  const artLeft = (width - artWidth) / 2;
  const artTop = (height - artHeight) / 2;
  const artScale = artWidth / width;
  const depth = Math.max(...nodes.map(node => node.generation), 1);
  const rows = new Map();
  const rowSpacing = 0.64 / depth;
  // Powiększone pokolenie dostaje proporcjonalnie wyższy pas, pozostałe trochę niższe; razem tyle samo miejsca co dotąd.
  const scaled = Object.keys(config.generationScale).length > 0 || Object.values(fit.weights).some(value => value !== 1);
  const weight = generation => (config.generationScale[generation] ?? 1) * (fit.weights[generation] ?? 1);
  const gaps = Array.from({ length: depth }, (_, index) => (weight(index) + weight(index + 1)) / 2);
  const unit = scaled ? 0.64 / gaps.reduce((sum, gap) => sum + gap, 0) : rowSpacing;
  // „Margines od góry” jest sufitem drzewa: tytuł (jeśli jest) i najwyższe pokolenie nie wchodzą wyżej.
  // Gdy pokolenia sięgają wyżej (duże odstępy), drzewo ściska się pod sufitem. Bez tytułu sufit = sam margines.
  const header = headerLayout(config, artTop, artHeight, artScale);
  const ceiling = (header.bottom - artTop) / artHeight;
  // nad najwyższym pokoleniem nie ma linii: jego podpisy mogą sięgać do samego sufitu (bez wolnego pasa)
  const topRoom = (depth >= 2 ? LANE + 8 : 8) * artScale / artHeight / 2;
  const verticalSpread = Math.min(config.verticalSpread, Math.max(0.05, (0.855 + topRoom - ceiling) / (0.64 + unit * weight(depth) / 2)));
  const staggerRatio = Math.min(0.018, rowSpacing * verticalSpread * 0.15);
  const rowOffset = [0];
  for (const [index, gap] of gaps.entries()) rowOffset.push(scaled ? rowOffset[index] + gap * unit : (index + 1) * rowSpacing);
  // Pismo bez powiększeń: punkt odniesienia dla suwaka (150% = pismo 1,5 raza większe niż automatyczne).
  const reference = Object.keys(config.generationScale).length ? layoutPoster(people, { ...config, generationScale: {} }).plans : null;
  for (const node of nodes) {
    const baseY = 0.855 - rowOffset[node.generation];
    const stagger = 0;   // dawny rozrzut ±1,8% (pokolenia 4+) zabierał wysokość; odstępy w rzędzie pilnuje teraz układ
    node.rowY = artTop + artHeight * (0.855 + config.rootDrop - (0.855 - baseY) * verticalSpread);   // rootDrop: całe drzewo niżej
    node.y = node.rowY + artHeight * stagger;
    node.stagger = stagger * artHeight;
    if (!rows.has(node.generation)) rows.set(node.generation, []);
    rows.get(node.generation).push(node);
  }
  // Automatyczna wielkość pisma (05.11.2026). Wcześniej pismo wynikało z odstępu między sąsiadami w rzędzie:
  // pokolenie z kilkudziesięcioma znanymi osobami dostawało 3 pkt, a najdalsze (mało znanych) 12 pkt.
  // Teraz: zatłoczone pokolenie rozkłada się na 2–3 przesunięte rzędy (każdy podpis ma 2–3× więcej szerokości),
  // pismo liczy się z rzeczywistej długości imion i nazwisk pokolenia, a dalsze pokolenie nie ma większego pisma niż bliższe.
  // Ręczne ustawienia pokolenia (szerokość, pismo) i pojedynczych kartuszy działają jak dotąd.
  const circle = config.labelStyle === "halo" && config.haloShape === "circle";
  const bandOf = generation => unit * weight(generation) * verticalSpread * artHeight;
  const textRoom = cardWidth => cardWidth - Math.min(16, cardWidth * 0.15);
  const widthFor = textWidth => textWidth / 0.85 <= 16 / 0.15 ? textWidth / 0.85 : textWidth + 16;
  const lineNeed = node => Math.max(3, ...node.lines.map(line => textUnits(line.text) * line.scale * (line.bold ? 1.06 : 1)));
  const bendShift = x => config.bend * artHeight * 0.22 * ((x - width / 2) / (artWidth * config.spread / 2)) ** 2;
  // Układ jak w rodowodzie: przodkowie każdej gałęzi stoją nad swoim potomkiem. Kolumna = przodek bez dalszych przodków
  // na plakacie; osoba stoi nad środkiem swoich rodziców. Kolejność w rzędzie jest ta sama co dotąd (numer Ahnentafela),
  // a w rzędzie pilnujemy tylko minimalnych odstępów, więc linie nie biegną przez pół plakatu i rzadko się krzyżują.
  const column = new Map();
  let columns = 0;
  const placeColumn = number => {
    const parents = [number * 2, number * 2 + 1].filter(parent => byNumber.has(parent));
    const value = parents.length ? parents.map(placeColumn).reduce((sum, x) => sum + x, 0) / parents.length : columns++;
    column.set(number, value);
    return value;
  };
  placeColumn(1);
  const plans = new Map();
  const frames = new Map();   // granice rzędu i minimalny odstęp między kolejnymi osobami
  let overflow = 0;   // o ile podpisy poprzedniego pokolenia wchodzą w pas tego (np. przy ściśniętych odstępach)
  for (const generation of [...rows.keys()].sort((left, right) => left - right)) {
    const row = rows.get(generation);
    const scale = config.generationScale[generation] ?? 1;   // suwak „Wielkość wybranych pokoleń” (bez podziału wysokości)
    const band = bandOf(generation);
    if (generation === 0) {
      const siblings = row.filter(node => node.isSibling);
      row.splice(0, row.length, ...siblings.slice(0, Math.floor(siblings.length / 2)), byNumber.get(1), ...siblings.slice(Math.floor(siblings.length / 2)));
    } else row.sort((left, right) => left.number - right.number);
    const canopyWidth = config.spread * (0.5 + 0.5 * (generation / depth) ** 0.6);
    const spacing = generation === 0 ? Math.min(315 * artScale, artWidth * config.spread / row.length) : artWidth * canopyWidth / row.length;
    const settings = generationSettings(config, generation);
    for (const node of row) node.lines = labelLines(node, settings);
    const heightRatio = Math.max(1.9, ...row.map(node => node.lines.reduce((sum, line) => sum + line.scale * 1.15, 0) + 0.9));
    const needs = row.map(lineNeed).sort((left, right) => left - right);
    const typicalNeed = needs[Math.floor((needs.length - 1) * 0.75)];
    const longestNeed = needs[needs.length - 1];
    const capFont = (generation === 0 ? 24 : 18) * artScale * scale;
    const staggerRoom = 0;
    const heightBound = generation >= 2 || circle;
    const lift = generation >= 2 ? overflow : 0;
    // ok. 1/5 pasa pokolenia zostaje wolna: tam linie przechodzą w bok, zamiast skosem przez cudze podpisy
    // wolny pas na linie; szerszy tam, gdzie poprzedni przebieg zmierzył za mały odstęp (np. przy wygięciu)
    const lane = generation >= 2 ? LANE * artScale + (fit.lanes[generation] ?? 0) : 0;
    const usable = band - lane - 8 * artScale - lift;
    const xs = row.map((_, index) => width / 2 + (index - (row.length - 1) / 2) * spacing);   // równy podział: do planu pisma
    let plan = null;
    const target = reference && scale !== 1 ? reference.get(generation).font * scale : null;
    // najwyżej 2 przesunięte rzędy: przy trzech linia do górnego rzędu musiałaby przejść przez podpis z dolnego
    for (let tiers = 1; tiers <= (generation >= 2 && settings.width === null ? 2 : 1); tiers++) {
      // przy wygiętych pokoleniach sąsiedzi z różnych rzędów jednego pokolenia przesuwają się w pionie o różną wysokość
      let drift = 0;
      for (let gap = 1; gap < tiers; gap++) for (let index = 0; index + gap < xs.length; index++) {
        drift = Math.max(drift, Math.abs(bendShift(xs[index]) - bendShift(xs[index + gap])));
      }
      const cardWidth = Math.min((generation === 0 ? 280 : 205) * artScale * scale, Math.max(8 * artScale, tiers * spacing - 7 * artScale));
      const tierHeight = Math.max(2 * artScale, (usable - (tiers === 1 ? staggerRoom : 0)) / tiers - (tiers > 1 ? 4 * artScale + drift : 0));
      const room = circle ? Math.min(cardWidth, tierHeight) : cardWidth;
      const heightCap = heightBound ? tierHeight / heightRatio : Infinity;
      const font = Math.max(1.8 * artScale, Math.min(capFont, textRoom(room) / typicalNeed, heightCap));
      if (target === null) { if (!plan || font > plan.font * 1.05) plan = { tiers, font, room, heightCap }; }
      else {   // powiększone pokolenie: najmniej rzędów, w których zmieści się pismo docelowe (albo najbliżej tego)
        const short = Math.max(0, target - font);
        if (!plan || short < plan.short - 0.02 * target) plan = { tiers, font, room, heightCap, short };
      }
    }
    if (!plan.font) plan.font = 1.8 * artScale;
    plan.lane = lane;
    const previous = plans.get(generation - 1);
    if (target !== null) plan.font = target;
    else if (reference) plan.font = Math.min(plan.font, reference.get(generation).font);   // inne pokolenia tylko maleją, gdy oddały miejsce
    else if (generation >= 2 && previous) plan.font = Math.min(plan.font, previous.font);
    plans.set(generation, plan);
    // Gdy pismo pokolenia zostało zmniejszone do bliższego pokolenia, zostaje zapas wysokości: dodatkowy rząd
    // (do 3) pozwala podpisom stać bliżej siebie, czyli nad własnym dzieckiem, a nie tam, gdzie zmieści je równy podział.
    if (generation >= 2 && settings.width === null && settings.fontSize === null && target === null) {
      for (let tiers = plan.tiers + 1; tiers <= 2; tiers++) {
        let drift = 0;
        for (let index = 0; index + 1 < xs.length; index++) drift = Math.max(drift, Math.abs(bendShift(xs[index]) - bendShift(xs[index + 1])));
        const tierHeight = usable / tiers - 4 * artScale - drift;
        const fits = tierHeight / heightRatio / config.labelScale;
        // ciasne pokolenie (zmierzone w poprzednim przebiegu): drugi rząd nawet za cenę mniejszego pisma (do 15% przy „Krótsze linie”)
        if (fits < plan.font && !(fit.crowded[generation] && fits >= (1 - 0.15 * config.compact) * plan.font)) break;
        plan.font = Math.min(plan.font, fits);
        plan.tiers = tiers;
      }
    }
    const step = usable / plan.tiers;
    let reach = 0;
    for (const node of row) {
      let fontSize = plan.font;
      if (generation <= 1) node.width = plan.room;
      else node.width = Math.min(plan.room, Math.max(fontSize * 5, widthFor(fontSize * longestNeed) * 1.06));
      if (settings.width !== null) {
        node.width = settings.width * width / config.width;
        fontSize = Math.max(1.8 * artScale, Math.min(capFont, textRoom(circle ? Math.min(node.width, plan.room) : node.width) / typicalNeed, plan.heightCap));
      }
      fontSize = Math.min(fontSize * config.labelScale, Math.max(fontSize, plan.heightCap));
      node.width *= config.labelScale;
      if (settings.fontSize !== null) fontSize = settings.fontSize * width / config.width * 25.4 / 72;
      node.fontSize = fontSize;
      const individual = config.cardSettings[node.number];
      if (individual) {
        node.width *= individual.scale;
        node.fontSize = individual.fontSize === undefined ? node.fontSize * individual.scale
          : individual.fontSize * width / config.width * 25.4 / 72;
      }
      node.height = node.fontSize * heightRatio;
      // „Miękkie” i „Sam tekst”: ramki nie widać, więc podpis zajmuje tyle, ile jego tekst (krótkie nazwiska — mniej miejsca)
      if (!circle && ["halo", "tekst"].includes(config.labelStyle) && settings.width === null && !individual) {
        const text = Math.max(...node.lines.map(line => node.fontSize * line.scale * textUnits(line.text) * (line.bold ? 1.06 : 1)));
        node.width = Math.min(node.width, widthFor(text) + 6 * artScale);
      }
      if (circle) node.width = node.height = Math.max(node.width, node.height);
    }
    // pozycje w rzędzie: jak najbliżej miejsca z rodowodu, ale nie bliżej siebie niż pozwalają kartusze
    // (kolejne osoby są w różnych rzędach pokolenia, więc te z jednego rzędu dzieli plan.tiers odstępów)
    if (generation === 0) row.forEach((node, index) => { node.x = xs[index]; });
    else {
      const half = artWidth * canopyWidth / 2 - spacing / 2;
      // przy dwóch rzędach między sąsiadami z dolnego rzędu zostaje korytarz na linię do górnego
      // odstęp do sąsiada z jego i własnej szerokości: w jednym rzędzie kartusze się nie stykają, w dwóch rzędach
      // sąsiad z drugiego rzędu nie zasłania korytarza na linię
      let gap = row.slice(1).map((node, index) => plan.tiers > 1
        ? Math.max(row[index].width, node.width) / 2 + 5 * artScale
        : (row[index].width + node.width) / 2 + 4 * artScale);
      const total = gap.reduce((sum, value) => sum + value, 0);
      plan.packed = total / (2 * half);   // ile szerokości rzędu zajmują same odstępy (1 = ciasno)
      if (total > 2 * half) gap = gap.map(value => value * 2 * half / total);
      for (const node of row) node.columnX = width / 2 + ((column.get(node.number) + 0.5) / columns - 0.5) * artWidth * canopyWidth;
      frames.set(generation, { gap, left: width / 2 - half, right: width / 2 + half });
      const placed = spreadInOrder(row.map(node => node.columnX), gap, width / 2 - half, width / 2 + half);
      row.forEach((node, index) => { node.x = placed[index]; });
    }
    for (const [index, node] of row.entries()) {
      if (plan.tiers > 1) node.y += -node.stagger + (index % plan.tiers - (plan.tiers - 1) / 2) * step;
      node.y -= lift / 2;
      node.rowY -= lift / 2;
      const offset = (plan.tiers > 1 ? (index % plan.tiers - (plan.tiers - 1) / 2) * step : node.stagger) - lift / 2;
      reach = Math.max(reach, node.height / 2 - offset);
    }
    overflow = Math.max(0, reach - (band - 8 * artScale) / 2);
    if (generation === 1 && rows.has(0)) {
      // przy wielu pokoleniach pas jest niski: duże podpisy osoby u korzeni zahaczały o rodziców — schodzą odrobinę niżej
      const tallest = list => Math.max(...list.map(node => node.height));
      const push = Math.min(0.05 * artHeight, Math.max(0, (tallest(rows.get(0)) + tallest(row)) / 2 + 4 * artScale - (bandOf(0) + band) / 2));
      for (const node of rows.get(0)) { node.y += push; node.rowY += push; }
    }
  }
  // Kilka przejść w górę i w dół: każdy przodek ciągnie do swojego dziecka i rodziców (a lekko do miejsca z rodowodu),
  // w rzędzie z zachowaniem kolejności i odstępów. Tak zatłoczony rząd nie odsuwa dzieci daleko od ich rodziców.
  const ancestorsRows = [...frames.keys()].sort((left, right) => left - right);
  const pull = node => {
    let sum = 0.3 * node.columnX, count = 0.3;
    const child = byNumber.get(Math.floor(node.number / 2));
    if (child) { sum += 1.5 * child.x; count += 1.5; }
    for (const parent of [byNumber.get(node.number * 2), byNumber.get(node.number * 2 + 1)]) if (parent) { sum += parent.x; count += 1; }
    return sum / count;
  };
  const reposition = generation => {
    const row = rows.get(generation), frame = frames.get(generation);
    const placed = spreadInOrder(row.map(pull), frame.gap, frame.left, frame.right);
    row.forEach((node, index) => { node.x = placed[index]; });
  };
  for (let sweep = 0; sweep < 8; sweep++) {
    for (const generation of [...ancestorsRows].reverse()) reposition(generation);
    for (const generation of ancestorsRows) reposition(generation);
  }
  const rowEdges = new Map();
  for (const [generation, row] of rows) rowEdges.set(generation, {
    top: Math.min(...row.map(node => node.y - node.height / 2)), bottom: Math.max(...row.map(node => node.y + node.height / 2)),
  });
  for (const node of nodes) {
    node.bendY = bendShift(node.x);
    node.y += node.bendY;
  }
  for (const node of nodes) {
    const offset = config.positions[node.number] || { x: 0, y: 0 };
    node.x = Math.max(artLeft + node.width / 2 + 12 * artScale, Math.min(artLeft + artWidth - node.width / 2 - 12 * artScale, node.x + offset.x * artWidth));
    node.y += offset.y * artHeight;
  }
  return { config, nodes, byNumber, width, height, artTop, artHeight, artLeft, artWidth, artScale, plans, header, rowEdges, bendShift, bandOf };
}

// Gładka linia przez punkty (Catmull-Rom zamieniony na krzywe Béziera), bez ponownego „M”.
function smoothPath(points) {
  let path = "";
  for (let index = 0; index + 1 < points.length; index++) {
    const [p0, p1, p2, p3] = [points[Math.max(0, index - 1)], points[index], points[index + 1], points[Math.min(points.length - 1, index + 2)]];
    const c1 = [p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6], c2 = [p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6];
    path += `C ${c1[0].toFixed(2)},${c1[1].toFixed(2)} ${c2[0].toFixed(2)},${c2[1].toFixed(2)} ${p2[0].toFixed(2)},${p2[1].toFixed(2)} `;
  }
  return path.trim();
}

// Osoby w rzędzie w tej samej kolejności, jak najbliżej celów (najmniejsze kwadraty), co najmniej gaps[i] od sąsiada,
// w granicach [left, right]: regresja izotoniczna (PAVA) na celach przesuniętych o sumę odstępów.
function spreadInOrder(targets, gaps, left, right) {
  const count = targets.length;
  if (count === 1) return [Math.max(left, Math.min(right, targets[0]))];
  const offset = [0];
  for (const gap of gaps) offset.push(offset[offset.length - 1] + gap);
  const blocks = [];
  for (const [index, target] of targets.entries()) {
    blocks.push({ sum: target - offset[index], count: 1 });
    while (blocks.length > 1 && blocks.at(-2).sum / blocks.at(-2).count > blocks.at(-1).sum / blocks.at(-1).count) {
      const last = blocks.pop();
      blocks.at(-1).sum += last.sum;
      blocks.at(-1).count += last.count;
    }
  }
  const shifted = blocks.flatMap(block => Array(block.count).fill(block.sum / block.count));
  const high = right - offset[count - 1];
  return shifted.map((value, index) => Math.max(left, Math.min(high, value)) + offset[index]);
}

// Tytuł i podtytuł: położenie wspólne dla układu (sufit drzewa) i rysunku.
// Bez tytułu podtytuł wchodzi na jego miejsce; bez obu drzewo może sięgać aż do marginesu od góry.
function headerLayout(config, artTop, artHeight, artScale) {
  const top = artTop + artHeight * config.titleMargin;
  const titleY = top + 34.4 * artScale;
  const title = config.title.trim(), subtitle = config.subtitle.trim();
  const subtitleY = title ? titleY + 28 * artScale : top + 14 * artScale;
  const bottom = subtitle ? subtitleY + 12 * artScale : title ? titleY + 18 * artScale : top;
  return { titleY, subtitleY, bottom };
}

export function escapeXml(value) {
  return String(value ?? "").replace(/[<>&"']/g, character => ({
    "<": "&lt;", ">": "&gt;", "&": "&amp;", '"': "&quot;", "'": "&apos;",
  })[character]);
}

function textUnits(text) {
  return [...String(text)].reduce((total, character) => total + (/[MW@]/.test(character) ? 0.9 : /[iljt .,'’]/.test(character) ? 0.3 : 0.58), 0);
}

function fittedTextSize(text, size, maxWidth) {
  return Math.min(size, maxWidth / Math.max(textUnits(text), 1));
}

function textLine(text, x, y, size, attributes = "", maxWidth = Infinity) {
  const fittedSize = fittedTextSize(text, size, maxWidth);
  return `<text x="${x}" y="${y}" text-anchor="middle" font-size="${fittedSize.toFixed(2)}" ${attributes}>${escapeXml(text)}</text>`;
}

function renderLabel(node, config) {
  const { x, y, width, height, fontSize, person, number } = node;
  const textWidth = width - Math.min(16, width * 0.15);
  const left = -width / 2;
  const top = -height / 2;
  const shape = config.labelStyle === "lisc"
    ? `<path d="M ${left},0 C ${left},${top * 1.6} ${-left},${top * 1.6} ${-left},0 C ${-left},${-top * 1.6} ${left},${-top * 1.6} ${left},0 Z"/>`
    : `<rect x="${left}" y="${top}" width="${width}" height="${height}" rx="${Math.min(9, height * 0.15)}"/>`;
  const name = person?.name || "Nieznany przodek";
  const date = person ? [person.born, person.died].filter(Boolean).join("–") : "";
  let output = `<g class="person-label" data-number="${escapeXml(number)}" data-generation="${node.generation}"${node.isSibling ? ' data-sibling="true"' : ""} transform="translate(${x.toFixed(2)} ${y.toFixed(2)})"><title>${escapeXml(name)}${date ? ` (${date})` : ""}</title><rect x="${left}" y="${top}" width="${width}" height="${height}" fill="transparent" pointer-events="all"/>`;
  if (config.labelStyle === "halo") {
    output += `<ellipse cx="0" cy="0" rx="${width / 2}" ry="${height / 2}" fill="url(#cartouche-halo)" opacity="${config.labelOpacity}"${config.haloBlur ? ' filter="url(#cartouche-blur)"' : ""} pointer-events="none"/>`;
  } else if (config.labelStyle !== "tekst") {
    output += `<g fill="${config.paper}" fill-opacity="${config.labelOpacity}" stroke="${config.accent}" stroke-width="${node.generation === 0 ? 1.8 : 0.8}">${shape}</g>`;
    if (node.generation === 0 && config.labelStyle === "kartusz" && width > 14 && height > 14) output += `<rect x="${left + 5}" y="${top + 5}" width="${width - 10}" height="${height - 10}" rx="5" fill="none" stroke="${config.accent}" stroke-width="0.5"/>`;
  }
  const outline = config.labelStyle === "tekst" ? `stroke="${config.paper}" stroke-width="3" paint-order="stroke" stroke-linejoin="round"` : "";
  output += `<g fill="${config.ink}" ${outline}>`;
  const totalHeight = node.lines.reduce((sum, line) => sum + line.scale * fontSize * 1.15, 0);
  let baseline = -totalHeight / 2;
  for (const line of node.lines) {
    const size = fontSize * line.scale;
    output += textLine(line.text, 0, baseline + size * 0.85, size,
      line.bold ? 'font-weight="600"' : line.dates ? 'font-variant-numeric="lining-nums"' : "", textWidth);
    baseline += size * 1.15;
  }
  return output + "</g></g>";
}

export function renderPoster(people, input, backgroundHref) {
  const layout = layoutPoster(people, input);
  const { config, nodes, byNumber, width, height, artTop, artHeight, artLeft, artWidth, artScale } = layout;
  const background = BACKGROUNDS.find(item => item.id === config.background);
  const href = backgroundHref || `/poster/assets/${background.file}.jpg`;
  const known = new Set(nodes.filter(node => node.person).map(node => node.personId)).size;
  const generations = Math.max(...nodes.map(node => node.generation)) + 1;
  const labels = nodes.map(node => renderLabel(node, config)).join("");
  const relations = nodes.filter(node => node.number > 1).map(parent => ({ parent, child: byNumber.get(Math.floor(parent.number / 2)) }));
  for (const child of nodes.filter(node => node.isSibling)) {
    for (const parentNumber of [2, 3]) {
      const parent = byNumber.get(parentNumber);
      if (parent?.personId && child.person.parents.includes(parent.personId)) relations.push({ parent, child });
    }
  }
  // Linie między dwoma pokoleniami wyginają się na wspólnej wysokości (środek między rzędami), więc się nie przeplatają.
  const curve = (x1, y1, x2, y2, middle1, middle2) => `M ${x1},${y1} C ${x1},${middle1} ${x2},${middle2} ${x2},${y2}`;
  const between = (value, a, b) => Math.max(Math.min(a, b), Math.min(Math.max(a, b), value));
  // Linia: od dziecka pionowo w górę do wolnego pasa między pokoleniami, w pasie w bok, potem pionowo do rodzica.
  // Pionowe odcinki mieszczą się w korytarzach między sąsiednimi podpisami, więc linia nie biegnie przez cudze napisy.
  const connect = (child, parent) => {
    const startY = child.y - child.height / 2;
    const endY = parent.y + parent.height / 2;
    const low = layout.rowEdges.get(child.generation), high = layout.rowEdges.get(parent.generation);
    const lane = low && high ? [low.top + layout.bendShift(child.x), high.bottom + layout.bendShift(parent.x)] : null;
    if (!lane || lane[0] - lane[1] < 4 * artScale) {
      const middle = (child.rowY + parent.rowY) / 2;
      return curve(child.x, startY, parent.x, endY, between(middle + child.bendY, startY, endY), between(middle + parent.bendY, startY, endY));
    }
    // Skręt w bok płynie wzdłuż (wygiętego) pasa: na wysokości u ∈ [0, 1] pasa linia jest w x = x_dziecka + dx·S(u).
    // Dla dwóch linii o tej samej kolejności dzieci i rodziców na każdej wysokości pasa jedna jest na lewo od drugiej,
    // więc nie mogą się przeciąć — także przy wygiętych pokoleniach.
    const bottomAt = x => low.top + layout.bendShift(x) - 2 * artScale;
    const topAt = x => high.bottom + layout.bendShift(x) + 2 * artScale;
    const enter = Math.min(startY, bottomAt(child.x)), leave = Math.max(endY, topAt(parent.x));
    const steps = Math.max(4, Math.min(24, Math.ceil(Math.abs(parent.x - child.x) / (6 * artScale)) + 4));
    const points = [];
    for (let index = 0; index <= steps; index++) {
      const u = index / steps, x = child.x + (parent.x - child.x) * u * u * (3 - 2 * u);
      points.push([x, index === 0 ? enter : index === steps ? leave : bottomAt(x) + (topAt(x) - bottomAt(x)) * u]);
    }
    return `M ${child.x},${startY} L ${child.x},${enter} ${smoothPath(points)} L ${parent.x},${endY}`;
  };
  // Rodzeństwo u korzeni z tymi samymi rodzicami: jedna linia od każdego rodzica do wspólnego węzła, od węzła do dzieci
  // (zamiast krzyżyka linii dziecko–rodzic).
  const father = byNumber.get(2), mother = byNumber.get(3);
  const shared = father?.personId && mother?.personId ? nodes.filter(node => node.generation === 0
    && (node.number === 1 || [father.personId, mother.personId].every(id => node.person?.parents?.includes(id)))) : [];
  const joined = shared.length > 1;
  // kolor linii: wg kolejności dziecka w jego rzędzie (od lewej), albo jeden kolor ornamentu
  const order = new Map();
  for (const generation of new Set(nodes.map(node => node.generation))) {
    nodes.filter(node => node.generation === generation).sort((left, right) => left.x - right.x).forEach((node, index) => order.set(node, index));
  }
  const colorOf = child => config.lineColors === "rodziny" ? LINE_COLORS[order.get(child) % LINE_COLORS.length] : config.accent;
  // pod każdą linią cienka obwódka w kolorze papieru: linie biegnące blisko siebie albo mijające się są oddzielone
  // suwaki „Grubość linii”, „Wyrazistość linii” i „Obwódka” (0 = bez obwódki)
  const casing = config.lineCasing > 0
    ? d => `<path d="${d}" stroke="${config.paper}" stroke-width="${(config.lineWidth + 4.4 * config.lineCasing).toFixed(2)}" stroke-opacity="${(0.4 + 0.6 * config.lineCasing).toFixed(2)}"/>`
    : () => "";
  const line = (d, color, attributes) => `${casing(d)}<path ${attributes} d="${d}" stroke="${color}"/>`;
  let connections = "";
  if (config.showConnections) {
    connections = relations.filter(({ child, parent }) => !(joined && shared.includes(child) && (parent === father || parent === mother)))
      .map(({ parent, child }) => line(connect(child, parent), colorOf(child), `data-child="${escapeXml(child.number)}" data-parent="${escapeXml(parent.number)}"`)).join("");
    if (joined) {
      const top = Math.min(...shared.map(node => node.y - node.height / 2));
      const parentsBottom = Math.max(father.y + father.height / 2, mother.y + mother.height / 2);
      const knot = { x: shared.reduce((sum, node) => sum + node.x, 0) / shared.length, y: top - Math.max(6 * artScale, (top - parentsBottom) * 0.3) };
      for (const parent of [father, mother]) {
        const endY = parent.y + parent.height / 2, middle = (knot.y + endY) / 2;
        connections += line(curve(knot.x, knot.y, parent.x, endY, middle, middle), config.accent, `data-child="family" data-parent="${parent.number}"`);
      }
      for (const child of shared) {
        const startY = child.y - child.height / 2, middle = (startY + knot.y) / 2;
        connections += line(curve(child.x, startY, knot.x, knot.y, middle, middle), config.accent, `data-child="${escapeXml(child.number)}" data-parent="family"`);
      }
    }
  }
  const headerY = layout.header.titleY;
  const footerY = artTop + artHeight - 30 * artScale;
  const header = textLine(config.title, width / 2, headerY, 43 * artScale, `fill="${config.titleColor}" data-title="main"`, 1100 * artScale)
    + textLine(config.subtitle, width / 2, layout.header.subtitleY, 15 * artScale, `fill="${config.subtitleColor}" data-title="subtitle" letter-spacing="${artScale}"`, 1050 * artScale);
  const stops = [0, 0.35, 0.5, 0.65, 0.8, 0.9, 1].map(radius => `<stop offset="${radius}" stop-color="${config.paper}" stop-opacity="${Math.max(0, 1 - Math.max(0, radius - 0.35) / 0.65) ** config.haloDecay}"/>`).join("");
  const footer = config.footerText.replace(/\{(people|generations)\}/g, (_, key) => key === "people" ? known : generations);
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${width} ${height}" width="${config.width}mm" height="${config.height}mm" role="img" aria-labelledby="poster-title poster-description" font-family="${escapeXml(FONTS[config.font])}">
<title id="poster-title">${escapeXml(config.title)}</title><desc id="poster-description">Drzewo przodków: ${escapeXml(people[config.root].name)}. ${known} osób, ${generations} pokoleń.</desc>
${config.labelStyle === "halo" ? `<defs><radialGradient id="cartouche-halo">${stops}</radialGradient><filter id="cartouche-blur" x="-75%" y="-75%" width="250%" height="250%" primitiveUnits="objectBoundingBox"><feGaussianBlur stdDeviation="${config.haloBlur}"/></filter></defs>` : ""}
<rect width="${width}" height="${height}" fill="${config.paper}"/>
<image href="${escapeXml(href)}" x="${artLeft}" y="${artTop}" width="${artWidth}" height="${artHeight}" preserveAspectRatio="xMidYMid meet"/>
${config.showFrame ? `<rect data-decoration="frame" x="19" y="19" width="${width - 38}" height="${height - 38}" fill="none" stroke="${config.accent}" stroke-opacity="0.55" stroke-width="0.9"/>` : ""}
${config.showGuides ? `<path data-decoration="guides" d="M 30,48 V 30 H 48 M ${width - 48},30 H ${width - 30} V 48 M 30,${height - 48} V ${height - 30} H 48 M ${width - 48},${height - 30} H ${width - 30} V ${height - 48}" fill="none" stroke="${config.accent}" stroke-width="1.5"/>` : ""}
<g stroke-width="${config.lineWidth}" stroke-opacity="${config.lineOpacity}" fill="none" stroke-linecap="round" stroke-linejoin="round">${connections}</g>
${labels}${header}
${config.showFooter && footer ? textLine(footer, width / 2, footerY, 12 * artScale, `fill="${config.ink}" data-footer="true"`, artWidth - 100 * artScale) : ""}
</svg>`;
  const dpi = Math.round(5016 / (config.width * artScale / 25.4));
  const smallestText = Math.min(...nodes.flatMap(node => node.lines.map(line => {
    return fittedTextSize(line.text, node.fontSize * line.scale, node.width - Math.min(16, node.width * 0.15));
  }))) * config.width / width * 72 / 25.4;
  let overlaps = 0;
  const outOfBounds = nodes.filter(node => node.x - node.width / 2 < 0 || node.x + node.width / 2 > width
    || node.y - node.height / 2 < 0 || node.y + node.height / 2 > height).length;
  for (const [index, node] of nodes.entries()) {
    for (const other of nodes.slice(index + 1)) {
      if (Math.abs(node.x - other.x) < (node.width + other.width) / 2 && Math.abs(node.y - other.y) < (node.height + other.height) / 2) overlaps++;
    }
  }
  return { svg, known, generations, positions: nodes.length, dpi, smallestText, overlaps, outOfBounds, layout, relations };
}

export function printDocument(svg, config) {
  return `<!doctype html><html lang="pl"><head><meta charset="utf-8"><meta name="robots" content="noindex,nofollow"><title>${escapeXml(config.title)}</title><style>@page{size:${config.width}mm ${config.height}mm;margin:0}html,body{margin:0;padding:0;width:${config.width}mm;height:${config.height}mm}svg{display:block;width:100%;height:100%;break-inside:avoid}*{-webkit-print-color-adjust:exact;print-color-adjust:exact}</style></head><body>${svg}</body></html>`;
}
