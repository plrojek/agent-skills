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
  readers otherwise didn't know which way to scroll.
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

## Publishing

- **noindex is a request, not a lock.** The page needs access control on the server; see publishing.md.
- **An 11-digit number in a note is probably a PESEL** copied from a land register or an act. The
  public copy masks every one; the local file, sent to family, still carries them.
- **The family book is a PDF and can't be filtered afterwards.** Build it from the page you publish.
- **A CDN can cache a page you meant to keep private.** Send `Cache-Control: private, no-store` and
  `CDN-Cache-Control: no-store`, then check with a request that has no credentials.
