export const normalize = value => String(value || "").normalize("NFD")
  .replace(/[\u0300-\u036f]/g, "").replace(/ł/g, "l").replace(/Ł/g, "L")
  .toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();

export const lifeYears = person => person.dy ? `${person.by || "?"}–${person.dy}` : person.by || "daty nieznane";

export function createGraph(database) {
  const people = new Map(Object.values(database.people).filter(person => person.t !== "luka")
    .sort((left, right) => left.id.localeCompare(right.id)).map(person => [person.id, person]));
  const adjacency = new Map([...people.keys()].map(id => [id, []]));
  const edges = [];
  const families = [];
  const connect = (family, from, to, type) => {
    if (!people.has(from) || !people.has(to) || from === to) return;
    const edge = { id: `${family.id}:${type}:${from}:${to}`, from, to, type,
      familyId: family.id, hypothetical: Boolean(family.hp) };
    edges.push(edge);
    adjacency.get(from).push({ to, type: type === "parent-child" ? "child" : "spouse", edge });
    adjacency.get(to).push({ to: from, type: type === "parent-child" ? "parent" : "spouse", edge });
  };
  for (const [familyId, source] of Object.entries(database.fams).sort(([left], [right]) => left.localeCompare(right))) {
    const family = { ...source, id: source.id || familyId };
    family.parents = [...new Set([family.h, family.w].filter(id => people.has(id)))];
    family.children = [...new Set((family.c || []).filter(id => people.has(id)))];
    families.push(family);
    if (!family.um) connect(family, family.h, family.w, "spouse");
    for (const parent of family.parents) {
      for (const child of family.children) connect(family, parent, child, "parent-child");
    }
  }
  for (const neighbors of adjacency.values()) {
    neighbors.sort((left, right) => left.to.localeCompare(right.to) || left.edge.id.localeCompare(right.edge.id));
  }
  const searchIndex = [...people.values()].map(person => {
    const spouseNames = adjacency.get(person.id).filter(link => link.type === "spouse")
      .map(link => people.get(link.to).sn || "").filter(Boolean);
    const ownName = normalize(`${person.n} ${person.mn || ""} ${person.by || ""} ${person.dy || ""}`);
    return { person, ownName, contextName: normalize(`${ownName} ${spouseNames.join(" ")}`), spouseNames };
  });
  return { people, edges, families, adjacency, searchIndex,
    gaps: Object.values(database.people).filter(person => person.t === "luka").length };
}

export function searchPeople(graph, query, limit = 12) {
  const tokens = normalize(query).split(" ").filter(Boolean);
  if (!tokens.length) return [];
  return graph.searchIndex.flatMap(entry => {
    if (!tokens.every(token => entry.contextName.includes(token))) return [];
    const contextual = !tokens.every(token => entry.ownName.includes(token));
    const exact = entry.ownName.startsWith(normalize(query));
    return [{ ...entry, contextual, rank: (contextual ? 2 : 0) + (exact ? 0 : 1) }];
  }).sort((left, right) => left.rank - right.rank || left.person.n.localeCompare(right.person.n, "pl")
    || left.person.id.localeCompare(right.person.id)).slice(0, limit);
}

export function findConnection(graph, start, end, includeHypotheses = false) {
  if (!graph.people.has(start) || !graph.people.has(end)) return null;
  if (start === end) return { people: [start], steps: [], hypothetical: false };
  const distance = new Map([[start, 0]]);
  const queue = [start];
  for (let cursor = 0; cursor < queue.length; cursor++) {
    const id = queue[cursor];
    if (distance.has(end) && distance.get(id) >= distance.get(end)) break;
    for (const link of graph.adjacency.get(id)) {
      if (!includeHypotheses && link.edge.hypothetical) continue;
      if (!distance.has(link.to)) {
        distance.set(link.to, distance.get(id) + 1);
        queue.push(link.to);
      }
    }
  }
  if (!distance.has(end)) return null;
  const best = new Map([[start, new Map([["start", { cost: 0, people: [start], steps: [] }]])]]);
  for (const id of queue) {
    if (!best.has(id)) continue;
    for (const [previous, candidate] of best.get(id)) {
      for (const link of graph.adjacency.get(id)) {
        if ((!includeHypotheses && link.edge.hypothetical) || distance.get(link.to) !== distance.get(id) + 1) continue;
        const cost = candidate.cost + (previous === "child" && link.type === "parent" ? 100 : 0)
          + (link.edge.hypothetical ? 10 : 0) + (link.type === "spouse" ? 1 : 0);
        if (!best.has(link.to)) best.set(link.to, new Map());
        if (!best.get(link.to).has(link.type) || best.get(link.to).get(link.type).cost > cost) {
          best.get(link.to).set(link.type, { cost, people: [...candidate.people, link.to],
            steps: [...candidate.steps, { from: id, to: link.to, type: link.type, edge: link.edge }] });
        }
      }
    }
  }
  const result = [...best.get(end).values()].sort((left, right) => left.cost - right.cost)[0];
  return { people: result.people, steps: result.steps,
    hypothetical: result.steps.some(step => step.edge.hypothetical) };
}

export function neighborhood(graph, seeds, depth = 1, includeHypotheses = false) {
  const visible = new Set(seeds.filter(id => graph.people.has(id)));
  let frontier = [...visible];
  for (let level = 0; level < depth; level++) {
    const next = [];
    for (const id of frontier) {
      for (const link of graph.adjacency.get(id)) {
        if ((!includeHypotheses && link.edge.hypothetical) || visible.has(link.to)) continue;
        visible.add(link.to);
        next.push(link.to);
      }
    }
    frontier = next;
  }
  return visible;
}

export function componentCount(graph, includeHypotheses = false) {
  const remaining = new Set(graph.people.keys());
  let count = 0;
  while (remaining.size) {
    const first = remaining.values().next().value;
    const queue = [first];
    remaining.delete(first);
    count++;
    for (let cursor = 0; cursor < queue.length; cursor++) {
      for (const link of graph.adjacency.get(queue[cursor])) {
        if ((!includeHypotheses && link.edge.hypothetical) || !remaining.delete(link.to)) continue;
        queue.push(link.to);
      }
    }
  }
  return count;
}

export function stepLabel(step, graph) {
  if (step.type === "spouse") return "małżeństwo";
  const sex = graph.people.get(step.to)?.s;
  if (step.type === "parent") return sex === "M" ? "ojciec" : sex === "F" ? "matka" : "rodzic";
  return sex === "M" ? "syn" : sex === "F" ? "córka" : "dziecko";
}
