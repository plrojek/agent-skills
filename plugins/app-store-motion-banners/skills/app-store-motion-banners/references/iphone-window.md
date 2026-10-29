# What an iPhone shows of a header video, and how to measure it

## The measured window (iOS App Store, product page, portrait; measured 2026)

It was measured from a screenshot of a live product page whose header was a 3840×1646 video. A photo of the same phone showed the Dynamic Island, which screenshots leave out.

| Thing | Artboard px (1920×823) | Video px (3840×1646) | Notes |
|---|---|---|---|
| Visible window | x 336–1584, y 0–823 | x 672–3168, full height | the full height and the centre ≈65% of the width; aspect ≈1.52 |
| Status bar | y 0–171 | y 0–342 | 54 pt; clock and battery glyphs at y ≈66–115 |
| Dynamic Island | x 760–1160, y 36–154 | x 1520–2320, y 72–308 | ≈126×37 pt at y 11 pt |
| Back button | x 389–524, y 186–327 | | glass circle |
| Mute + share capsule | x 1219–1533, y 186–327 | | glass capsule |
| Narrowest phones | buttons reach x 554 (left) and x 1147 (right) | | the centre gap at the button row is only ≈590 px |

The scale is 393 pt ↔ 1248 artboard px, so 3.176 artboard px per pt.

**Rules that follow:**
- nothing readable and no distinct object above y 345 inside the window;
- headline, words and hero motion in x 430–1490, y 345–790;
- keep a photo credit inside the window too, if the photo shows there;
- x < 430 and x > 1490 are iPad/Mac decoration.

**Why this matters:** a common first design puts the app icon at the top centre and a two-line headline at the top. On the phone the icon then sits exactly under the Dynamic Island and the headline runs into the clock and the buttons. Phones and motion placed at the sides are cropped away, and the visible centre looks static.

## How to measure it again (new device, new iOS, a different page type)

1. Get a **screenshot** of the live product page (exact pixels) and, if anything looks hidden, a **photo** of the phone (it shows the island).
   - A photo taken in a mirror or with the front camera is flipped. Read positions, not text direction.
2. Pick 2–3 features you can find in both the screenshot and the source frame: the left and right edges of a headline, the bottom credit line, the top of an icon.
3. Work out the scale from a horizontal distance (source px per screenshot px). Check it against a vertical one. The banner's height in the screenshot × the scale tells you whether the full height is shown.
4. Work out the window offset from the matched features, then read the overlay rectangles (status bar, island, buttons) off the screenshot and photo in the same units.
5. Update the numbers in `scripts/iphone_mock.py` and `scripts/iphone_preview.sh` (crop `2496:1646:672:0`). The safe-zone checks in `scripts/make_header.py` (pins) use the same numbers.

The App Store Connect preview tool is worth a look, but trust a device screenshot over it. The universal 16:9 *image* header uses a different window (roughly the top-centre band); don't apply that window to video headers.
