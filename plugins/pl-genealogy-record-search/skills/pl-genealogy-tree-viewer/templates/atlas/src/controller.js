import { createGraph, searchPeople, findConnection, neighborhood, componentCount, normalize, stepLabel, lifeYears as years } from "./graph.js";
import { layoutGraph, visibleGraph } from "./layout.js";
import { createScene } from "./scene.js";
import { atlasMarkup, icon, initials } from "./ui.js";

const escape = value => String(value || "").replace(/[&<>"']/g, character => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[character]);
const evidence = { akt: "akt", praw: "poszlaka", hip: "hipoteza" };

export function createAtlas(host, { database, portraits = {}, onSelect, onExit, onChange, navigate = action => action() }) {
  const graph = createGraph(database);
  const components = [componentCount(graph), componentCount(graph, true)];
  let scene = null, active = false, initialized = false, route = null, focused = null;
  let scope = "all", includeHypotheses = false, flat = false, touchPan = false, presentation = false;
  let positions = null, visible = new Set(), sceneData = null, cameraTimer;
  const endpoints = [null, null];
  let committedPair = [null, null];
  const events = new AbortController();
  const signal = events.signal;

  host.className = "atlas";
  host.innerHTML = atlasMarkup(graph.gaps);
  const query = selector => host.querySelector(selector);
  const story = query(".atlas-story"), selectedPanel = query(".atlas-selected");
  const status = query(".atlas-status"), viewport = query(".atlas-viewport");
  const failure = query(".atlas-failure");
  const inputs = [query("#atlas-from"), query("#atlas-to")];
  const optionLists = [query("#atlas-options-0"), query("#atlas-options-1")];
  const options = [[], []], optionIndex = [-1, -1];
  const commit = action => navigate(() => { action(); onChange(); });

  function insets() {
    if (presentation) return { left: 70, right: 70, top: 90, bottom: 70 };
    const compact = host.clientWidth < 760;
    const mobileBottom = query(".atlas-dock").getBoundingClientRect().height + 35
      + (route ? query(".atlas-inspector").getBoundingClientRect().height + 12 : 0);
    return compact ? { left: 35, right: 35, top: 145, bottom: Math.max(205, mobileBottom) }
      : { left: route || !focused ? 315 : 75, right: focused ? 325 : 90, top: 125, bottom: 205 };
  }

  function obstructions() {
    const bounds = viewport.getBoundingClientRect();
    return [...host.querySelectorAll("[data-obstruct]")].filter(element => element.getClientRects().length)
      .map(element => {
        const rect = element.getBoundingClientRect();
        return { left: rect.left - bounds.left - 8, right: rect.right - bounds.left + 8,
          top: rect.top - bounds.top - 8, bottom: rect.bottom - bounds.top + 8 };
      });
  }

  function cameraChanged() {
    clearTimeout(cameraTimer);
    cameraTimer = setTimeout(onChange, 120);
  }

  function failed(message) {
    failure.hidden = false;
    failure.querySelector("p").textContent = message;
    host.classList.add("has-failure");
  }

  function initializeScene() {
    try {
      scene?.dispose();
      scene = null;
      scene = createScene(viewport, { portraits, onSelect: selectPerson, onCamera: cameraChanged, onFailure: failed, insets, obstructions });
      failure.hidden = true;
      host.classList.remove("has-failure");
      scene.setActive(active);
      if (flat) scene.setFlat(true);
      scene.setTouchPan(touchPan);
      return true;
    } catch {
      viewport.querySelectorAll("canvas,.atlas-labels").forEach(element => element.remove());
      failed("WebGL 2 jest niedostępny. Możesz nadal wyszukać dwie osoby, przeczytać całą trasę i otworzyć ich karty.");
      return false;
    }
  }

  function announce(message, error = false) {
    status.textContent = message;
    status.classList.toggle("is-error", error);
  }

  function setEndpoint(index, id) {
    endpoints[index] = graph.people.has(id) ? id : null;
    inputs[index].value = endpoints[index] ? graph.people.get(id).n : "";
    closeOptions(index);
  }

  function closeOptions(index) {
    optionLists[index].hidden = true;
    inputs[index].setAttribute("aria-expanded", "false");
    inputs[index].removeAttribute("aria-activedescendant");
    optionIndex[index] = -1;
  }

  function showOptions(index) {
    const matches = searchPeople(graph, inputs[index].value);
    options[index] = matches;
    optionIndex[index] = -1;
    const list = optionLists[index];
    list.replaceChildren();
    for (const [matchIndex, match] of matches.entries()) {
      const button = document.createElement("button");
      button.type = "button";
      button.id = `atlas-result-${index}-${matchIndex}`;
      button.setAttribute("role", "option");
      button.setAttribute("aria-selected", "false");
      button.tabIndex = -1;
      const person = match.person;
      button.innerHTML = `<span class="atlas-result-avatar">${portraits[person.id] ? `<img src="${escape(portraits[person.id])}" alt="">` : escape(initials(person.n))}</span><span><strong>${escape(person.n)}</strong><small>${escape(years(person))} · ${escape(person.br || person.id)}</small>`
        + (match.contextual ? `<small class="atlas-context-match">Kontekst małżeństwa: ${escape(match.spouseNames.join(", "))}. Imię w bazie pozostaje bez zmian.</small>` : "") + "</span>";
      button.addEventListener("pointerdown", event => { if (event.button === 0) event.preventDefault(); });
      button.addEventListener("click", () => { setEndpoint(index, person.id); inputs[index === 0 && !endpoints[1] ? 1 : index].focus(); });
      list.append(button);
    }
    if (!matches.length) {
      const empty = document.createElement("p");
      empty.textContent = inputs[index].value.trim() ? "Brak osób o takim imieniu lub nazwisku." : "Wpisz imię i nazwisko.";
      list.append(empty);
    }
    list.hidden = false;
    inputs[index].setAttribute("aria-expanded", "true");
  }

  inputs.forEach((input, index) => {
    input.addEventListener("input", () => { endpoints[index] = null; showOptions(index); }, { signal });
    input.addEventListener("focus", () => { if (!endpoints[index] && input.value) showOptions(index); }, { signal });
    input.addEventListener("keydown", event => {
      if (event.key === "Escape") { event.stopPropagation(); closeOptions(index); return; }
      if (event.key === "ArrowDown" || event.key === "ArrowUp") {
        event.preventDefault();
        if (optionLists[index].hidden) showOptions(index);
        const direction = event.key === "ArrowDown" ? 1 : -1;
        const length = options[index].length;
        if (!length) return;
        optionIndex[index] = (optionIndex[index] + direction + length) % length;
        [...optionLists[index].children].forEach((button, buttonIndex) => button.setAttribute("aria-selected", String(buttonIndex === optionIndex[index])));
        const option = optionLists[index].children[optionIndex[index]];
        input.setAttribute("aria-activedescendant", option.id);
        option.scrollIntoView({ block: "nearest" });
      }
      if (event.key === "Enter" && !optionLists[index].hidden && optionIndex[index] >= 0) {
        event.preventDefault();
        setEndpoint(index, options[index][optionIndex[index]].person.id);
      }
    }, { signal });
  });
  host.addEventListener("focusout", () => queueMicrotask(() => {
    for (const index of [0, 1]) if (!inputs[index].closest(".atlas-field").contains(document.activeElement)) closeOptions(index);
  }), { signal });
  document.addEventListener("pointerdown", event => {
    for (const index of [0, 1]) if (!inputs[index].closest(".atlas-field").contains(event.target)) closeOptions(index);
  }, { signal });

  function chooseEndpoint(index) {
    if (endpoints[index]) return true;
    const matches = searchPeople(graph, inputs[index].value);
    const exact = matches.filter(match => normalize(match.person.n) === normalize(inputs[index].value));
    const candidates = exact.length ? exact : matches;
    if (candidates.length === 1) { setEndpoint(index, candidates[0].person.id); return true; }
    announce(candidates.length ? "Wybierz konkretną osobę z listy wyników." : "Wyszukaj i wybierz obie osoby.", true);
    inputs[index].focus(); showOptions(index); return false;
  }

  function connect() {
    if (!chooseEndpoint(0) || !chooseEndpoint(1)) return;
    commit(applyConnection);
  }

  function applyConnection(pair = endpoints) {
    committedPair = [...pair];
    route = findConnection(graph, pair[0], pair[1], includeHypotheses);
    focused = null;
    scope = "family";
    positions = layoutGraph(graph, null, route, includeHypotheses);
    if (route) {
      announce(route.steps.length ? `${route.people.length} osób · ${route.steps.length} relacji · cała trasa widoczna` : "To ta sama osoba. Wybierz inną osobę, aby zobaczyć połączenie.");
    } else {
      const hypotheticalRoute = !includeHypotheses && findConnection(graph, pair[0], pair[1], true);
      announce(hypotheticalRoute ? "Połączenie wymaga hipotetycznej relacji. Możesz włączyć ją w Przewodniku."
        : "W tej bazie nie ma połączenia między wybranymi osobami. Pokazujemy obie rodziny.", true);
    }
    update(true);
  }
  query("form").addEventListener("submit", event => { event.preventDefault(); connect(); }, { signal });

  function renderStory() {
    query(".atlas-inspector").hidden = !route;
    query(".atlas-overview").hidden = Boolean(route || focused);
    if (!route) {
      story.replaceChildren();
      return;
    }
    const pivotIndex = route.steps.findIndex((step, index) => step.type === "child" && route.steps[index - 1]?.type === "parent");
    story.innerHTML = `<div class="atlas-panel-head"><span class="atlas-story-kicker">Odnalezione połączenie</span><button type="button" data-action="overview" aria-label="Wyczyść połączenie i pokaż całe drzewo">${icon("close")}</button></div><div class="atlas-route-heading"><h3>${route.steps.length} ${route.steps.length === 1 ? "relacja" : route.steps.length < 5 ? "relacje" : "relacji"}<span>przez ${route.people.length} osób</span></h3></div><ol class="atlas-route">`
      + route.people.map((id, index) => {
        const person = graph.people.get(id);
        const step = route.steps[index - 1];
        const relation = step ? stepLabel(step, graph) : "początek trasy";
        return `<li${index === pivotIndex ? ' class="atlas-turn"' : ""}>${step ? `<span class="atlas-step-label">${escape(relation)}${step.edge.hypothetical ? " · hipoteza" : ""}</span>` : ""}<button type="button" data-person="${escape(id)}"><span class="atlas-step-index">${index + 1}</span>${portraits[id] ? `<img src="${escape(portraits[id])}" alt="">` : ""}<span><strong>${escape(person.n)}</strong><small>${escape(years(person))}</small>${index === pivotIndex ? '<em>Punkt łączący gałęzie</em>' : ""}</span></button></li>`;
      }).join("") + `</ol><p class="atlas-route-note">Najkrótsza droga w zapisanych relacjach. Nie jest potwierdzeniem dokumentowym ani automatyczną nazwą pokrewieństwa.</p>`;
    const routeFamilies = new Set(route.steps.map(step => step.edge.familyId));
    const unmarried = graph.families.filter(family => family.um && routeFamilies.has(family.id));
    for (const family of unmarried) {
      const note = document.createElement("p");
      note.className = "atlas-family-note";
      note.textContent = `${family.parents.map(id => graph.people.get(id).n).join(" i ")}: rodzice wspólnego dziecka, nie zapis małżeństwa.`;
      story.append(note);
    }
    const clear = document.createElement("button");
    clear.type = "button";
    clear.className = "atlas-clear";
    clear.textContent = "Wróć do całego drzewa";
    clear.addEventListener("click", () => commit(resetOverview));
    story.append(clear);
    story.querySelectorAll("[data-person]").forEach(button => button.addEventListener("click", () => selectPerson(button.dataset.person)));
  }

  function renderSelected() {
    const person = graph.people.get(focused);
    selectedPanel.hidden = !person;
    if (!person) { selectedPanel.replaceChildren(); return; }
    const neighbors = graph.adjacency.get(focused).filter(link => includeHypotheses || !link.edge.hypothetical);
    const unique = [...new Map(neighbors.map(link => [link.to, link])).values()];
    selectedPanel.innerHTML = `<div class="atlas-panel-head"><span class="atlas-story-kicker">Wybrana osoba</span><button type="button" data-action="deselect" aria-label="Zamknij wybór osoby">${icon("close")}</button></div><div class="atlas-person-head"><span class="atlas-person-avatar">${portraits[focused] ? `<img src="${escape(portraits[focused])}" alt="">` : escape(initials(person.n))}</span><h3>${escape(person.n)}</h3><small>${escape(years(person))}</small>${evidence[person.t] ? `<span class="atlas-evidence ${escape(person.t)}">${evidence[person.t]}</span>` : ""}<p>${escape(person.br || "")}</p></div><div class="atlas-person-actions"><button type="button" data-from>Od tej osoby</button><button type="button" data-to>Do tej osoby</button></div><button type="button" class="atlas-person-detail" data-details>Otwórz kartę i źródła ${icon("external")}</button><details class="atlas-neighbors"><summary>Bezpośrednie relacje (${unique.length})</summary><ul>`
      + unique.map(link => `<li><button type="button" data-neighbor="${escape(link.to)}"><span>${escape(stepLabel(link, graph))}${link.edge.hypothetical ? " · hipoteza" : ""}</span>${escape(graph.people.get(link.to).n)}</button></li>`).join("") + "</ul></details>";
    selectedPanel.querySelector("[data-details]").addEventListener("click", () => onSelect(focused));
    selectedPanel.querySelector("[data-from]").addEventListener("click", () => { setEndpoint(0, focused); if (endpoints[1]) connect(); else inputs[1].focus(); });
    selectedPanel.querySelector("[data-to]").addEventListener("click", () => { setEndpoint(1, focused); if (endpoints[0]) connect(); else inputs[0].focus(); });
    selectedPanel.querySelectorAll("[data-neighbor]").forEach(button => button.addEventListener("click", () => selectPerson(button.dataset.neighbor)));
    for (const button of story.querySelectorAll("[data-person]")) {
      button.classList.toggle("is-selected", button.dataset.person === focused);
      if (button.dataset.person === focused) button.setAttribute("aria-current", "true");
      else button.removeAttribute("aria-current");
    }
  }

  function update(autoFit = false) {
    if (!positions) positions = layoutGraph(graph, null, route, includeHypotheses);
    const seeds = route?.people || [focused, ...committedPair].filter(Boolean);
    visible = scope === "all" ? new Set(graph.people.keys())
      : neighborhood(graph, seeds, scope === "route" ? 0 : route ? 1 : 2, includeHypotheses);
    if (focused && !visible.has(focused)) visible.add(focused);
    sceneData = { ...visibleGraph(graph, positions, visible, includeHypotheses, route), fitAll: scope === "all" };
    const groups = components[Number(includeHypotheses)];
    query(".atlas-scene-count").textContent = `${visible.size} z ${graph.people.size} osób · ${new Set(sceneData.nodes.map(node => node.generation)).size} warstw pokoleń`
      + (scope === "all" && groups > 1 ? ` · ${groups} rozłącznych grup` : "");
    renderStory(); renderSelected();
    syncControls();
    scene?.setData(sceneData, route, autoFit);
    scene?.select(focused);
  }

  function selectPerson(id) {
    if (!graph.people.has(id)) return;
    commit(() => {
      focused = id;
      if (!visible.has(id)) update(false);
      else { scene?.select(id); renderStory(); renderSelected(); syncControls(); }
      scene?.focus(id);
    });
  }

  function resetOverview() {
    route = null; focused = null; scope = "all";
    committedPair = [null, null];
    [0, 1].forEach(index => setEndpoint(index, null));
    positions = layoutGraph(graph, null, null, includeHypotheses);
    update(true);
    announce("Całe drzewo. Żadna osoba ani gałąź nie jest wybrana.");
  }

  function setPresentation(value) {
    presentation = value;
    host.classList.toggle("is-presenting", value);
    document.body.classList.toggle("atlas-presenting", value);
    for (const element of host.children) {
      if (!element.matches(".atlas-viewport,.atlas-vignette,.atlas-end-presentation")) element.inert = value;
    }
    query(".atlas-end-presentation").hidden = !value;
    query('.atlas-head [data-action="present"]').setAttribute("aria-pressed", String(value));
    if (value) query(".atlas-end-presentation").focus();
    else query('.atlas-head [data-action="present"]').focus();
    scene?.fit();
  }

  query(".atlas-scope").addEventListener("change", event => commit(() => { scope = event.target.value; update(true); }), { signal });
  query(".atlas-hypotheses").addEventListener("change", event => {
    const enabled = event.target.checked;
    commit(() => {
      includeHypotheses = enabled;
      positions = null;
      if (committedPair.every(Boolean)) applyConnection(committedPair);
      else update(false);
    });
  }, { signal });
  host.addEventListener("click", event => {
    const action = event.target.closest("[data-action]")?.dataset.action;
    if (!action) return;
    if (action === "swap") { const previous = endpoints[0]; setEndpoint(0, endpoints[1]); setEndpoint(1, previous); if (endpoints.every(Boolean)) connect(); }
    if (action === "exit") onExit();
    if (action === "overview") commit(resetOverview);
    if (action === "deselect") commit(() => { focused = null; scene?.select(null); renderStory(); renderSelected(); syncControls(); scene?.redraw(); });
    if (action === "present") setPresentation(!presentation);
    if (action === "help") {
      const guide = query(".atlas-key");
      guide.hidden = !guide.hidden;
      query('.atlas-head [data-action="help"]').setAttribute("aria-expanded", String(!guide.hidden));
      (guide.hidden ? query('.atlas-head [data-action="help"]') : guide.querySelector("button")).focus();
      scene?.redraw();
    }
    if (action === "retry" && initializeScene()) update(true);
    if (action === "fit") scene?.fit();
    if (action === "reset") { flat = false; syncControls(); scene?.setFlat(false); }
    if (action === "flat") commit(() => { flat = !flat; scene?.setFlat(flat); syncControls(); });
    if (action === "touch") { touchPan = !touchPan; scene?.setTouchPan(touchPan); syncControls(); }
    if (action === "in") scene?.zoom(1.25);
    if (action === "out") scene?.zoom(1 / 1.25);
  }, { signal });
  host.addEventListener("keydown", event => {
    if (/^(INPUT|SELECT|TEXTAREA)$/.test(event.target.tagName) || event.metaKey || event.ctrlKey || event.altKey) return;
    if (event.key === "Escape") {
      if (presentation) setPresentation(false);
      else if (!query(".atlas-key").hidden) query('[data-action="help"]').click();
      else { scene?.fit(); viewport.querySelector("canvas")?.focus(); }
      event.preventDefault();
    }
    if (event.key.toLowerCase() === "p") { setPresentation(!presentation); event.preventDefault(); }
    if (event.key.toLowerCase() === "f") { scene?.fit(); event.preventDefault(); }
  }, { signal });
  viewport.addEventListener("keydown", event => {
    if (/^(INPUT|SELECT|TEXTAREA|BUTTON)$/.test(event.target.tagName)) return;
    if (event.key === "+" || event.key === "=") { scene?.zoom(1.25); event.preventDefault(); }
    if (event.key === "-") { scene?.zoom(1 / 1.25); event.preventDefault(); }
    if (route && ["ArrowLeft", "ArrowRight"].includes(event.key)) {
      const index = Math.max(0, route.people.indexOf(focused));
      const next = Math.max(0, Math.min(route.people.length - 1, index + (event.key === "ArrowLeft" ? -1 : 1)));
      selectPerson(route.people[next]); event.preventDefault();
    }
  }, { signal });

  function syncControls() {
    query('.atlas-scope option[value="family"]').disabled = !focused && !committedPair.some(Boolean);
    query('.atlas-scope option[value="route"]').disabled = !route;
    query(".atlas-scope").value = scope;
    query(".atlas-hypotheses").checked = includeHypotheses;
    query('[data-action="flat"]').setAttribute("aria-pressed", String(flat));
    query('[data-action="touch"]').title = touchPan ? "Przesuń: przeciągnij jednym palcem" : "Obrót: przeciągnij jednym palcem";
    query('[data-action="touch"]').setAttribute("aria-pressed", String(touchPan));
    query('[data-action="touch"]').setAttribute("aria-label", touchPan ? "Przełącz na obrót" : "Przełącz na przesuwanie");
    query('[data-action="overview"]').hidden = !route && !focused && !committedPair.some(Boolean);
    host.classList.toggle("has-route", Boolean(route));
    host.classList.toggle("has-selection", Boolean(focused));
  }

  return {
    show() {
      active = true; host.hidden = false;
      if (!initialized) {
        initialized = true;
        initializeScene();
        announce("Całe drzewo. Wybierz dowolne dwie osoby, aby odkryć połączenie.");
        update(true);
      } else scene?.setActive(true);
      syncControls();
    },
    hide() { if (presentation) setPresentation(false); active = false; scene?.setActive(false); host.hidden = true; inputs.forEach((input, index) => closeOptions(index)); },
    focus(id, frame = false) {
      if (!graph.people.has(id)) return;
      focused = id;
      if (!visible.has(id)) { update(false); frame = true; }
      else { scene?.select(id); renderStory(); renderSelected(); syncControls(); scene?.redraw(); }
      if (frame) scene?.focus(id);
    },
    openConnection() { const input = inputs[endpoints[0] ? 1 : 0]; input.focus(); input.select(); },
    refresh() { if (initialized) update(false); },
    fit() { scene?.fit(); },
    state() { return { v: 2, pair: [...committedPair], scope, includeHypotheses, flat, focused, camera: scene?.state() || null }; },
    key() { return JSON.stringify([committedPair, scope, includeHypotheses, flat, focused]); },
    restore(state) {
      if (!initialized) this.show();
      if (!state || state.v !== 2) { includeHypotheses = false; flat = false; scene?.setFlat(false); resetOverview(); return; }
      focused = graph.people.has(state.focused) ? state.focused : null;
      scope = ["route", "family", "all"].includes(state.scope) ? state.scope : "all";
      includeHypotheses = Boolean(state.includeHypotheses);
      flat = Boolean(state.flat);
      [0, 1].forEach(index => setEndpoint(index, state.pair?.[index]));
      committedPair = [...endpoints];
      route = endpoints.every(Boolean) ? findConnection(graph, ...endpoints, includeHypotheses) : null;
      if ((scope === "route" && !route) || (scope === "family" && !focused && !endpoints.some(Boolean))) scope = "all";
      positions = layoutGraph(graph, null, route, includeHypotheses);
      scene?.setFlat(flat); syncControls(); update(true); scene?.restore(state.camera);
      announce(route ? `${route.people.length} osób · ${route.steps.length} relacji · przywrócone połączenie` : "Wyszukuj w całym drzewie, niezależnie od wybranej gałęzi.");
    },
    diagnostics() { return { ...scene?.diagnostics(), people: graph.people.size, edges: graph.edges.length,
      route: route?.people || [], routeEdges: route?.steps.map(step => step.edge.id) || [], scope, focused, pair: [...committedPair], presentation }; },
    dispose() { if (presentation) setPresentation(false); clearTimeout(cameraTimer); events.abort(); scene?.dispose(); host.replaceChildren(); }
  };
}
