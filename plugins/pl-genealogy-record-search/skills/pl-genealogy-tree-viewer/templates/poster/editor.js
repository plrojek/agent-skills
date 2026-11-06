// Poster configurator of pl-genealogy-tree-viewer. Made by Applied AI (https://appliedai.dev),
// https://github.com/plrojek/agent-skills. Posters themselves carry no credit; this page's footer does.
import { BACKGROUNDS, FORMATS, generationSettings, normalizeConfig, renderPoster, rootSiblings } from "./poster.js";

// Publikacja statyczna (publish.py zapisuje poster/ z <meta name="poster-static">): bez serwera podglądu.
// Dane z people.json obok strony, ścieżki względne, SVG i PDF składane w przeglądarce (bez okna druku).
const STATIC = Boolean(document.querySelector('meta[name="poster-static"]'));
const ASSETS = STATIC ? "assets/" : "/poster/assets/";
const backgroundUrl = () => `${ASSETS}${BACKGROUNDS.find(item => item.id === config.background).file}.jpg`;

const form = document.querySelector("#poster-form");
const sheet = document.querySelector("#poster-sheet");
const storageKey = "genealogia-poster-v1";
let people;
let config = normalizeConfig();
let currentPoster;
let zoom = 1;
let toastTimer;
let drag;
let selectedCard = "1";
let cardOptionsKey;
const scaleTargets = new Set();   // pokolenia zaznaczone pod suwakiem „Wielkość wybranych pokoleń”
const GENERATION_NAMES = ["Osoba u korzeni i rodzeństwo", "Rodzice", "Dziadkowie", "Pradziadkowie"];

function pointsFor(node) {
  return node.fontSize * config.width / currentPoster.layout.width * 72 / 25.4;
}

function syncDetailControls() {
  const generations = document.querySelector("#generation-select");
  if (generations.options.length !== config.generations) {
    const selected = Math.min(Number(generations.value || 0), config.generations - 1);
    const names = ["U korzeni i rodzeństwo", "Rodzice", "Dziadkowie", "Pradziadkowie"];
    generations.replaceChildren(...Array.from({ length: config.generations }, (_, generation) => new Option(`${generation + 1}. ${names[generation] || "Dalsi przodkowie"}`, generation)));
    generations.value = selected;
  }
  const generation = Number(generations.value);
  const settings = generationSettings(config, generation);
  const customized = Object.hasOwn(config.generationSettings, generation);
  document.querySelector("#generation-custom").checked = customized;
  for (const control of document.querySelectorAll("[data-generation-setting]")) {
    control.disabled = !customized;
    if (control.type === "checkbox") control.checked = settings[control.dataset.generationSetting];
    else control.value = settings[control.dataset.generationSetting] ?? "";
  }
  const row = currentPoster.layout.nodes.filter(node => node.generation === generation);
  const sizes = row.map(pointsFor);
  const widths = row.map(node => node.width * config.width / currentPoster.layout.width);
  document.querySelector("#generation-info").textContent = row.length
    ? `Kartusze: ${row.length}. Szerokość: ${Math.min(...widths).toFixed(1)}–${Math.max(...widths).toFixed(1)} mm. Tekst bazowy: ${Math.min(...sizes).toFixed(1)}–${Math.max(...sizes).toFixed(1)} pkt. Długie napisy dopasowują się do szerokości.`
    : "Brak osób w tym pokoleniu w wybranej gałęzi.";

  const cards = document.querySelector("#card-select");
  const optionsKey = `${config.root}|${currentPoster.layout.nodes.map(node => node.number).join("|")}`;
  if (optionsKey !== cardOptionsKey) {
    cards.replaceChildren(...currentPoster.layout.nodes.map(node => new Option(`${node.person?.name || "Nieznany przodek"} · pok. ${node.generation + 1}${node.isSibling ? " · rodzeństwo" : ""}`, node.number)));
    cardOptionsKey = optionsKey;
  }
  if (!currentPoster.layout.nodes.some(node => String(node.number) === selectedCard)) selectedCard = "1";
  cards.value = selectedCard;
  const individual = config.cardSettings[selectedCard] || {};
  document.querySelector("#card-scale").value = individual.scale ?? 1;
  document.querySelector("#card-scale-value").textContent = `${Math.round((individual.scale ?? 1) * 100)}%`;
  document.querySelector("#card-fontSize").value = individual.fontSize ?? "";
  const selected = currentPoster.layout.nodes.find(node => String(node.number) === selectedCard);
  document.querySelector("#card-info").textContent = `Rozmiar bazowy tekstu: ${pointsFor(selected).toFixed(1)} pkt. Puste pole dziedziczy rozmiar pokolenia i skalę kartusza.`;
}

function syncGenerationScale() {
  for (const generation of [...scaleTargets]) if (generation >= config.generations) scaleTargets.delete(generation);
  document.querySelector("#generation-chips").replaceChildren(...Array.from({ length: config.generations }, (_, generation) => {
    const chip = document.createElement("button");
    const scale = config.generationScale[generation];
    chip.type = "button";
    chip.className = "generation-chip";
    chip.dataset.generation = generation;
    chip.textContent = scale ? `${generation + 1} · ${Math.round(scale * 100)}%` : String(generation + 1);
    chip.title = `${generation + 1}. ${GENERATION_NAMES[generation] || "Dalsi przodkowie"}`;
    chip.setAttribute("aria-pressed", scaleTargets.has(generation));
    return chip;
  }));
  const slider = document.querySelector("#generationScale");
  const first = Math.min(...scaleTargets);
  slider.disabled = !scaleTargets.size;
  slider.value = scaleTargets.size ? config.generationScale[first] ?? 1 : 1;
  const values = new Set([...scaleTargets].map(generation => config.generationScale[generation] ?? 1));
  document.querySelector("#generationScale-value").textContent = !scaleTargets.size ? "—"
    : values.size > 1 ? "różne · suwak ustawi wszystkim" : `${Math.round(Number(slider.value) * 100)}%`;
}

function fitPoster() {
  if (!currentPoster) return;
  const container = document.querySelector("#canvas-scroll");
  const mobile = window.matchMedia("(max-width: 760px)").matches;
  const availableWidth = container.clientWidth - (mobile ? 0 : 34);
  const availableHeight = mobile ? Infinity : Math.max(100, container.clientHeight - 66);
  const fittedWidth = Math.min(availableWidth, availableHeight * currentPoster.layout.width / currentPoster.layout.height);
  sheet.style.width = `${fittedWidth * zoom}px`;
}

function notify(message) {
  const toast = document.querySelector("#toast");
  toast.textContent = message;
  toast.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { toast.hidden = true; }, 4500);
}

function syncControls() {
  for (const element of form.elements) {
    if (!element.name || !Object.hasOwn(config, element.name)) continue;
    if (element.type === "checkbox") element.checked = config[element.name];
    else element.value = config[element.name];
  }
  document.querySelector("#custom-dimensions").hidden = config.format !== "custom";
  document.querySelector("#halo-controls").hidden = config.labelStyle !== "halo";
  for (const button of document.querySelectorAll("[data-background]")) button.setAttribute("aria-pressed", button.dataset.background === config.background);
  for (const button of document.querySelectorAll("[data-label-style]")) button.setAttribute("aria-pressed", button.dataset.labelStyle === config.labelStyle);
  for (const key of ["generations", "labelScale", "labelOpacity"]) {
    document.querySelector(`#${key}-value`).textContent = key === "generations" ? config[key] : `${Math.round(config[key] * 100)}%`;
  }
  document.querySelector("#haloDecay-value").textContent = config.haloDecay.toFixed(1);
  document.querySelector("#haloBlur-value").textContent = `${Math.round(config.haloBlur * 100)}%`;
  document.querySelector("#bend-value").textContent = `${Math.round(config.bend * 100)}%`;
  document.querySelector("#verticalSpread-value").textContent = `${Math.round(config.verticalSpread * 100)}%`;
  document.querySelector("#lineWidth-value").textContent = `${(config.lineWidth * config.width / currentPoster.layout.width).toFixed(2)} mm`;
  document.querySelector("#lineOpacity-value").textContent = `${Math.round(config.lineOpacity * 100)}%`;
  document.querySelector("#lineCasing-value").textContent = config.lineCasing ? `${Math.round(config.lineCasing * 100)}%` : "bez obwódki";
  document.querySelector("#compact-value").textContent = `${Math.round(config.compact * 100)}%`;
  document.querySelector("#rootDrop-value").textContent = `${(currentPoster.layout.artHeight * config.rootDrop * config.width / currentPoster.layout.width).toFixed(1)} mm`;
  document.querySelector("#titleMargin-value").textContent = `${(currentPoster.layout.artHeight * config.titleMargin * config.width / currentPoster.layout.width).toFixed(1)} mm`;
  const siblings = rootSiblings(people, config.root);
  document.querySelector("#siblings-info").textContent = siblings.length
    ? `Rodzeństwo w danych: ${siblings.length}. Także przyrodnie, jeśli potwierdzono wspólnego rodzica. Ustawienia pokolenia 1 obejmują całą tę grupę.`
    : "Brak potwierdzonego rodzeństwa w obecnych danych.";
  const selected = document.querySelector("#selected-person");
  selected.replaceChildren();
  const name = document.createElement("strong");
  name.textContent = people[config.root].name;
  const details = document.createElement("span");
  details.textContent = `${people[config.root].born || "Rok nieznany"} · początek drzewa`;
  selected.append(name, details);
  syncDetailControls();
}

// Nowy SVG przy każdym ruchu kartusza, ale ten sam element ilustracji, gdy się nie zmieniła: bez ponownego
// dekodowania kilkumegabajtowego JPEG-a przy każdym ruchu myszy (Safari potrafi wtedy mignąć).
function showSvg(markup) {
  const oldImage = sheet.querySelector("svg > image");
  const template = document.createElement("template");
  template.innerHTML = markup;
  const image = template.content.querySelector("svg > image");
  if (oldImage && image && ["href", "x", "y", "width", "height"].every(name => oldImage.getAttribute(name) === image.getAttribute(name))) image.replaceWith(oldImage);
  sheet.replaceChildren(template.content);
}

function render(persist = true) {
  config = normalizeConfig(config);
  currentPoster = renderPoster(people, config, backgroundUrl());
  showSvg(currentPoster.svg);
  for (const label of sheet.querySelectorAll("[data-number]")) {
    label.setAttribute("tabindex", "0");
    label.setAttribute("role", "button");
    label.setAttribute("aria-label", `${label.querySelector("title").textContent}. Przesuń podpis strzałkami.`);
  }
  fitPoster();
  syncControls();
  syncGenerationScale();
  document.querySelector("#poster-summary").textContent = `${currentPoster.known} osób · ${currentPoster.generations} pokoleń · ${FORMATS[config.format].name}`;
  document.querySelector("#print-info").textContent = `${config.width} × ${config.height} mm · ilustracja ok. ${currentPoster.dpi} dpi · ${STATIC ? "tekst wektorowy w SVG" : "tekst wektorowy"}`;
  const warning = document.querySelector("#layout-warning");
  const warnings = [];
  if (currentPoster.outOfBounds) warnings.push(`Kartusze poza arkuszem: ${currentPoster.outOfBounds}. Zmniejsz odstępy lub wygięcie, przesuń podpisy albo zwiększ wysokość papieru.`);
  if (currentPoster.overlaps) warnings.push(`Nakładające się kartusze: ${currentPoster.overlaps}. Przesuń podpisy lub zmniejsz ich rozmiar.`);
  if (currentPoster.smallestText < 7) warnings.push(`Najmniejszy tekst ma ok. ${currentPoster.smallestText.toFixed(1)} pkt. Zwiększ tekst pokolenia, wybierz większy papier lub mniej pokoleń.`);
  if (currentPoster.dpi < 140) warnings.push(`Tło ma ${currentPoster.dpi} dpi w tym formacie. Sprawdź z drukarnią akceptowalną rozdzielczość.`);
  warning.textContent = warning.title = warnings.join(" ");
  warning.hidden = !warnings.length;
  document.querySelector("#drag-hint").hidden = Boolean(warnings.length);
  if (persist) {
    try { localStorage.setItem(storageKey, JSON.stringify(config)); }
    catch { document.querySelector("#save-state").textContent = "· zapis lokalny niedostępny"; }
  }
}

function download(blob, filename) {
  const href = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = href; link.download = filename; link.click();
  setTimeout(() => URL.revokeObjectURL(href), 30000);
}

async function backgroundDataUrl() {
  const response = await fetch(backgroundUrl());
  if (!response.ok) throw new Error("Nie można wczytać ilustracji drzewa.");
  const blob = await response.blob();
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => reject(new Error("Nie można wczytać ilustracji drzewa."));
    reader.readAsDataURL(blob);
  });
}

// Bez serwera: ten sam renderer co CLI, ilustracja osadzona w pliku.
// PDF (06.11.2026): okno druku nie nadaje się do plakatu — Safari ignoruje @page i tnie arkusz na kartki A4.
// Przeglądarka rysuje ten sam SVG na płótnie (fonty systemowe, poświaty i gradienty dokładnie jak w podglądzie),
// a PDF składamy sami: jedna strona w rozmiarze plakatu, jeden obraz JPEG. Napisy są tu rastrem; wektorowe zostają w SVG.
const PDF_MAX_DPI = 300, PDF_MAX_AREA = 40e6, PDF_MAX_SIDE = 16384;

function svgImage(svg) {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(new Blob([svg], { type: "image/svg+xml" }));
    const img = new Image();
    img.onload = () => resolve({ img, url });
    img.onerror = () => { URL.revokeObjectURL(url); reject(new Error("Przeglądarka nie narysowała plakatu.")); };
    img.src = url;
  });
}

// Rozdzielczość: do 300 dpi, ale płótno najwyżej ok. 40 mln pikseli i 16384 px na bok. iPhone ma limit 16,7 mln
// i przekroczenie daje puste płótno bez błędu — dlatego po rysowaniu sprawdzamy piksel (papier zakrywa cały arkusz)
// i w razie pustki próbujemy z połową pikseli.
async function rasterPoster(svg) {
  const wIn = config.width / 25.4, hIn = config.height / 25.4;
  const size = `width="${config.width}mm" height="${config.height}mm"`;
  if (!svg.includes(size)) throw new Error("Nie można ustalić rozmiaru plakatu do PDF.");
  let dpi = Math.min(PDF_MAX_DPI, Math.sqrt(PDF_MAX_AREA / (wIn * hIn)), PDF_MAX_SIDE / Math.max(wIn, hIn));
  for (let attempt = 0; attempt < 5; attempt++, dpi /= Math.SQRT2) {
    const w = Math.round(wIn * dpi), h = Math.round(hIn * dpi);
    // Wymiar w pikselach w samym SVG: Safari rysuje obraz SVG w jego naturalnej wielkości i dopiero skaluje (rozmyte napisy).
    const { img, url } = await svgImage(svg.replace(size, `width="${w}" height="${h}"`));
    const canvas = document.createElement("canvas");
    canvas.width = w; canvas.height = h;
    let blob = null;
    try {
      const ctx = canvas.getContext("2d");
      if (ctx) {
        ctx.drawImage(img, 0, 0, w, h);
        if (ctx.getImageData(1, 1, 1, 1).data[3] === 255) blob = await new Promise(done => canvas.toBlob(done, "image/jpeg", 0.92));
      }
    } catch { blob = null; }
    finally { URL.revokeObjectURL(url); canvas.width = canvas.height = 0; }
    if (blob) return { jpeg: new Uint8Array(await blob.arrayBuffer()), w, h, dpi: Math.round(dpi) };
  }
  throw new Error("Przeglądarka nie zmieściła plakatu w pamięci. Pobierz SVG albo wybierz mniejszy format.");
}

// Najprostszy poprawny PDF: katalog, strona w rozmiarze plakatu (punkty = mm · 72 / 25,4), obraz /DCTDecode, treść
// „narysuj obraz na całej stronie”, tytuł jako UTF-16 (<FEFF…>), żeby polskie litery przetrwały. Poza strumieniem JPEG
// wszystko jest ASCII, więc przesunięcia w tablicy xref to po prostu długości kawałków w bajtach.
function pdfFromJpeg({ jpeg, w, h }) {
  const pt = mm => (mm * 72 / 25.4).toFixed(2);
  const W = pt(config.width), H = pt(config.height);
  const utf16 = text => "<FEFF" + Array.from({ length: text.length }, (_, i) => text.charCodeAt(i).toString(16).padStart(4, "0")).join("").toUpperCase() + ">";
  const enc = new TextEncoder(), parts = [], offsets = [];
  let length = 0;
  const add = chunk => { const bytes = typeof chunk === "string" ? enc.encode(chunk) : chunk; parts.push(bytes); length += bytes.length; };
  const obj = (n, body) => { offsets[n] = length; add(`${n} 0 obj\n${body}\nendobj\n`); };
  add("%PDF-1.4\n");
  obj(1, "<< /Type /Catalog /Pages 2 0 R >>");
  obj(2, "<< /Type /Pages /Kids [3 0 R] /Count 1 >>");
  obj(3, `<< /Type /Page /Parent 2 0 R /MediaBox [0 0 ${W} ${H}] /Resources << /XObject << /Im0 4 0 R >> >> /Contents 5 0 R >>`);
  offsets[4] = length;
  add(`4 0 obj\n<< /Type /XObject /Subtype /Image /Width ${w} /Height ${h} /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length ${jpeg.length} >>\nstream\n`);
  add(jpeg);
  add("\nendstream\nendobj\n");
  const draw = `q ${W} 0 0 ${H} 0 0 cm /Im0 Do Q`;
  obj(5, `<< /Length ${draw.length} >>\nstream\n${draw}\nendstream`);
  obj(6, `<< /Title ${utf16(config.title || "")} /Creator (Plakaty do druku) >>`);
  const xref = length;
  add(`xref\n0 7\n0000000000 65535 f \n${offsets.slice(1).map(o => `${String(o).padStart(10, "0")} 00000 n \n`).join("")}`
    + `trailer\n<< /Size 7 /Root 1 0 R /Info 6 0 R >>\nstartxref\n${xref}\n%%EOF\n`);
  return new Blob(parts, { type: "application/pdf" });
}

const pdfName = () => `${(config.title || "").replace(/[\\/:*?"<>|]+/g, " ").replace(/\s+/g, " ").trim() || "Drzewo-plakat"}.pdf`;
const cm = mm => (mm / 10).toLocaleString("pl-PL", { maximumFractionDigits: 1 });

async function downloadPosterStatic(format, button) {
  const initial = button.textContent;
  button.disabled = true;
  button.textContent = "Przygotowuję plik…";
  try {
    const poster = renderPoster(people, config, await backgroundDataUrl());
    if (format === "svg") {
      download(new Blob([poster.svg], { type: "image/svg+xml" }), `Drzewo-plakat-${config.background}.svg`);
      notify("SVG jest gotowy. Ilustracja jest osadzona w pliku.");
      return;
    }
    const raster = await rasterPoster(poster.svg);
    download(pdfFromJpeg(raster), pdfName());
    notify(`PDF jest gotowy: ${cm(config.width)} × ${cm(config.height)} cm, ok. ${raster.dpi} dpi. Drukuj w skali 100%, bez dopasowania do strony. Napisy wektorowe ma plik SVG.`);
  } catch (error) { notify(error.message); }
  finally { button.disabled = false; button.textContent = initial; }
}

async function downloadPoster(format, button) {
  if (STATIC) return downloadPosterStatic(format, button);
  const initial = button.textContent;
  button.disabled = true;
  button.textContent = "Przygotowuję plik…";
  try {
    const response = await fetch(`/api/export/${format}`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(config),
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || "Nie udało się przygotować pliku.");
    }
    download(await response.blob(), `Drzewo-plakat-${config.background}.${format}`);
    notify(format === "pdf" ? "PDF jest gotowy. Drukuj w skali 100%, bez dopasowania do strony." : "SVG jest gotowy. Ilustracja jest osadzona w pliku.");
  } catch (error) { notify(error.message); }
  finally { button.disabled = false; button.textContent = initial; }
}

form.addEventListener("submit", event => event.preventDefault());
function updateSetting(event) {
  const element = event.target;
  if (!element.name || !Object.hasOwn(config, element.name) || !people) return;
  if (element.type === "number" && event.type === "input") return;
  if (element.type !== "number" && event.type === "change") return;
  if (element.type === "number" && (!element.value || !element.checkValidity())) {
    element.reportValidity(); return;
  }
  config[element.name] = element.type === "checkbox" ? element.checked
    : ["range", "number"].includes(element.type) ? Number(element.value) : element.value;
  render();
}
form.addEventListener("input", updateSetting);
form.addEventListener("change", updateSetting);

document.querySelector("#generation-select").addEventListener("change", syncDetailControls);
document.querySelector("#generation-chips").addEventListener("click", event => {
  const chip = event.target.closest("[data-generation]");
  if (!chip || !people) return;
  const generation = Number(chip.dataset.generation);
  if (scaleTargets.has(generation)) scaleTargets.delete(generation); else scaleTargets.add(generation);
  syncGenerationScale();
  document.querySelector(`#generation-chips [data-generation="${generation}"]`)?.focus();
});
document.querySelector("#generationScale").addEventListener("input", event => {
  if (!people || !scaleTargets.size) return;
  const scale = Number(event.target.value);
  for (const generation of scaleTargets) {
    if (Math.abs(scale - 1) < 0.001) delete config.generationScale[generation];
    else config.generationScale[generation] = scale;
  }
  render();
});
document.querySelector("#generation-custom").addEventListener("change", event => {
  const generation = document.querySelector("#generation-select").value;
  if (event.target.checked) config.generationSettings[generation] = generationSettings(config, generation);
  else delete config.generationSettings[generation];
  render();
});
for (const control of document.querySelectorAll("[data-generation-setting]")) control.addEventListener("change", () => {
  if (control.type === "number" && control.value && !control.checkValidity()) { control.reportValidity(); return; }
  const generation = document.querySelector("#generation-select").value;
  const key = control.dataset.generationSetting;
  if (!config.generationSettings[generation]) return;
  if (control.type === "checkbox") config.generationSettings[generation][key] = control.checked;
  else if (control.value) config.generationSettings[generation][key] = Number(control.value);
  else delete config.generationSettings[generation][key];
  render();
});

function selectCard(number, reveal = false) {
  selectedCard = String(number);
  // klik w kartusz na podglądzie: na komputerze panel przewija się do „Wybrana osoba” (na telefonie formularz jest pod podglądem)
  if (reveal && window.matchMedia("(min-width: 761px)").matches) document.querySelector("#card-panel").scrollIntoView({ block: "nearest", behavior: "smooth" });
  syncDetailControls();
  for (const label of sheet.querySelectorAll("[data-number]")) label.classList.toggle("is-selected", label.dataset.number === selectedCard);
}
document.querySelector("#card-select").addEventListener("change", event => selectCard(event.target.value));
document.querySelector("#card-scale").addEventListener("input", event => {
  config.cardSettings[selectedCard] = { ...config.cardSettings[selectedCard], scale: Number(event.target.value) };
  render(); selectCard(selectedCard);
});
document.querySelector("#card-fontSize").addEventListener("change", event => {
  const control = event.target;
  if (control.value && !control.checkValidity()) { control.reportValidity(); return; }
  config.cardSettings[selectedCard] ||= {};
  if (control.value) config.cardSettings[selectedCard].fontSize = Number(control.value);
  else delete config.cardSettings[selectedCard].fontSize;
  render(); selectCard(selectedCard);
});
document.querySelector("#reset-card").addEventListener("click", () => {
  delete config.cardSettings[selectedCard]; render(); selectCard(selectedCard);
});

document.querySelector("#background-options").innerHTML = BACKGROUNDS.map(background => `<button type="button" class="background-option" data-background="${background.id}" aria-pressed="false" title="${background.description}"><img src="${ASSETS}${background.file}-thumb.jpg" alt="" width="140" height="79"><span>${background.name}</span></button>`).join("");
document.querySelector("#background-options").addEventListener("click", event => {
  const button = event.target.closest("[data-background]");
  if (!button || !people) return;
  config.background = button.dataset.background; render();
});
for (const button of document.querySelectorAll("[data-label-style]")) button.addEventListener("click", () => {
  if (!people) return;
  config.labelStyle = button.dataset.labelStyle; render();
});

const search = document.querySelector("#person-search");
const results = document.querySelector("#person-results");
function searchPeople() {
  const query = search.value.trim().toLocaleLowerCase("pl");
  results.replaceChildren();
  results.hidden = !query || !people;
  if (results.hidden) return;
  const matches = Object.entries(people).filter(([, person]) => person.name.toLocaleLowerCase("pl").includes(query)).slice(0, 30);
  for (const [personId, person] of matches) {
    const button = document.createElement("button");
    button.type = "button";
    const label = document.createElement("span"); label.textContent = person.name;
    const dates = document.createElement("small"); dates.textContent = [person.born, person.died].filter(Boolean).join("–") || "Lata nieznane";
    button.append(label, dates);
    button.addEventListener("click", () => {
      config.root = personId; config.positions = {}; config.cardSettings = {}; selectedCard = "1";
      search.value = ""; results.hidden = true; render();
    });
    results.append(button);
  }
  if (!matches.length) { const empty = document.createElement("p"); empty.textContent = "Nie znaleziono osoby. Spróbuj innego nazwiska."; results.append(empty); }
}
search.addEventListener("input", searchPeople);
search.addEventListener("keydown", event => {
  if (event.key === "ArrowDown") { event.preventDefault(); results.querySelector("button")?.focus(); }
  if (event.key === "Escape") results.hidden = true;
});
results.addEventListener("keydown", event => {
  if (event.key === "Escape") { results.hidden = true; search.focus(); }
});

document.querySelector("#save-config").addEventListener("click", () => download(new Blob([JSON.stringify(config, null, 2)], { type: "application/json" }), "plakat-ustawienia.json"));
document.querySelector("#open-config").addEventListener("click", () => document.querySelector("#load-config").click());
document.querySelector("#load-config").addEventListener("change", async event => {
  const file = event.target.files[0];
  if (!file) return;
  try {
    if (file.size > 128 * 1024) throw new Error("Plik ustawień jest za duży (maks. 128 KB).");
    const loaded = normalizeConfig(JSON.parse(await file.text()));
    if (!Object.hasOwn(people, loaded.root)) throw new Error("Osoby z ustawień nie ma w tym drzewie.");
    config = loaded; render(); notify("Ustawienia zostały wczytane.");
  } catch (error) { notify(`Nie można wczytać ustawień: ${error.message}`); }
  event.target.value = "";
});
document.querySelector("#reset-config").addEventListener("click", () => { config = normalizeConfig(); render(); });
document.querySelector("#reset-positions").addEventListener("click", () => { config.positions = {}; render(); });
document.querySelector("#download-pdf").addEventListener("click", event => downloadPoster("pdf", event.currentTarget));
document.querySelector("#download-svg").addEventListener("click", event => downloadPoster("svg", event.currentTarget));
for (const [id, change] of [["zoom-in", 0.25], ["zoom-out", -0.25], ["zoom-fit", 0]]) document.querySelector(`#${id}`).addEventListener("click", () => {
  zoom = change ? Math.max(1, Math.min(3, zoom + change)) : 1;
  fitPoster();
  document.querySelector("#zoom-fit").textContent = zoom === 1 ? "Dopasuj" : `${Math.round(zoom * 100)}%`;
});

sheet.addEventListener("pointerdown", event => {
  const label = event.target.closest("[data-number]");
  if (!label || event.button !== 0) return;
  const svg = sheet.querySelector("svg");
  selectCard(label.dataset.number, true);
  const point = new DOMPoint(event.clientX, event.clientY).matrixTransform(svg.getScreenCTM().inverse());
  drag = { number: label.dataset.number, point, original: config.positions[label.dataset.number] || { x: 0, y: 0 }, pointerId: event.pointerId };
  sheet.setPointerCapture(event.pointerId);
  event.preventDefault();
});
sheet.addEventListener("pointermove", event => {
  if (!drag || drag.pointerId !== event.pointerId) return;
  const svg = sheet.querySelector("svg");
  const point = new DOMPoint(event.clientX, event.clientY).matrixTransform(svg.getScreenCTM().inverse());
  config.positions[drag.number] = {
    x: drag.original.x + (point.x - drag.point.x) / currentPoster.layout.artWidth,
    y: drag.original.y + (point.y - drag.point.y) / currentPoster.layout.artHeight,
  };
  render(false);
  sheet.querySelector(`[data-number="${drag.number}"]`)?.classList.add("is-dragging");
});
function endDrag() {
  if (!drag) return;
  const number = drag.number;
  drag = undefined;
  render();
  selectCard(number);
  sheet.querySelector(`[data-number="${CSS.escape(number)}"]`)?.focus({ preventScroll: true });
}
sheet.addEventListener("pointerup", endDrag);
sheet.addEventListener("pointercancel", endDrag);
sheet.addEventListener("lostpointercapture", endDrag);
sheet.addEventListener("focusin", event => {
  const label = event.target.closest("[data-number]");
  if (label) selectCard(label.dataset.number, true);
});
sheet.addEventListener("keydown", event => {
  const label = event.target.closest("[data-number]");
  if (label && ["Enter", " "].includes(event.key)) { event.preventDefault(); selectCard(label.dataset.number); return; }
  const direction = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] }[event.key];
  if (!label || !direction) return;
  event.preventDefault();
  const number = label.dataset.number;
  const original = config.positions[number] || { x: 0, y: 0 };
  const step = event.shiftKey ? 10 : 2;
  config.positions[number] = {
    x: original.x + direction[0] * step / currentPoster.layout.artWidth,
    y: original.y + direction[1] * step / currentPoster.layout.artHeight,
  };
  render();
  sheet.querySelector(`[data-number="${CSS.escape(number)}"]`).focus({ preventScroll: true });
});
new ResizeObserver(fitPoster).observe(document.querySelector("#canvas-scroll"));

try {
  const response = await fetch(STATIC ? "people.json" : "/api/people");
  if (!response.ok) throw new Error("Nie można odczytać drzewa rodzinnego.");
  people = await response.json();
  try {
    const saved = localStorage.getItem(storageKey);
    if (saved) config = normalizeConfig(JSON.parse(saved));
  } catch { notify("Nie można odczytać poprzednich ustawień. Wczytano domyślne."); }
  // Link ze strony drzewa: ?root=<id osoby>[&rodzenstwo=1]. Zmiana osoby jak przy wyborze z listy:
  // ręczne przesunięcia i ustawienia kartuszy należą do poprzedniej osoby, więc są zerowane.
  const wanted = new URLSearchParams(location.search);
  const wantedRoot = wanted.get("root");
  if (wantedRoot && Object.hasOwn(people, wantedRoot)) {
    if (wantedRoot !== config.root) { config.root = wantedRoot; config.positions = {}; config.cardSettings = {}; selectedCard = "1"; }
    if (wanted.get("rodzenstwo") === "1") config.showSiblings = true;
  }
  if (wantedRoot) history.replaceState(null, "", location.pathname);
  // domyślnie osoba, dla której jest drzewo (ME w tree_data.py), a gdy jej nie ma — pierwsza z listy
  const pageRoot = document.querySelector('meta[name="poster-root"]')?.content;
  if (!Object.hasOwn(people, config.root)) config.root = Object.hasOwn(people, pageRoot || "") ? pageRoot : Object.keys(people)[0];
  render();
} catch (error) {
  sheet.replaceChildren();
  const message = document.createElement("p"); message.className = "loading"; message.textContent = error.message;
  sheet.append(message);
  for (const button of document.querySelectorAll("button")) button.disabled = true;
}
