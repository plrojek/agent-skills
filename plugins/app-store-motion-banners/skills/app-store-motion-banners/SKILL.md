---
name: app-store-motion-banners
description: Make App Store product-page header videos (21:9, 3840x1646, seamless 10 s loops) that work on an iPhone. Nothing sits under the Dynamic Island, the status bar or the store's back/share buttons, and real UI pieces from the app's screenshots move in the part an iPhone actually shows. The video is rendered frame by frame from an HTML/CSS scene with Playwright and ffmpeg, checked for spec and loop problems, and copied under 10 MB for browser upload. Use it when asked to make, fix or animate an App Store header or banner video or a product-page header, or when a live header looks cut off by the Dynamic Island or "doesn't move" on a phone.
---

# App Store motion banners

**Outcome:** per language, a header video that App Store Connect accepts:
- H.264 High, 30 fps, BT.709, no audio, 10 s seamless loop;
- an iPhone preview of it with the status bar, island and buttons drawn on top;
- a ≤10 MB upload copy;
- a suggested poster frame.

**What it needs:**
- Python 3.9 or later with Pillow, plus numpy for QA (or `uv`: the preview script falls back to `uv run --with pillow`);
- Node with `playwright` (run `npm i playwright` in the working folder, or set `PW_FROM` to a `package.json` that has it);
- Google Chrome, or Playwright's Chromium;
- `ffmpeg`/`ffprobe`.

It runs locally and sends nothing anywhere. The scene loads web fonts from the URLs you put in it (Google Fonts by default).

## The fact that drives the layout

On an iPhone (portrait, App Store product page) the header shows the **full video height** but only the **centre ~65% of its width**. The top ~40% of that is covered:

- **Window:** x 336–1584 of the 1920×823 artboard. The artboard renders at 2× = 3840×1646.
- **Covered:**
  - status bar, y 0–171;
  - Dynamic Island, x 760–1160, y 36–154;
  - back button, x 389–524, y 186–327;
  - mute + share capsule, x 1219–1533, y 186–327.
  - On the narrowest phones the buttons reach x 554 / 1147.
- **Rules:**
  - nothing readable and no distinct object (icon, logo, pin) above **y 345** inside the window;
  - the headline, the words and the hero motion go in **x 430–1490, y 345–790**;
  - x < 430 and x > 1490 show only on iPad and Mac.

How this was measured, and how to re-measure on a new device or iOS version: `references/iphone-window.md`. Re-measure whenever you can: one screenshot of the live page is enough.

## Workflow

1. **Inputs.** Get these from the user:
   - the approved copy: the headline and the store subtitle words. One animated "act" per word.
   - real app screenshots (simulator captures at @3x are ideal), plus the brand colours and fonts;
   - the languages;
   - any photo credits that must stay visible.
   - Don't invent UI, data or copy. Don't put URLs in the asset (Apple's rule).
2. **Check the window.**
   - If a header is already live, ask for a screenshot of the product page. If something looks hidden, also ask for a photo of the phone: screenshots don't show the island.
   - Run any frame through `scripts/iphone_mock.py <frame> <out.png> --guides` to see it as the phone does.
3. **Cut the UI pieces** (cards, chips, chat bubbles) from the screenshots.
   - `scripts/measure.py col|row|grid` finds exact rectangles. Cards sit on a flat background, so runs of colour give the edges to the pixel.
   - `scripts/crop_ui.py crops.json crops/` cuts them with anti-aliased rounded corners. Per-corner radii handle a chat bubble's tail; `pad_bottom` fixes a card cut short by the tab bar. Example spec: `references/crops.example.json`.
   - Check a contact sheet of the crops on the banner colour before using them.
4. **Write the scene** (`scene.json`, documented at the top of `scripts/make_header.py`; example in `references/scene.example.json`) and generate the page:
   `python3 scripts/make_header.py scene.json page.html`
   - Layers: gradient + glow + orbiting light; optional skyline with twinkling windows and pins dropping onto rooftops; headline; words as tabs (the lit one pops); per act, cards fly in with overshoot, bob and leave in a cascade; optional side phones for iPad/Mac (one can swipe its screen with the acts); credit line.
5. **Look before rendering:**
   - `node scripts/render.mjs page.html 1920 823 shots/s --stills 1.2,4.6,8.0`
   - then `iphone_mock.py` on each still.
   - Fix overlaps, empty areas and anything touching the covered zones. Check every act and every language: words have different lengths.
6. **Render the loop:**
   - `node scripts/render.mjs page.html 1920 823 out/header_<lang>_3840x1646_10s_loop.mp4 --offset <s>`
   - Choose the offset so frame 0 shows a complete act: the poster frame is usually picked near the start. It takes about 3 minutes per file on a recent Mac.
7. **Check and package:**
   - `python3 scripts/qa.py out/`: every file must print PASS.
   - `scripts/iphone_preview.sh out/<file>.mp4 previews/` makes a small MP4 and a GIF of what the phone shows. Send that to the user, not the full frame.
   - `scripts/upload_copy.sh out/<file>.mp4 upload/<file>.mp4`: a ≤10 MB copy with the same specs, for browser uploads.
8. **Hand off:**
   - Suggest a poster frame time: **it cannot be changed after approval**.
   - Say that replacing a live or already-reviewed header means a new review.
   - Remind the user to check the App Store Connect preview: iPhone and iPad, both orientations, each language, Dark Mode.

Smoke test without any real app: `python3 scripts/make_demo.py demo/` builds synthetic screens, cards and a scene.

## Design rules that matter

- **Loop math:** every animation period must divide the loop length (10 s: 1.25 / 2.5 / 3.333 / 5 / 10 s). One period that doesn't divide it breaks the seamless loop. `qa.py` reports the seam.
- **One act per subtitle word:** 3 words = 3.333 s each, 4 words = 2.5 s each. Tighten the card stagger for 4 acts so the last card still holds for about a second.
- **Real captures only.** Crops are fine. Leave out any crop whose text breaks the copy rules (sources, sirens, disclaimers…).
- **Keep the motion in the window.** Motion in the side strips is invisible on the phone; that is the usual reason a header "doesn't move" there.
- **Drop the app icon** from the top centre. The store shows the icon right under the header, and the top centre is the island.
- **Readable at ~50% of in-app size:** cards with photos (food, places) read best; icon-only rows look empty.
- **Uneven card heights** (two-line titles): use a masonry layout (two columns that end at different heights), not a forced grid.
- **To fix an existing design** that is fine apart from the layout, patch its HTML (move blocks into the safe zone; move a brand mark along its own path) instead of starting over. 🔴 Mind the z-order of anything you insert.

More: `references/design-lessons.md`.

## Encoding foot-guns (all handled by the scripts)

- **No B-frames (`-bf 0`).** With B-frames ffmpeg writes an MP4 edit list (media time ≠ 0), and players that loop by seeking flash black at every restart. No frame is actually black.
- **Level comes from the macroblock *rate*,** not only the frame size. 3600×2400 at 30 fps needs level 5.2.
- **Colour tags:** BT.709 must be in the container **and** the H.264 bitstream (`h264_metadata`). `-color_*` flags alone don't reach the bitstream.
- **Size and sources:** a 10 s 3840×1646 master is ~16–28 MB at crf 16. Browser-extension upload paths often cap files at 10 MB, so make the upload copy.

Specs and sizes: `references/specs.md`.

## Files

- `scripts/make_header.py`: scene.json → animated HTML page (the header layout above).
- `scripts/render.mjs`: deterministic frame-by-frame render to MP4, or stills.
- `scripts/measure.py`, `scripts/crop_ui.py`: find rectangles, cut UI pieces.
- `scripts/iphone_mock.py`, `scripts/iphone_preview.sh`: what the iPhone shows (still, video, GIF).
- `scripts/qa.py`: spec, B-frame, edit-list and loop-seam check (PASS/FAIL).
- `scripts/upload_copy.sh`: a ≤10 MB two-pass copy with the same specs.
- `scripts/make_demo.py`: synthetic demo assets and scene.
- `references/`:
  - `iphone-window.md`: the measured window and how to re-measure it;
  - `specs.md`: Apple's sizes and the encoding settings;
  - `design-lessons.md`: what worked and what didn't;
  - example JSON files.
