const comparePeople = (graph, left, right) => graph.people.get(left).n.localeCompare(graph.people.get(right).n, "pl") || left.localeCompare(right);

function overviewLayout(graph, includeHypotheses) {
  const parents = new Map([...graph.people.keys()].map(id => [id, id]));
  const root = id => {
    if (parents.get(id) !== id) parents.set(id, root(parents.get(id)));
    return parents.get(id);
  };
  for (const family of graph.families) {
    if (family.hp && !includeHypotheses) continue;
    if (family.parents.length === 2) parents.set(root(family.parents[1]), root(family.parents[0]));
  }
  const children = new Map([...graph.people.keys()].map(id => [root(id), new Set()]));
  for (const edge of graph.edges) {
    if (edge.type !== "parent-child" || (edge.hypothetical && !includeHypotheses)) continue;
    const parent = root(edge.from), child = root(edge.to);
    if (parent !== child) children.get(parent).add(child);
  }
  const levels = new Map(), visiting = new Set();
  function level(id) {
    if (levels.has(id)) return levels.get(id);
    if (visiting.has(id)) return 0;
    visiting.add(id);
    const value = Math.max(0, ...[...children.get(id)].map(child => level(child) + 1));
    visiting.delete(id);
    levels.set(id, value);
    return value;
  }
  for (const id of children.keys()) level(id);
  const remaining = new Set(graph.people.keys());
  const components = [];
  while (remaining.size) {
    const ids = [remaining.values().next().value];
    remaining.delete(ids[0]);
    for (let cursor = 0; cursor < ids.length; cursor++) {
      for (const link of graph.adjacency.get(ids[cursor])) {
        if ((!includeHypotheses && link.edge.hypothetical) || !remaining.delete(link.to)) continue;
        ids.push(link.to);
      }
    }
    components.push(ids);
  }
  components.sort((left, right) => right.length - left.length || comparePeople(graph, left[0], right[0]));
  const positions = new Map();
  const branches = [...new Set([...graph.people.values()].map(person => person.br || ""))].sort();
  let mainWidth = 0, satelliteTop = 0, isolated = 0;
  components.forEach((ids, component) => {
    const layers = new Map();
    for (const id of ids) {
      const generation = levels.get(root(id));
      if (!layers.has(generation)) layers.set(generation, []);
      layers.get(generation).push(id);
    }
    const orderedLevels = [...layers.keys()].sort((left, right) => left - right);
    const centerLevel = (orderedLevels[0] + orderedLevels.at(-1)) / 2;
    const coordinates = new Map();
    for (const members of layers.values()) {
      members.sort((left, right) => (graph.people.get(left).br || "").localeCompare(graph.people.get(right).br || "") || comparePeople(graph, left, right));
      const columns = Math.ceil(Math.sqrt(members.length * 3.4));
      members.forEach((id, index) => coordinates.set(id, (index % columns - (columns - 1) / 2) * 36));
    }
    for (let sweep = 0; sweep < 6; sweep++) {
      const direction = sweep % 2 ? [...orderedLevels].reverse() : orderedLevels;
      for (const generation of direction) {
        const members = layers.get(generation);
        const barycenter = id => {
          const links = graph.adjacency.get(id).filter(link => (includeHypotheses || !link.edge.hypothetical) && coordinates.has(link.to));
          return links.length ? links.reduce((sum, link) => sum + coordinates.get(link.to), 0) / links.length : coordinates.get(id);
        };
        const scores = new Map(members.map(id => [id, barycenter(id)]));
        members.sort((left, right) => scores.get(left) - scores.get(right) || comparePeople(graph, left, right));
        const columns = Math.ceil(Math.sqrt(members.length * 3.4));
        members.forEach((id, index) => coordinates.set(id, (index % columns - (columns - 1) / 2) * 36));
      }
    }
    let halfWidth = 0;
    for (const [generation, members] of layers) {
      const columns = Math.ceil(Math.sqrt(members.length * 3.4));
      const rows = Math.ceil(members.length / columns);
      members.forEach((id, index) => {
        const x = coordinates.get(id);
        halfWidth = Math.max(halfWidth, Math.abs(x));
        const branch = branches.indexOf(graph.people.get(id).br || "");
        positions.set(id, { x, y: (generation - centerLevel) * 56,
          z: (Math.floor(index / columns) - (rows - 1) / 2) * 64 + branch * 5,
          generation, component, branch });
      });
    }
    if (!component) { mainWidth = halfWidth; satelliteTop = (orderedLevels.at(-1) - orderedLevels[0]) * 28; }
    else {
      const halfHeight = (orderedLevels.at(-1) - orderedLevels[0]) * 28;
      const offsetY = ids.length === 1 ? satelliteTop - Math.floor(isolated / 4) * 44 : satelliteTop - halfHeight;
      const offsetX = mainWidth + halfWidth + 115 + (ids.length === 1 ? isolated % 4 * 44 : 0);
      for (const id of ids) {
        positions.get(id).x += offsetX;
        positions.get(id).y += offsetY;
        positions.get(id).z -= 95;
      }
      if (ids.length === 1) isolated++;
      else satelliteTop -= halfHeight * 2 + 70;
    }
  });
  return positions;
}

export function layoutGraph(graph, origin = null, route = null, includeHypotheses = false) {
  const positions = overviewLayout(graph, includeHypotheses);
  if (!route) return positions;
  const queue = [], anchored = new Set();
  let generation = 0;
  route.people.forEach((id, index) => {
    if (index) generation += route.steps[index - 1].type === "parent" ? 1 : route.steps[index - 1].type === "child" ? -1 : 0;
    positions.set(id, { ...positions.get(id), x: (index - (route.people.length - 1) / 2) * 76,
      y: generation * 48, z: Math.sin(index / Math.max(1, route.people.length - 1) * Math.PI) * 30 + 30, generation, route: true });
    anchored.add(id);
    queue.push(id);
  });
  const slots = new Map();
  for (let cursor = 0; cursor < queue.length; cursor++) {
    const id = queue[cursor], anchor = positions.get(id);
    for (const link of graph.adjacency.get(id)) {
      if (anchored.has(link.to) || (!includeHypotheses && link.edge.hypothetical)) continue;
      const level = anchor.generation + (link.type === "parent" ? 1 : link.type === "child" ? -1 : 0);
      const slotKey = `${Math.round(anchor.x / 76)}:${level}`;
      const slot = slots.get(slotKey) || 0;
      slots.set(slotKey, slot + 1);
      positions.set(link.to, { ...positions.get(link.to), x: anchor.x + (slot % 2 ? -1 : 1) * (20 + Math.floor(slot / 2) * 28),
        y: level * 48, z: Math.min(anchor.z - 75, -45) - Math.floor(slot / 4) * 42, generation: level });
      anchored.add(link.to);
      queue.push(link.to);
    }
  }
  return positions;
}

export function visibleGraph(graph, positions, visible, includeHypotheses, route) {
  const routeEdges = new Set((route?.steps || []).map(step => step.edge.id));
  const nodes = [...visible].filter(id => positions.has(id)).map(id => ({ id, person: graph.people.get(id), ...positions.get(id) }));
  const edges = graph.edges.filter(edge => visible.has(edge.from) && visible.has(edge.to)
    && (includeHypotheses || !edge.hypothetical || routeEdges.has(edge.id)));
  return { nodes, edges, routeEdges };
}
