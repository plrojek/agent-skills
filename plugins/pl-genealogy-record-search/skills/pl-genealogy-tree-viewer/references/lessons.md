# Lessons: what went wrong in a real tree and the rule that came out of it

Each item cost at least one session in a tree of about 600 people. The viewer and the builder already
follow them; they are here so a change to either doesn't undo one.

## Data

- **Key descriptions by name, never by a guessed xref.** The first version keyed wall descriptions by
  xrefs typed from memory, and the text for one man's birth act landed under an unrelated woman. Keys
  are `Name|year` or a looked-up xref; a key that matches no one is printed, never dropped silently.
- **No key may match everyone without a name.** A `"(bez imienia)"` key would attach to every future
  person without a given name.
- **A note is not doubt.** Defaulting every person with a note to "probable" put a badge on half the
  family, including people a relative named from memory. Only explicit markers (`TIER: …`), the
  override table and transcribed acts set a tier. Facts the family gives are certain unless someone
  says otherwise.
- **The tier follows the transcription.** Whoever is named in a transcribed act gets `akt`. Without
  this rule, people whose acts were already in the package still showed as "probable".
- **(?) marks only uncertainty that comes from the research** (`praw`, `hip`, hypothetical parents),
  not people without a source: marking all of those turns the sign into background noise.
- **A couple with a shared child is not a marriage.** Shown as "Dziecko z" with a dotted grey line, not
  as "Małżonek"; "partner" wording was rejected by the family. Kinship goes by blood, not through the
  couple, so an unmarried mother's sister is "great-great-grandmother's sister", not "mother of a
  great-great-grandfather's son".
- **Conflicting sources are shown, not resolved by the tool.** Values verbatim from the notes, the
  status only what the evidence decided. A conflict never changes the tier or the value in the tree.
- **When the acts win, the old value stays on the card.** Four acts gave a great-grandfather's father a
  different given name than the family tree had. The tree now carries the acts' name, and the card
  shows the old one twice: in a conflict marked "rozstrzygnięta według aktów" and in a `🔁 ZMIANA`
  note naming the acts. A relative who remembers the old name finds why it changed instead of
  thinking the page is wrong.

## Branches (lines)

- **The anchor of a line is at its bottom.** The family view unfolds upwards; an anchor chosen as the
  earliest-born person was a child who died at eight, and the "line" showed four siblings.
- **The default bucket is its own label.** When the fallback was one of the real lines, a dozen people
  the algorithm didn't reach sat in the wrong family. Unassigned people go to "poza znanymi gałęziami",
  and that tab only appears when someone is in it.
- **Blood first, then spouses, in a loop.** A line is the anchor's ancestors and all their descendants
  over parent–child edges only (spouses would merge lines). Married-in spouses join their partner's
  line, then the spouse's own family follows, and this repeats until nothing changes: run once, the
  cascade stopped one level short and sixteen people fell out.
- **A line never hides people in the drawing.** Filtering the drawing by line hid a person's own
  children whenever they belonged to the other parent's line (everyone has exactly one line). Lines
  narrow the List only; choosing a line puts its anchor in the centre of the whole tree.
- **"Hide hypothetical branches" works on graph components, not tiers.** Remove the hypothetical
  family edges, keep the largest component as the core, hide what only rejoins it through those edges.
  Otherwise a filter for hypotheses also hides documented people who are merely loose.

## Evidence

- **Judge a role by its first part.** Excluding any role containing "wymieniony" also excluded
  "dziad dziecka — wymieniony jako ojciec matki", the maternal grandfather; and "ojciec dziecka,
  zgłaszający" is a father who also reported the birth.
- **Never back a hypothetical link.** A baptism naming "Jan, son of Józef" doesn't prove the tree's Jan
  is that child, when that is precisely the hypothesis. Hypothetical families get no
  backing, and a person with hypothetical parents gets no birth evidence.
- **A fact without an act mark is not uncertain.** Say so in the legend, or readers take every unmarked
  date as doubtful.

## Lines and colours

- **Give each grandparent's line its own background.** A line holds both of its anchor's parents'
  families; with nothing but the line to go by, a reader can't tell the father's side from the
  mother's in a deep tree. Each line splits into its anchor's father's and mother's lines, a band
  behind each run of neighbouring tiles of one line, rows of one line joining into one field, and
  the label "linia: …" pinned to the top-left of the visible part of the field.
- **The people the tree is for get no band.** They are in two anchors' lines at once; colouring them
  after either would be wrong.
- **Hues stay away from the sex and tier colours**, or a band reads as "female" or "probable". The
  father's side cool, the mother's warm. Two couples' parents can share hues: their ancestors never meet
  in one person's tree.
- **One colour language everywhere.** The same hue in the family view, the map, the fan, the minimap
  and the path bar; a view in its own colours would have to be learned again.

## Path bar

- **Show the route, not only the kinship word.** "pradziadek" tells a reader what, the route
  "me › father › grandfather › great-grandfather" tells them through whom, and each step is clickable.
  It starts at the person the tree is for (`ME`) until a reader marks "to ja" on their own device.
- **The bar keeps a constant height in every tree view**, so switching views doesn't make the drawing
  jump; it hides on the List, the start screen and while the kinship path is open.

## Layout

- **Couples stand together; spacing comes from contours.** Pulling each ancestor towards its child
  within its own subtree separated spouses by hundreds of pixels. Couples are one node; subtrees are
  pushed together by their row-by-row contours, groups placed by isotonic regression (PAV).
- **Test the layout with every person in the centre**, with side relatives off and on: no two tiles
  in a row closer than a tile's width, nobody twice. `check_tree.py` does this; run it after any layout
  change. In the real tree that is about 1 100 layouts in under two seconds.
- **The family view never "fits everything".** Fit the person with parents, partner and children at a
  readable scale; the rest is scrolled to. The whole-tree map is the one that fits everything, with
  level of detail (dots and family names → names → tiles).
- **The direct line is drawn thicker**, and an edge hint points to parents that are off screen;
  readers otherwise didn't know which way to scroll. At far zoom the thick lines merged into one
  smear: thinner there.
- **Far out, names instead of dots.** The map's dots told nobody anything. Names at a constant size on
  screen, as many as fit without overlapping, the centre person, search hits and the direct line first;
  computed a tenth of a second after the last movement, not every frame. The map's narrow tiles switch
  to dots only below zoom 0.5: lower, their labels would be under 9 px.
- **On a computer the card is a wide panel, not a column.** A narrow column cut the act transcriptions
  into short lines. The panel opens on a click and closes with ✕ or Esc; the tree shifts by half the
  width change so the person in the centre stays in the middle.
- **Two-line labels when zoomed out use `dy` in `em`.** The label font grows as 1/zoom to keep its
  size on screen; a fixed `y` in SVG units lets the lines drift onto each other.

## Interaction

- **History is the browser's.** Every view change is a `pushState` step, so the phone's back gesture and
  the browser's back button return to the previous person and framing. Replacing the URL instead made
  "back" leave the tree. The back button says where it goes ("← Lista", "← <name>").
- **Wheel zoom is proportional to the scroll amount.** A fixed factor per wheel event made trackpads
  (dozens of events per gesture) jump by orders of magnitude. One notch ≈ 7 %; trackpad pinch
  (`ctrlKey`) has its own sensitivity; `+`/`−` keys and buttons step smoothly ×1.25.
- **Dragging the tree must not select text** (`user-select:none` on the stage, `preventDefault` on
  mousedown), while the card and the List stay copyable.
- **Safari sends no dblclick for touch**: double tap is detected by hand.
- **Phone layout**: the card is a bottom sheet whose *height* changes (a transform left the bottom of
  the card unreachable), a tab bar replaces the header buttons, the "More" menu needs a higher z-index
  than the start screen and the sheet, and a one-time gesture hint explains pinch and the sheet.
- **"O drzewie" belongs on the start screen, not in a side window.** Opened at start, the window
  covered the tree on a computer and was a second thing to close. Under the family cards it is read
  in passing: first where to go next, then the description, the lines, the oldest ancestors, the
  legend; the header's "O drzewie" scrolls down to it.
- **A screen that scrolls inside the zoomable stage must keep its wheel.** The start screen and the
  List sit in the stage, whose wheel handler took every event as zoom. Once "O drzewie" made the
  start screen longer than the window it could not be scrolled; the handler now lets the wheel
  through on both.

## Ancestor picture

- **Relatives want a picture they can print or send**, not a link to a page. It is built as an SVG
  with explicit colours and fonts, because a saved file can't see the page's styles; PNG and JPG
  are that SVG drawn on a canvas.
- **Safari limits a canvas to about 16 million pixels and 16 000 px a side**, and sometimes draws the
  photos inside an SVG only on the second pass: cap the size and draw twice.
- **Sharing on a phone needs a fresh tap.** Preparing the file takes long enough that the browser no
  longer counts the tap as the user's (`NotAllowedError`): keep the file and ask for one more tap.
- **Hypothetical parents stay dashed in the picture too**, and dates and places of people presumed
  living are off by default: the picture leaves the family's hands more easily than the page.

## The page and its code

- **The builder writes the whole page from the template.** Hand edits go into your copy of
  `templates/viewer/tree.html` (`--template`), never into the output.
- **Find the data lines by their content.** Code that replaced "line 455" kept working until the CSS
  grew by 75 lines; then it overwrote two style lines and left the real data in place. Match lines that
  start with `const DB = ` and `const IMG = `.
- **Class names must not collide with tier names.** `.akt` is the tier badge; the act box is `.zrd`.
- **A global `svg{position:absolute}` styles every icon.** It is meant for the tree canvas; an inline
  SVG icon needs its own `position:static` and size.
- **In a `@media` block the later rule wins**: add overrides at its end.
- **Chrome caches `file://` pages.** After a rebuild, reload ignoring the cache. In Playwright a `goto`
  that only changes the `#hash` doesn't reload: go through `about:blank`.
- **Headless screenshots catch the tiles mid-move.** Under `--virtual-time-budget` the animation
  frames of a centre change don't run, so new tiles stay invisible and old ones where they were.
  For a screenshot, set the centre person and call `render()` and `view()` directly instead of `go()`.

## The family book

- **One book per family, not one book for everyone.** Relatives read their own lines: the whole
  tree's book given to one side of a couple is mostly the other side's family. `--lines` picks the
  chapters, and the book keeps only the acts that name someone in them (the index likewise);
  without that filter a two-line book carried every act of the tree.
- **Say what a generation is to the reader.** Chapters count from the anchor, who is normally the
  reader's parent, so "Dziadkowie" in a chapter are the reader's great-grandparents and every header
  had to be translated in the reader's head. With `--reader` each header says both ("Dziadkowie · dla
  Tomasza: pradziadkowie") and the anchor is "ojciec Tomasza".
- **A fan of every known ancestor, not of a fixed number of generations.** A six-generation fan with
  a field for every possible ancestor left out the 7th–9th generations a tree had reached and spent
  most of its area on empty fields. Only a known ancestor gets an angle, as much as their name needs;
  a branch with no further ancestors simply ends; a half circle when that fits, otherwise a full
  circle; letters shrink to 0.7 rather than names being cut, and grow to 1.25 when there is room.
- **Measure the fan against the page.** A full circle taller than a landscape page's content area
  moved to the next page and left an empty one: the fan's height has a cap per page type.
- **The fan's centre needs two lines.** "Tomasz i Ewa" cut to "Tomasz i…" in one line; a label with
  " i " is split, the second line starting with "i".
- **Paper has no links.** The print edition gives page numbers in the contents, in the index and next
  to every reference to another chapter. A number makes a line longer and can move a page break, so
  the book goes through Chrome until the numbers stop changing (two passes usually, at most four),
  read back from the PDF's named destinations. It also gets a wider margin on the binding side and
  the front fans on landscape pages. The screen edition keeps the links and no page numbers.
- **`break-inside: avoid` on a whole act put one act per page** when a transcription was long. Only
  the act's header and its scan crop are kept together; the transcription may break.
- **Children known only from a count are one phrase.** Three children recorded without given names
  printed as "Kowal, Kowal, Kowal"; they are "3 dzieci o nieznanych imionach".
- **Place strings exported from tree sites carry litter**: "---, ", a postcode, "X / X Voivodeship,
  Poland". The book prints the place itself.
- **Three act marks are enough after one fact.** A parent proven by many acts drowned the line in
  marks; the book shows three and "+N" (every act still lists its people).
- **Put each act under the entry it proves, not in an appendix.** With all acts in an appendix at
  the back, readers flipped between an entry and the act behind it a hundred pages later. Each act
  stands once, right under the person it is about: a birth act under the child, a death act under
  the deceased, a marriage act after the entries of both spouses (§2n and §2n+1 stand side by
  side). The birth act of an ancestor's sibling, who has no entry, goes under their parents. Every
  other person named in the act gets "Wymieniony także w aktach: D12 (świadek)" at their own entry.
  Only acts naming nobody in the chapters go to "Pozostałe dokumenty" at the end; a one-family book
  has none. Number the acts D1… in the order they stand in the book, not in the tree's order.
- **A row crop's frame fits the crop.** `width: 100%` with `object-fit: contain` drew a page-wide
  frame around a narrow row; the image keeps its own size, capped at the column width and 70 mm.
- **An act that may be about someone proves nothing about them.** A role marked `KANDYDAT` made the
  person "akt" because everyone named in an act was raised; now such a role raises no tier, and the
  book marks the act "hipoteza".

## Publishing

- **noindex is a request, not a lock.** The page needs access control on the server; see publishing.md.
- **An 11-digit number in a note is probably a PESEL** copied from a land register or an act. The
  public copy masks every one; the local file, sent to family, still carries them.
- **The family book is a PDF and can't be filtered afterwards.** Build it from the page you publish.
- **A CDN can cache a page you meant to keep private.** Send `Cache-Control: private, no-store` and
  `CDN-Cache-Control: no-store`, then check with a request that has no credentials.
- **A redacted name must go everywhere it is used.** A living person's name also labels a
  grandparent's line; the redaction replaces it there too, and lines whose anchor is presumed living
  are printed so their labels can be changed.
- **Mask numbers in the data, nowhere else.** An 11-digit run can occur inside base64, and the Atlas
  3D code (three.js) holds one too; masking line by line broke a photo once and would break the atlas.
  Only the strings inside `const DB` are masked, which is where a PESEL in a note ends up.
- **Posters read the published data.** The poster page's `people.json` is made from the page after
  `--living`, so a person redacted on the tree is redacted on every poster too.

## Atlas and posters

- **One page that opens from disk.** The Atlas 3D needs three.js; loading it from a CDN would make the
  page depend on the network and leak visits. It is bundled (about 0.7 MB) and inline, and the page
  still works from a USB stick. The poster page is the exception: it is a module that fetches
  `people.json`, so it needs a web server.
- **A print window does not do posters.** Printing the poster SVG through the browser's print window
  relied on `@page { size: … }`; Safari ignores it and cut an A1 poster onto two A4 pages (the left of
  the tree on one, a strip on the other). The configurator draws the same SVG on a canvas and writes a
  one-page PDF in the poster's size itself: up to 300 dpi, the canvas capped at about 40 million pixels
  and 16384 px a side (an A1 comes out at about 227 dpi), half the pixels on retry when a phone's canvas
  limit leaves it blank. The PDF's text is raster; the SVG keeps vector text.
- **Safari draws an SVG image at its own size, then scales it.** Rasterising `width="841mm"` at
  227 dpi gave blurred text; the SVG gets the target pixel size before it is drawn.
- **Nothing that appears during a drag may change the preview's size.** The overlap warning sat under
  the poster; dragging a cartouche onto another showed it, the preview lost height, the poster shrank and
  jumped away from the cursor, and back again. Warnings now stand in the caption row, on one line.
- **Keep the illustration element across redraws.** Every drag step rebuilds the SVG; reusing the same
  `<image>` keeps a 5 MB JPEG from being decoded again on each pointer move.
- **Credit where people look, not on what they hang.** The footer of every page and the book's last
  page say "Made by" with the Applied AI wordmark; posters and exported pictures carry nothing.

## Dates

- **A death without a date is still a death.** Tree sites export "deceased" as `1 DEAT Y` with no date.
  The builder dropped it, so dozens of the dead looked alive: no death on the card, and `--living`
  would redact them. Such a death becomes "data nieznana".
