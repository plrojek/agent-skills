# Using an existing design (step 4b)

When the app already has a header design, keep it. It might be a designer's export, an earlier banner page or a hand-written HTML/CSS scene. The pipeline needs only an HTML page: the stills, the render, the checks, the iPhone preview and the upload copy work the same as for a generated page.

## What the page must do for the renderer

`render.mjs` opens the page at a 1920×823 viewport with a device scale of 2 (so the video is 3840×1646). It waits for fonts and images, pauses every animation in `document.getAnimations()`, and seeks each one to the frame's time.

- **Size:** one stage element of 1920×823 CSS px at the top left, with `overflow:hidden`, and `html,body{margin:0}`.
- **CSS motion only:**
  - CSS animations, CSS transitions and the Web Animations API render exactly.
  - Motion driven from JavaScript stays frozen: `requestAnimationFrame`, timers, canvas drawing, `<video>`, and Lottie or other script players.
  - Convert that motion to CSS keyframes.
- **Seamless loop:**
  - give every animation `infinite` iterations and a period that divides the loop (10 s: 1.25, 2.5, 3.333, 5 or 10 s);
  - set phases with a **negative** `animation-delay`. A positive delay leaves the element unanimated for the first seconds, so the last frame no longer matches the first.
- **Assets:**
  - every `<img>` must load, or the render stops and names the missing file;
  - CSS background images aren't checked, so look for them in the stills;
  - web fonts load from the URLs in the page.
- **No content that changes per run:** no clock, `Date.now()` or random values at load time.

## Fixing the layout for the iPhone

1. **See it as the phone does.** Render stills (`render.mjs … --stills 1.2,4.6,8.0`) and put each through `iphone_mock.py <still> <out> --guides`.
2. **Move blocks instead of redesigning:**
   - **Text:** change the block's `top` and `left`, or wrap it in a container with `transform: translate()`, so that readable text starts at y ≥ 345 inside x 336–1584.
   - **A brand mark or object in the top band:** move it into the window along its own path. In SVG, wrap the group in `<g transform="translate(dx dy)">`; gradients with `gradientUnits="userSpaceOnUse"` move with it.
   - **Devices and other side decoration:** move them to the outer strips (x < 430 or > 1490). Only iPad and Mac show those.
   - 🔴 **Z-order:** insert a new element after the ones it must cover. A later element paints on top unless `z-index` says otherwise.
3. **Put motion where the phone looks.** If everything that moves sits at the sides, move one moving element into x 430–1490 or add one there. For example, a real UI card from the app that pops next to the brand mark every 5 s.
4. **Repeat** until every still passes, in every language. Then continue with steps 5–8 of `SKILL.md`.

**Worked example (anonymised).** A dark alert-app header had its wordmark under the status bar and its brand mark (a pin on a river) behind the share button. The fix:
- the text block moved down;
- the pin, its halo and its rings moved together along the river into the centre;
- a real status card from the app was added after the side phones, so it paints above them, and pops next to the pin every 5 s;
- one word of the wordmark glows in time with the pin's rings (2.5 s).

## Minimal skeleton

```html
<!doctype html><html><head><meta charset="utf-8"><style>
html,body{margin:0;background:#000;overflow:hidden}
.stage{position:relative;width:1920px;height:823px;overflow:hidden;background:#1e293b}
/* readable text starts at y 345, centred in the iPhone window */
.head{position:absolute;left:0;top:352px;width:1920px;text-align:center;font:800 74px/84px system-ui,sans-serif;color:#fff}
/* a UI card that pops every 5 s: 5 divides the 10 s loop; the negative delay sets its phase */
.card{position:absolute;left:760px;top:520px;width:400px;animation:pop 5s ease-in-out infinite;animation-delay:-1s}
@keyframes pop{0%,100%{opacity:0;transform:translateY(40px)}20%,80%{opacity:1;transform:none}}
</style></head><body><div class="stage">
<div class="head">Your headline here.</div>
<img class="card" src="crops/card.png" alt="">
</div></body></html>
```
