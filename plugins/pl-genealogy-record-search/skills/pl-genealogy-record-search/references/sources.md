# Sources, endpoints and archives

Checked October 2026. Sites change their markup; if a script returns nothing for a query
that should have hits, open the page in a browser before trusting the zero.

## Geneteka (geneteka.genealodzy.pl)

Parish indexes compiled by PTG volunteers. Index years grow every month: re-run
`geneteka.py parishes <woj>` before a big search.

Province codes: `01ds` dolnośląskie · `02kp` kujawsko-pomorskie · `03lb` lubelskie ·
`04ls` lubuskie · `05ld` łódzkie · `06mp` małopolskie · `07mz` mazowieckie · `71wa` Warszawa ·
`08op` opolskie · `09pk` podkarpackie · `10pl` podlaskie · `11pm` pomorskie · `12sl` śląskie ·
`13sk` świętokrzyskie · `14wm` warmińsko-mazurskie · `15wp` wielkopolskie ·
`16zp` zachodniopomorskie · `21uk` Ukraine · `22br` Belarus · `23lt` Lithuania · `25po` other

| | |
|---|---|
| parish list | `index.php?op=gt&lang=pol&bdm=B&w=<woj>&rid=B`: `<option data-b data-s data-d data-years>` |
| search | `api/getAct.php?op=gt&lang=pol&bdm=<B/S/D>&w=<woj>&rid=<rid or letter>&search_lastname=&search_name=&from_date=&to_date=&start=&length=50&exac=1` |
| real answer | `recordsTotal` plausible, `parishes` names the parish asked for |
| pooled answer | `recordsTotal` in the tens of thousands, `parishes` empty, surname in no row |
| surname counts | `geneszukacz.genealodzy.pl?op=se` (counts only, no records) |

Columns: births and deaths `year, act, given, surname, father, mother, mother's surname,
parish, village, remarks`; marriages `year, act, groom, surname, groom's parents, bride,
surname, bride's parents, parish, remarks`.

## Indeks Represjonowanych (indeksrepresjonowanych.pl)

- Search: `/wyniki?search[<field>]=...&search[limit]=100&search[start]=<page>` (pages from 1).
- Fields: `last_name`, `name`, `father_first_name`, `mother_first_name`, `birth`,
  `birth_place`, `city`, `county`, `voivodeship`, `fate`, `repression_place`,
  `old_county` (district in the USSR), `old_voivodeship` (oblast), `old_country`.
- Every field has `exact_<field>=1`, which means **contains the text**. Without it the match
  is strict: a village search returns nothing for records that say "Village near Town".
- Cards: `/szczegoly/<uuid>`, fates in order (deportation, exile, army, return, death) and
  the source signature.

**Archiwum IPN** (originals of the questionnaires): ul. Janusza Kurtyki 1, 02-676 Warszawa,
tel. +48 22 581 89 04, `archiwumipn@ipn.gov.pl` (from abroad `archives@ipn.gov.pl`); forms at
`archiwum.ipn.gov.pl/pl/wnioski-i-formularze`. Give the fond signature (`IPN BU ...`) and
the questionnaire number (`IR/...`).

## Military: Anders' Army and the Polish forces in the West

No complete public index of the 2nd Corps exists.

| Collection | Coverage | Note |
|---|---|---|
| Kresy-Siberia, 2nd Corps index (`kresy-siberia.org`) | ~32 000 names | about a quarter; absence proves nothing |
| Lista Krzystka (`listakrzystka.pl`) | Polish Air Force in Britain 1940-47 | air force only |
| WBH-CAW, Warsaw | personnel cards, mostly **with a photo** | the best first move, and it is in Poland |
| Sikorski Institute, London | main personnel files of the 2nd Corps | paid queries |
| The National Archives, Kew | `WO 315`, Polish Resettlement Corps | |
| UdSKiOR | veterans' files | feeds the Indeks Represjonowanych |

## Resettled from the Kresy (not deported)

A family that left the Kresy in 1944-46 will not be in the Indeks Represjonowanych. Look
for **PUR** (Państwowy Urząd Repatriacyjny) registration cards in the regional state archive
of where they settled.

## Cemeteries

**Przemyśl municipal** (`cmentarzeprzemysl.pl`), script `cmentarze_przemysl.py`:

| | |
|---|---|
| list (paged) | `pages/find2.php?nazwisko=&imie=&data_ur=&data_zg=&rok_od=&rok_do=&search=Szukaj&page=N&c=` |
| grave card | `pages/mapa.php?c=<1-5>&id=<id>`: birth date, death date, section/row/grave, fee paid until |

Cemetery codes: `1` Główny · `2` Zasanie · `3` Wojskowy · `4` Przekopana · `5` Kruhel Mały.
Without `search=Szukaj` the filter is ignored. `nazwisko` is matched as `LIKE '<input>%'`.
The TLS certificate is issued for another host name.

**Grobonet** (`<name>.grobonet.com`), script `grobonet.py`:

| | |
|---|---|
| search | `/wyszukiwarka/wyniki?nazwisko=&imie=&ppstrona=N` (12 per page) |
| person | `/osoba/<id>`; `/osoba/<id>?inni=1` = everyone in the grave |
| all instances | `polskie-cmentarze.com` (national search) and `grobonet.com` |

Others, no script: `mogily.pl`, `polskie-cmentarze.pl`, `ecmentarze.pl`.

## Other script-friendly sources

| Source | What it gives |
|---|---|
| `skanoteka.genealodzy.pl` | whole state-archive fonds of parish books, free (`skanoteka.py`) |
| `metryki.genealodzy.pl` | PTG scans, strong for Mazowsze (`skanoteka.py --site metryki`) |
| `caak.upjp2.edu.pl` | Kraków archdiocese books, IIIF (`caak.py`) |
| `jri-poland.org` | Jewish vital records; the route for a mixed-marriage lead |

## Need a real browser or an account

| Source | Why | Worth it for |
|---|---|---|
| `szukajwarchiwach.gov.pl` | bot protection (Imperva); a real browser passes | scans of parish and civil books, PUR files, court files, every AP inventory |
| Gesher Galicia | JavaScript app; some content for members | Galician records incl. Jewish, record inventories, cadastral maps (see below) |
| `genealogyindexer.org` | search needs a session | city directories, yizkor books, school yearbooks: an ancestor at an address |
| FamilySearch | login | indexes, the film catalog, emigrant documents (see below) |
| `genbaza.pl` | login | more scans |

Use these through a browser session the user can see (Claude in Chrome or a DevTools MCP),
at a human pace. Don't move their cookies into scripts or disguise a script as a browser.
Don't conclude "not online" before these have been tried: between them they hold the scans,
the Jewish records and the address directories no index reproduces.

## FamilySearch (familysearch.org)

Needs the user's login; use their browser session and only read. Never save, edit or
attach anything to their FamilySearch tree. Checked October 2026.

**Record search**: `/search/record/results?q.surname=&q.givenName=&q.anyPlace=&q.birthLikeDate.from=&q.birthLikeDate.to=&f.collectionId=&count=20`
- Places match loosely by default: "Przemyśl" returned births in other towns of the same
  province. Add `q.anyPlace.exact=on` (and `q.surname.exact=on`).
- Even an exact place matches at **any level of FamilySearch's place hierarchy**, which uses
  historical districts: a village filed under an old district comes up for that district's
  town. Read the event place on every row.
- Main Polish collections: `Poland, Church Books, 1568-1990` (`f.collectionId=4135958`) and
  `Poland, Tarnow, Roman Catholic Diocese Church Books, 1612-1900` (`1985025`).
- The Polish index is **thin** next to Geneteka (a handful of rows where Geneteka has
  hundreds). Use it to cross-check and for parishes Geneteka doesn't cover. A record's
  "Residence Place" is often just the house number.
- A record page has no direct scan, only "Check Image Availability", which leads to the catalog.

**Catalog**: `/search/catalog/results?q.place=<village>`, grouped by subject (church records,
Jewish records, Ukrainian `Метричні книги`). An entry (`/search/catalog/<id>`) gives the years
and record types per film, the film number and image group number (DGS), and **which archive
the books were filmed in**: a quick way to learn where a parish's books physically are.
- Many Polish church-book films are marked "viewable with additional restrictions": the
  images open **only at a FamilySearch Center or affiliate library**, not at home. Check
  the icon or its tooltip in the Film/Digital Notes table before promising the user a scan.
- Each film row has "Search the Index", which limits the record search to that film.

**Full-text search**: `/search/full-text/results?q.text=<words>` searches machine-read text
of documents. For Polish names it mostly finds **emigrants**: Polish-American newspapers,
US naturalization papers, passenger lists. The text has no Polish letters (`Przemysl`), so
type names without diacritics. Use it for relatives who left; it does not search parish books.

## Gesher Galicia (geshergalicia.org)

Galician records, strongest for Jewish families but not only them. Some content is for
members. Checked October 2026.

- **All Galicia Database**: `www.geshergalicia.org/all-galicia-database/`. A JavaScript app
  that loads its data from `search.geshergalicia.org`; scripts get only "Loading...".
  On 26 October 2026 that data server did not answer at all, so searches were not tested.
  If it doesn't load, say so and move on rather than retrying.
- **Record Inventories** (`/inventory/`): which records survive for a town and in which
  archive (AGAD, the Przemyśl state archive, Ukrainian archives). Read it before writing to
  an archive. Also a JavaScript search form.
- **Map Room** (`maps.geshergalicia.org`): cadastral and town maps. Cadastral maps carry
  house and plot numbers, which link to the `Numerus domus` column of parish registers.
- **Knowledge base**: guides to AGAD's Jewish Galician records, the Przemyśl State Archive
  and Ukrainian archives, and a town locator for old district names.

## Archives: where the books are

- **AP** (state archives) signatures look like `56/1639/0/-/8` (archive/fond/series/unit).
- **Diocesan archives** use plain volume numbers (`21/T. 10`).
- **AGAD fond 301**: Kresy parish books before ~1900. **CDIAL Lviv fond 618**: Eastern Galicia.
- **USC Warszawa-Śródmieście**: Kresy books after ~1900 (*księgi zabużańskie*).
- Civil registry offices (USC) keep recent books until they are old enough to pass to the
  state archive; ask the USC of the place for anything more recent than the AP holds.

## Wikipedia as a source

Before quoting a sentence, check its citation and its author:
`<lang>.wikipedia.org/w/index.php?title=<Article>&action=raw` and
`.../w/api.php?action=query&prop=revisions&titles=<Article>&rvlimit=30&rvprop=ids|timestamp|user|content&rvslots=main&format=json`.
