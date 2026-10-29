# Design lessons (what worked and what didn't)

These come from making header videos for two apps: a city-guide app on a bright blue gradient, and a dark-themed alert app with a brand mark (a pin on a river).

## Layout

- **Measure the phone first.** A full-frame preview misleads: the iPhone shows only the centre ~65% and covers the top ~40%. Every design decision below follows from `iphone-window.md`.
- **One-line headline** just under the button row (y ≈352–436 at 74 px). A two-line headline doesn't fit between the buttons, and the top line hits the island.
- **The store subtitle words as tabs** (no commas) under the headline. The active word gets a white pill that pops with overshoot, and its text turns the brand colour. Commas next to padded pills leave odd gaps.
- **The act zone** sits under the words (y ≈500–790). Each act has one "prompt" piece (a chat question, or the active filter chips) and 2–4 answer cards.
- **Remove the app icon** from the top centre: that's where the island is, and the store shows the icon right under the header.
- **Side phones are iPad/Mac decoration.** They can peek in at the iPhone window's edges, but never carry the message.

## Motion that reads on a small screen

- **Big displacement beats subtle effects.** Cards flying in from the sides with a little rotation and overshoot, then leaving upwards in a cascade, catch the eye. Faint rings and small floating chips don't.
- **One shared keyframe for all cards** (enter → bob → exit), shifted per element with a negative `animation-delay` and CSS variables for direction. Easy to keep consistent, and the loop is seamless by construction.
- **Stagger** 0.12 s for 3 acts and 0.09 s for 4. Overlapping exits and entrances make the acts cross-dissolve rather than cut.
- **Ambient motion in the covered band** (behind the status bar and buttons) is fine and adds life, as long as nothing there must be read or looks clipped. Keep distinct objects (pins, icons) out of the island's area and the buttons' area, also on the narrowest phone.

## Visual quality

- **Skyline (a city motif):** uniform rectangles with dense window grids looked cheap. What worked: varied tenement roofs (triangular, stepped, mansard, attic) and one landmark silhouette, frosted white with a vertical fade (no hard base line), and sparse windows of which ~30% twinkle warm on a 5 s cycle.
- **Pins** that drop onto rooftops, squash, bounce, leave a ripple ring and fade add constant motion in the top band. Filter their positions away from the island and the buttons.
- **UI crops** need anti-aliased rounded corners and a soft double drop shadow. Pick pieces with photos; icon-only rows look empty at half size.
- **Different card heights** (two-line titles): use a masonry layout (two columns that end at different heights).

## Content and copy

- **Real captures only.** Crops of real screens are fine; invented UI or data is not.
  - Leave out crops that carry words the copy rules forbid, e.g. a data-source name or a disclaimer.
  - In a serious app (alerts, health), keep the motion calm. Pulse the brand mark; don't add effects that imply something the app doesn't do.
- **Photo credits:** if a credited photo shows in the iPhone window, the credit line must be there too (bottom centre, small).
- **Languages:** each one needs its own crops (other content, other geometry) and its own act count when the subtitle has a different number of words. Check every act in every language through the iPhone mock: long words overflow.

## Process

- **Look before rendering:** render a few stills, put each through the iPhone mock, fix, repeat. A full render takes ~3 min per file.
- **Show the user the iPhone view** (MP4/GIF with status bar, island and buttons drawn on top), not just the full frame.
- **A design that is fine apart from its layout:** patch the existing HTML instead of regenerating it. *Example:* move the text block into the safe zone, and move a brand mark along its own path (wrap an SVG group in `translate()`; `userSpaceOnUse` gradients move with it). 🔴 Insert new elements after the ones they must cover, or the z-order hides them.
- **Keep a step log while working** (what was measured, the commands, the foot-guns). It makes the next app and the next language much faster.
