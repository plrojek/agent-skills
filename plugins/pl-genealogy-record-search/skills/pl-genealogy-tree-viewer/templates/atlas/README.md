# Atlas 3D

The "Atlas 3D" view of the family-tree page: everyone in the tree as a navigable 3D graph, with the
connection between any two people. `build_tree.py` puts `atlas.bundle.js` and `atlas.css` inline into
the page (`--no-atlas` leaves it out), so the page still opens from disk with no network and no Node.

- `src/` is the source: `controller.js` (the view and its panels), `graph.js` (people, families and
  paths from the page's `DB`), `layout.js`, `scene.js` (three.js), `labels.js`, `ui.js`, `style.css`.
- `atlas.bundle.js` is `src/` bundled with three.js 0.187.0 by esbuild 0.28.2 (`build.mjs`). To change
  the atlas, edit `src/`, then `npm install && npm run build` here.
- three.js is MIT-licensed; its licence comment stays inline in the bundle.

Made by Applied AI (https://appliedai.dev) · https://github.com/plrojek/agent-skills
