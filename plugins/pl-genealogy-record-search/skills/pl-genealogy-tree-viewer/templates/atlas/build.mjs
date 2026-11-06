// Atlas 3D bundle for pl-genealogy-tree-viewer. Made by Applied AI (https://appliedai.dev),
// https://github.com/plrojek/agent-skills (MIT; three.js is MIT, its licence stays inline in the bundle).
// Rebuild after editing src/:  npm install && npm run build   (writes atlas.bundle.js and atlas.css here)
import { build } from "esbuild";
import { copyFile, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const result = await build({ entryPoints: [resolve(here, "src/controller.js")], bundle: true, format: "iife",
  globalName: "FamilyAtlas", minify: true, write: false, target: ["es2020"], legalComments: "inline",
  charset: "utf8", supported: { "template-literal": false } });
// the bundle goes inline into a <script> of the tree page
const script = result.outputFiles[0].text.replace(/<\/script/gi, "<\\/script");
await writeFile(resolve(here, "atlas.bundle.js"), script);
await copyFile(resolve(here, "src/style.css"), resolve(here, "atlas.css"));
console.log(`atlas.bundle.js: ${Buffer.byteLength(script)} bytes`);
