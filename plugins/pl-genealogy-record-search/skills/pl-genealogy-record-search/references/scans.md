# Scans: getting them and reading them

Read downloaded scans yourself rather than handing the user a page range: online viewers
zoom in coarse steps and pan badly, while a local JPEG can be cropped and magnified exactly.

## Getting the scans

### Skanoteka and metryki.genealodzy.pl (`skanoteka.py`)

- The viewer page `index.php?op=pg&id=<id>&sy=<sy>&kt=<kt>&plik=<file>.jpg` builds the image
  URL in JavaScript: `https://metbox<N>.genealodzy.pl/metryka_get.php?dir=<dir>&znak=<znak>&plik=<file>.jpg`.
  `dir` and `znak` are constant for one volume, and on metryki **different for each `kt`**
  (kt1 births, kt2 marriages, kt3 deaths). The script reads them once per volume.
- **File names are not page numbers.** Some volumes number by page (`007.jpg`), others by the
  acts on the page (`031-032.jpg`, `135-138.jpg`), and density differs within one parish
  (one act per scan in one year, four in another). Run `files`, download one from the middle,
  count the acts, then aim. The first file can be `000` (a title card) or `001`.
- Scans are 3000-4000 px wide, 0.4-1.2 MB. The image host throws 502s and truncates
  downloads; the script retries and rejects anything that isn't a whole JPEG.
- Skanoteka's front page lists newly added fonds; PTG adds them weekly.

### CAAK and other IIIF hosts (`caak.py`)

- The page list is in the page's `__NEXT_DATA__` (`props.pageProps.record.pages`).
- The server caps an image at 10 million pixels, so a whole page comes down at about a
  quarter of its size. **Take a region instead**: `/x,y,w,h/max/` returns that area at native
  resolution. That is the only way to read small handwriting there.

### szukajwarchiwach.gov.pl

The national archives portal is behind bot protection; scripts get a challenge page, a
real browser passes. Work in a browser session the user can see.

- Search: the terms are ANDed and matched loosely, so pair a surname with a village
  (`Kowal Wola`) and filter the results; a bare surname returns thousands of place-name hits.
- A unit page (`/jednostka/-/jednostka/<id>`) shows the scan count and the gallery,
  200 thumbnails per page (`_Jednostka_delta=200&_Jednostka_cur=<page>`).
- 🔴 **Above 200 scans the gallery numbering restarts on every page**: "Obraz 1" on page 2 is
  scan 201. Real number = N + 200 x (page - 1). Page through by navigating the tab; a
  `fetch()` of another page from the same tab returns page 1 again (the page number is
  server-side session state).
- 🔴 Don't ask for a very large page size: a single request with `delta=600` got the whole
  browser session blocked for several minutes.
- Thumbnails end in `_mid`; the same address ending in `_max` is the full-resolution image
  (~2500x3600, some 3500 px wide). Other suffixes return a 12 KB placeholder.
- In some units only odd scan numbers hold images and even ones return a "PLIK NIEDOSTĘPNY"
  placeholder (379x273 px, about 10.7 KB). In such a unit "plik N" in a Geneteka remark was
  scan 2N-1. Check a known act before trusting a mapping.
- The portal's own "download scans" returns an empty ZIP when not logged in.
- Always run `file` on the first downloaded image before fetching a batch: a folder of
  200-byte "JPEGs" is an error page saved under image names.
- Court files (`Akta spadkowe`, `Akt zejścia`) have no scans, but the unit **title** usually
  names the deceased, the village and every heir: the search index alone rebuilds a household.

## Mapping a volume before hunting in it

A unit titled like `Kopie ksiąg metrykalnych parafii X z filią Y i Z` is not one register.
It is births, marriages, deaths, **repeated for each village**, each block restarting its
years and opening with a handwritten title (`Copia Natorum de pago Y ab anno 1857`). In one
unit of about 150 scans the third village started two thirds of the way in; miss that and you read the right years
in the wrong village all afternoon.

1. **Year map**: `contact_sheet.py sheet` over every ~13th scan, top strip only
   (`--y 0 0.13`; landscape birth books `--y 0.12 0.24 --x 0.13 0.62`). One image read gives
   the block boundaries, register types and years. The year is printed in the table header,
   and also written mid-page as an `Annus 186x` banner. Write the scan-to-year table into the
   research note: it is the expensive part and it never changes.
2. Then a second sheet over the target block to pin the year and month.
3. **Jump and magnify**: `contact_sheet.py crop` on a half page (`--x 0.04 0.49` or
   `0.49 0.96`, `--y 0.03 0.53` or `0.50 0.99`) at 2x makes entries legible; one row at 3x
   settles a surname. When scanning *for* a surname, crop only the name columns (`Nomen` +
   `Parentes`, or `Sponsus` + `Sponsa`) of both pages side by side.

Exact dates from court probate files or cemetery cards land you on the right scan first time.

Numbering traps:

- The handwritten page number is not the portal's scan number (cover frames shift it by several
  frames). An index citing "skan 116" may mean either: try both.
- Microfilmed units contain **duplicate frames**. Don't read the year cadence as "one page per
  year" without checking.
- Pencil renumbering next to the ink numbers can shift acts by one.
- **The last frame is the microfilm target card** and states the page and frame count
  (`LICZBA STRON ... · LICZBA KLATEK ...`). Read it before concluding "the book must continue
  somewhere": it settles whether later years are hiding further in.
- **A fond's description generalises; the unit list does not.** A Greek-Catholic parish fond
  advertised "Death book 1851-1945", which reads like the whole parish; the unit's own title
  showed it covered one filial village only. Open the unit list and read each title.

## Reading the registers

Transcribe the **whole row**, not just the names: house number (`Numerus domus`, the era's
address, and what tells two same-named families apart and links a marriage to the children's
births), age, marital state, occupation, cause of death, witnesses, godparents, midwife, and
any later note in the margin.

- 19th-century Latin registers: the `Parentes` block names the father and the mother **with
  her own father** (and often mother), so one act gives two generations. Marriage acts add
  both spouses' parents, ages and `natus in ...`.
- Galician Greek-Catholic birth registers name both sets of grandparents and the mother's
  home village: `Joannes X filius Petri et Annae` / `Maria filia Michaelis Y de Z`.
- The scribe does not always fill the origin column; read the neighbouring rows before
  concluding the register never records it.
- `Aetas` / `Dies vitae` convert straight into a birth year; ages in children's marriage acts
  order a parent's successive marriages.
- Russian-partition acts (Polish or Russian text) give Julian and Gregorian dates; the event
  date and the date the act was written differ.
- Later USC notes (1949-53 in Galicia) beside an entry give a spouse's death date and act
  number: a free bridge to the 20th century.
- An indexer's struck-out first attempt (`Marianna` corrected to `Magdalena`) is a correction,
  not a second person.

Latin worth knowing:

| | |
|---|---|
| `filius / filia leg(itimus)` | legitimate son / daughter of |
| `maritus N.` | husband of (living wife N.) |
| `vidua post N.`, `viduus post N.` | widow / widower of |
| `I° voto ... II° voto ...` | first / second marriage |
| `p.d.` (`pie defunctus`) | the late |
| `orta`, `nata` | née, born |
| `agricola` (`agr.`) | farmer |
| `hortulanus` (`hort.`) | cottager |
| `inquilinus` (`inquil.`) | lodger |
| `mercenarius` (`mercen.`) | labourer |
| `miles reservatis` | army reservist |
| `Testes`, `Patrini`, `Obstetrix` | witnesses, godparents, midwife |
| `e pago X oriundus` | coming from the village X |
