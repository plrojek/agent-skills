import { Vector3 } from "three";
import { lifeYears } from "./graph.js";
import { palette } from "./ui.js";

const tiers = { akt: "akt", praw: "poszlaka", hip: "hipoteza" };

export function createLabels(host, portraits, onSelect, onFrame, obstructions = () => []) {
  const layer = document.createElement("div");
  layer.className = "atlas-labels";
  host.append(layer);
  let entries = [];
  let selected = null;
  let hovered = null;
  let labelLayout = null;
  const point = new Vector3();

  function setNodes(nodes, route) {
    layer.replaceChildren();
    labelLayout = null;
    const order = new Map((route?.people || []).map((id, index) => [id, index + 1]));
    entries = nodes.map(node => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = `atlas-label${order.has(node.id) ? " is-route" : ""}`;
      button.dataset.person = node.id;
      button.setAttribute("aria-label", `Wybierz osobę: ${node.person.n}`);
      button.style.setProperty("--node-color", palette[node.branch % palette.length]);
      if (portraits[node.id]) {
        const portrait = document.createElement("img");
        portrait.src = portraits[node.id];
        portrait.alt = "";
        portrait.draggable = false;
        button.append(portrait);
      }
      const text = document.createElement("span");
      const name = document.createElement("strong");
      name.textContent = node.person.n;
      const detail = document.createElement("small");
      detail.textContent = lifeYears(node.person);
      text.append(name, detail);
      if (tiers[node.person.t]) {
        const evidence = document.createElement("span");
        evidence.className = `atlas-evidence ${node.person.t}`;
        evidence.textContent = tiers[node.person.t];
        text.append(evidence);
      }
      button.append(text);
      if (order.has(node.id)) {
        const index = document.createElement("span");
        index.className = "atlas-node-index";
        index.textContent = order.get(node.id);
        button.append(index);
      }
      button.addEventListener("click", () => onSelect(node.id));
      button.addEventListener("dblclick", () => onFrame(node.id));
      button.hidden = true;
      layer.append(button);
      const index = order.get(node.id);
      const turn = index && route?.steps[index - 1]?.type === "child" && route?.steps[index - 2]?.type === "parent";
      const priority = index === 1 || index === route?.people.length ? 3 : turn ? 2 : order.has(node.id) ? 1 : 0;
      return { node, button, route: order.has(node.id), priority };
    });
  }

  function update(camera, width, height) {
    const rectangles = [];
    const blocked = obstructions();
    let count = 0;
    const compact = width < 700;
    const layoutKey = `${compact}:${width < 600}`;
    if (labelLayout !== layoutKey) {
      for (const entry of entries) {
        entry.width = width < 600 && entry.route ? 132 : entry.route ? 166 : 150;
        entry.button.classList.toggle("is-compact", compact);
        entry.button.style.width = `${entry.width}px`;
        entry.button.hidden = false;
      }
      for (const entry of entries) entry.height = Math.ceil(entry.button.getBoundingClientRect().height);
      labelLayout = layoutKey;
    }
    const hasRoute = entries.some(entry => entry.route);
    const prioritized = [...entries].sort((left, right) => Number(right.node.id === selected) - Number(left.node.id === selected)
      || Number(right.node.id === hovered) - Number(left.node.id === hovered)
      || right.priority - left.priority
      || Number(Boolean(portraits[right.node.id])) - Number(Boolean(portraits[left.node.id])));
    for (const entry of prioritized) {
      const { node, button } = entry;
      const important = entry.route || node.id === selected || node.id === hovered;
      const distance = Math.hypot(node.x - camera.position.x, node.y - camera.position.y, node.z - camera.position.z);
      const scale = camera.isPerspectiveCamera ? height / (2 * Math.tan(camera.fov * Math.PI / 360) * distance)
        : height * camera.zoom / (camera.top - camera.bottom);
      if ((!important && scale < 0.5) || (compact && hasRoute && !important)) { button.hidden = true; continue; }
      point.set(node.x, node.y, node.z).project(camera);
      const x = (point.x + 1) * width / 2;
      let y = (1 - point.y) * height / 2 + 14;
      const labelWidth = entry.width;
      const labelHeight = entry.height;
      if (compact && entry.priority === 2) y = Math.max(12, y - labelHeight - 22);
      const verticalGap = entry.route ? 0 : 4;
      const overlaps = rectangle => rectangles.some(other => rectangle.left < other.right + 6 && rectangle.right > other.left - 6
        && rectangle.top < other.bottom + verticalGap && rectangle.bottom > other.top - verticalGap);
      if (entry.route && !compact) {
        const placement = [y, y - labelHeight - 24].find(top => top >= 12 && top <= height - labelHeight
          && !overlaps({ left: x - labelWidth / 2, right: x + labelWidth / 2, top, bottom: top + labelHeight }));
        if (placement !== undefined) y = placement;
      }
      const rectangle = { left: x - labelWidth / 2, right: x + labelWidth / 2, top: y, bottom: y + labelHeight };
      const outside = point.z < -1 || point.z > 1 || rectangle.left < 12 || rectangle.right > width - 12 || y < 12 || y > height - labelHeight;
      const collision = overlaps(rectangle);
      const obstructed = blocked.some(other => rectangle.left < other.right && rectangle.right > other.left && rectangle.top < other.bottom && rectangle.bottom > other.top);
      button.hidden = outside || obstructed || (node.id !== selected && node.id !== hovered && (collision || (!important && count >= (scale < 1.1 ? 12 : 42))));
      if (button.hidden) continue;
      button.style.left = `${x}px`;
      button.style.top = `${y}px`;
      button.style.zIndex = important ? "3" : "1";
      button.classList.toggle("is-selected", node.id === selected);
      button.classList.toggle("is-hover", node.id === hovered);
      if (node.id === selected) button.setAttribute("aria-current", "true");
      else button.removeAttribute("aria-current");
      rectangles.push(rectangle);
      count++;
    }
    return count;
  }

  return { setNodes, update, select(id) { selected = id; }, hover(id) { hovered = id; }, dispose() { layer.remove(); entries = []; } };
}
