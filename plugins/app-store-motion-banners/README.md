# app-store-motion-banners

App Store product-page header videos that work on an iPhone. Nothing hides under the Dynamic Island, and the motion sits in the part of the banner the phone actually shows.

```
/plugin marketplace add plrojek/agent-skills
/plugin install app-store-motion-banners@plrojek
```

![Top: a frame of a demo header with the part an iPhone crops off darkened and the band it covers tinted red. Bottom: what an iPhone shows of two demo apps, a light to-do app and a dark stats app, with the status bar, Dynamic Island and store buttons drawn on top. Demo assets.](docs/iphone-view.jpg)

My app's header video looked fine in App Store Connect. On my iPhone it didn't:
- the app icon sat right under the Dynamic Island;
- the headline ran into the clock and the back and share buttons;
- everything that moved was at the sides, which the phone crops off.

I measured what an iPhone shows from a screenshot of the live page. It shows the full height of the video but only the middle 65% of its width, and the status bar, the island and the store's buttons cover the top 40% of that. This skill builds the header around those numbers:

1. **It cuts real UI pieces** (cards, chips, chat bubbles) out of your app's screenshots, with exact edges and rounded corners.
2. **It generates the scene from a small JSON file,** in your app's colours, fonts and artwork:
   - the headline;
   - your store subtitle words as tabs;
   - one act per word, in which the UI pieces fly in and leave in a cascade;
   - optionally: your own artwork that drifts, floats, pulses or spins; markers that drop onto points you choose; phones at the sides for iPad and Mac; a built-in city skyline.

   If you already have a header design in HTML, it keeps that and only fixes the layout for the phone.
3. **It renders the loop frame by frame** in Chrome and encodes it the way App Store Connect accepts it. It avoids B-frames, which make the video flash black every time it loops.
4. **It checks every file:** level, colour tags, B-frames, the edit list and the loop seam. It also shows you what the iPhone will show, with the status bar, island and buttons drawn on top.
5. **It makes a copy under 10 MB** for uploading through a browser.

I made the headers for two of my apps with it, in three languages. One was generated from a scene file. The other was an existing design: I moved its parts out from under the island and the buttons, and ran it through the same render and checks. Ask Claude something like "make an App Store header video for my app". It should pick the skill up, ask for your copy and screenshots, and show you the iPhone view before rendering everything.

A few things to know:

- **Requirements:**
  - Python 3.9+ with Pillow, plus numpy for the check;
  - Node with Playwright;
  - Google Chrome or Playwright's Chromium;
  - ffmpeg.
- **Speed:** a 10-second 3840×1646 file takes about 3 minutes to render on a recent Mac.
- **Measurements:** the iPhone numbers come from one device in 2026. The skill explains how to measure again from a screenshot; do that if your header is already live.
- **Scope:** it lays out the product-page header (21:9). The renderer, the check and the upload copy work for a 3:2 search-result video too, but the scene generator only makes headers.
- **Real screenshots only.** It cuts pieces from your screens and doesn't invent UI, data or copy.

## What it runs, downloads and sends

The skill tells Claude to run its Python, shell and Node scripts. There are no hooks and no MCP servers.

- **Programs it runs:**
  - `python3` with Pillow and numpy;
  - `node` with `playwright`, which drives a headless Chrome or Chromium that opens the generated HTML page from your disk;
  - `ffmpeg` and `ffprobe`;
  - `uv`, only to get Pillow when your Python doesn't have it.
- **Downloads:**
  - the web fonts named in your scene, when the page loads (Google Fonts in the example);
  - Playwright and its Chromium, only if you install them.
  - Nothing else.
- **Sends nothing.** Your screenshots, crops, pages and videos stay in the folder you work in.

## License

MIT. Source: [github.com/plrojek/agent-skills](https://github.com/plrojek/agent-skills).
