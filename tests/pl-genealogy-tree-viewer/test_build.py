"""Offline tests for pl-genealogy-tree-viewer: build the example, check what the builder derives,
redact with publish.py and build the family book as HTML. Standard library only: the example's scan
pages and photos need Pillow, so the tests build it without them.

Run from the repository root:
    python3 -m unittest discover -s tests/pl-genealogy-tree-viewer
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

TESTS = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.join(os.path.dirname(os.path.dirname(TESTS)), "plugins", "pl-genealogy-record-search",
                     "skills", "pl-genealogy-tree-viewer")
EXAMPLE = os.path.join(SKILL, "templates", "example")
sys.path.insert(0, os.path.join(SKILL, "scripts"))

import build_tree  # noqa: E402
import publish     # noqa: E402

def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


WRAP = """import os, sys
sys.path.insert(0, {ex!r})
from tree_data import *
GEDCOM = os.path.join({ex!r}, "example.ged")
PHOTOS = ""
ACTS = [{{k: v for k, v in a.items() if k not in ("page", "crop", "autocontrast")}} for a in ACTS]
{extra}
"""


class ExampleBuild(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.cfg = cls.config("")
        with redirect_stdout(io.StringIO()):
            cls.r = build_tree.build(cls.cfg, out=os.path.join(cls.tmp, "tree.html"))
        cls.P = cls.r["db"]["people"]
        cls.F = cls.r["db"]["fams"]

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)
        sys.modules.pop("tree_data", None)

    @classmethod
    def config(cls, extra, name="tree_data_test.py"):
        path = os.path.join(cls.tmp, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(WRAP.format(ex=EXAMPLE, extra=extra))
        return path

    def person(self, name, year=None):
        hits = [p for p in self.P.values() if p["n"] == name and (year is None or p["by"] == year)]
        self.assertEqual(len(hits), 1, name)
        return hits[0]

    def test_counts_and_problems(self):
        self.assertEqual(self.r["people"], 35)
        self.assertEqual(self.r["walls"], 14)
        self.assertEqual(sorted(self.r["db"]["lines"]), sorted(
            ["przodkowie Andrzeja Jaworskiego", "przodkowie Teresy Kos", "przodkowie Krzysztofa Lisa", "przodkowie Doroty Dudziak"]))
        # without the scan pages the only problems are the missing scan files
        self.assertTrue(self.r["problems"])
        self.assertTrue(all("no scans/" in p for p in self.r["problems"]), self.r["problems"])
        self.assertIn("Maciej Sowa", self.r["missing_walls"])

    def test_tiers(self):
        self.assertEqual(self.person("Feliks Lis")["t"], "praw")            # TIER: PRAWDOPODOBNE in the note
        self.assertEqual(self.person("Antoni Wrona")["t"], "hip")           # TIER: HIPOTEZA
        self.assertEqual(self.person("Ludwik Kmieć")["t"], "praw")          # TIER_OVERRIDE
        self.assertEqual(self.person("Szymon Jaworski")["t"], "akt")        # named in a transcribed act
        self.assertEqual(self.person("Helena Gołąb")["t"], "")              # a note without a marker is not doubt

    def test_evidence_from_roles(self):
        sz = self.person("Szymon Jaworski")["ev"]
        self.assertEqual(sz["ur"], ["olszyny-u-1890-17"])
        self.assertEqual(len(sz["rd"]), 2)
        mar = self.person("Marianna Sowa")
        self.assertEqual(mar["ev"]["zm"], ["debina-z-1895-21"])
        self.assertIn("olszyny-u-1890-17", mar["ev"]["rd"][self.person("Maciej Sowa")["id"]])   # maternal grandfather named
        anna = self.person("Anna Cisek")
        self.assertNotIn("ev", anna)                                         # godmother: not a family role
        jozef = self.person("Józef Jaworski")
        self.assertEqual(list(jozef["ev"]["sl"].values()), [["olszyny-s-1885-3"]])
        w = self.r["db"]["acts"]["olszyny-u-1890-17"]["w"]
        self.assertIn("urodzenie: Szymon Jaworski", w)

    def test_hypothesis_link_never_backed(self):
        h = self.person("Helena Gołąb")
        self.assertEqual(h.get("hp"), 1)
        self.assertEqual(self.F["@F11@"].get("hp"), 1)
        self.assertNotIn("rd", h.get("ev", {}))

    def test_tables(self):
        self.assertEqual(self.F["@F21@"].get("um"), 1)
        self.assertEqual(self.r["db"]["var"], [["Jaworski", "Jaworzski"]])
        self.assertEqual(self.person("Grzegorz Pająk")["cf"][0]["f"], "rok urodzenia")
        self.assertEqual(len(self.person("Apolonia Kalita")["hy"][0]["v"]), 2)
        x = self.P["@X1@"]
        self.assertEqual(x["n"], "Ignacy Kos")
        self.assertTrue(any(p["t"] == "luka" and p.get("wf") == self.person("Leon Kos")["id"] for p in self.P.values()))

    def test_grandparents_lines(self):
        lnd = self.r["db"]["lnd"]
        stan, helena, andrzej = self.person("Stanisław Jaworski"), self.person("Helena Gołąb"), self.person("Andrzej Jaworski")
        self.assertEqual(lnd[stan["id"]][0], "Stanisław Jaworski")
        self.assertEqual(lnd[stan["id"]][2], 1)                              # a grandparent's line: labelled
        self.assertEqual(lnd[andrzej["id"]][2], 0)                           # the anchor's own side: band only
        self.assertEqual(len([v for v in lnd.values() if v[2]]), 8)          # 4 anchors x father and mother
        self.assertEqual(self.person("Szymon Jaworski")["ln"], stan["id"])   # an ancestor on the father's side
        self.assertEqual(self.person("Franciszek Gołąb")["ln"], helena["id"])
        self.assertEqual(andrzej["ln"], andrzej["id"])                       # in both his parents' blood
        self.assertEqual(self.person("Anna Cisek")["ln"], stan["id"])        # married in: takes the partner's line
        self.assertNotIn("ln", self.person("Tomasz Jaworski"))               # two anchors' lines meet: no band
        self.assertNotIn("ln", self.person("Michał Jaworski"))
        self.assertEqual(self.P["@X1@"]["ln"], self.person("Leon Kos")["id"])  # someone only in tree_data.py
        walls = [p for p in self.P.values() if p["t"] == "luka" and p.get("wf") == self.person("Maciej Sowa")["id"]]
        self.assertEqual(walls[0]["ln"], stan["id"])                         # the wall above follows its person
        hues = {v[1] for v in lnd.values()}
        self.assertEqual(len(hues), 12)                                      # every line its own hue

    def test_grandparents_lines_options(self):
        cfg = self.config('GRANDPARENT_LINES = False', "tree_data_nolines.py")
        with redirect_stdout(io.StringIO()):
            r = build_tree.build(cfg, out=os.path.join(self.tmp, "nolines.html"))
        self.assertEqual(r["db"]["lnd"], {})
        self.assertFalse(any("ln" in p for p in r["db"]["people"].values()))
        cfg = self.config('LINE_HUES = [((1, 2), 3)]', "tree_data_hues.py")
        with redirect_stdout(io.StringIO()):
            r = build_tree.build(cfg, out=os.path.join(self.tmp, "hues.html"))
        stan = next(p for p in r["db"]["people"].values() if p["n"] == "Stanisław Jaworski")
        self.assertEqual(r["db"]["lnd"][stan["id"]][1], 1)
        self.assertEqual({v[1] for v in r["db"]["lnd"].values()}, {1, 2, 3})   # one entry reused for every line

    def test_me_is_the_path_start(self):
        self.assertEqual(self.r["db"]["root"], self.person("Tomasz Jaworski")["id"])
        cfg = self.config('ME = ""', "tree_data_nome.py")
        with redirect_stdout(io.StringIO()):
            r = build_tree.build(cfg, out=os.path.join(self.tmp, "nome.html"))
        self.assertNotIn("root", r["db"])                                    # the viewer falls back on its own
        cfg = self.config('ME = "Nikt Taki|1800"', "tree_data_badme.py")
        with redirect_stdout(io.StringIO()):
            r = build_tree.build(cfg, out=os.path.join(self.tmp, "badme.html"))
        self.assertTrue(any("ME: key" in p for p in r["problems"]))

    def test_conflict_resolved_by_acts_with_change_note(self):
        m = self.person("Maciej Sowa")
        self.assertTrue(m["cf"][0]["s"].startswith("rozstrzygnięta według aktów"))  # shown green on the card
        self.assertEqual(m["cf"][0]["v"][0], ["drzewo rodzinne, przed poprawką", "Gerwazy"])
        self.assertTrue(any(n.startswith("🔁 ZMIANA") and "1885 nr 3" in n for n in m["no"]))
        self.assertEqual(m["t"], "akt")                                      # named in both acts

    def test_page_is_filled(self):
        page = read(self.r["out"])
        for ph in ("__DB__", "__IMG__", "__TITLE__", "__H1__"):
            self.assertNotIn(ph, page)
        self.assertIn("<title>Drzewo rodzinne — przykład</title>", page)

    def test_bad_key_is_reported(self):
        cfg = self.config('TIER_OVERRIDE = {"Nikt Taki|1800": "akt"}', "tree_data_bad.py")
        with redirect_stdout(io.StringIO()):
            r = build_tree.build(cfg, out=os.path.join(self.tmp, "bad.html"))
        self.assertTrue(any("Nikt Taki|1800" in p for p in r["problems"]))

    def test_publish_living(self):
        out = os.path.join(self.tmp, "pub")
        with redirect_stdout(io.StringIO()):
            res = publish.publish(self.r["out"], out, living=1926)
        page = read(os.path.join(out, "index.html"))
        self.assertIn('content="noindex,nofollow"', page)
        _, _, _, db, img = publish.split_page(page)
        tomasz = db["people"]["@I1@"]
        self.assertEqual(tomasz["n"], "Osoba żyjąca Jaworski")
        self.assertEqual(tomasz["by"], "")
        self.assertIn("@I1@", res["redacted"])
        self.assertNotIn("@I20@", res["redacted"])               # died 1990
        self.assertEqual(db["people"]["@I20@"]["n"], "Stanisław Jaworski")
        # a living anchor's name also labels a line: it goes too
        self.assertIn("@I10@", res["redacted"])
        self.assertEqual(db["lnd"]["@I10@"][0], "Osoba żyjąca Jaworski")
        self.assertEqual(db["lnd"]["@I20@"][0], "Stanisław Jaworski")
        self.assertNotIn("Andrzej Jaworski", page)
        self.assertIn("przodkowie Andrzeja Jaworskiego", res["line_labels"])   # your label: reported, not rewritten

    def test_publish_leaves_photos_alone(self):
        page = read(self.r["out"])
        lines = page.split("\n")
        i = next(k for k, l in enumerate(lines) if l.startswith("const IMG = "))
        uri = "data:image/jpeg;base64,AAAA+61041512345/BBBB"           # 11 digits inside base64 are not a number
        lines[i] = 'const IMG = {"t":{"@I20@":"%s"},"b":{}};' % uri
        src = os.path.join(self.tmp, "with-photo.html")
        with open(src, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        with redirect_stdout(io.StringIO()):
            res = publish.publish(src, os.path.join(self.tmp, "pub3"))
        self.assertEqual(res["masked"], 0)
        self.assertIn(uri, read(os.path.join(self.tmp, "pub3", "index.html")))

    def test_template_has_no_eleven_digit_number(self):
        tpl = read(os.path.join(SKILL, "templates", "viewer", "tree.html"))
        self.assertIsNone(publish.PESEL.search(tpl))             # masking must never touch the viewer's code

    def test_publish_masks_eleven_digits(self):
        page = read(self.r["out"]).replace("nauczyciel", "nauczyciel 61041512345")
        src = os.path.join(self.tmp, "with-number.html")
        with open(src, "w", encoding="utf-8") as f:
            f.write(page)
        with redirect_stdout(io.StringIO()):
            res = publish.publish(src, os.path.join(self.tmp, "pub2"))
        self.assertEqual(res["masked"], 1)
        self.assertNotIn("61041512345", read(os.path.join(self.tmp, "pub2", "index.html")))

    def test_book_html(self):
        out = os.path.join(self.tmp, "book.html")
        r = subprocess.run([sys.executable, os.path.join(SKILL, "scripts", "build_book.py"), self.r["out"],
                            "--no-pdf", "--out", out], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        book = read(out)
        self.assertEqual(book.count('<h2 id="r'), 4)
        self.assertIn('id="d3"', book)
        self.assertIn("Indeks osób", book)
        self.assertEqual(book.count('<svg class="fan"'), 4)          # one per chapter

    def book(self, *args, name="book.html"):
        out = os.path.join(self.tmp, name)
        r = subprocess.run([sys.executable, os.path.join(SKILL, "scripts", "build_book.py"), self.r["out"],
                            "--no-pdf", "--out", out, *args], capture_output=True, text=True)
        if "--print" in args: out = out[:-5] + "-druk.html"
        return r, (read(out) if r.returncode == 0 else "")

    def ancestors(self, pid):
        """Known direct ancestors, parents taken from the first family with parents (as par() does)."""
        seen, q = set(), [pid]
        while q:
            x = q.pop()
            for fid in self.P[x]["fc"]:
                f = self.F.get(fid) or {}
                if f.get("h") or f.get("w"):
                    for y in (f.get("h"), f.get("w")):
                        if y and self.P[y]["t"] != "luka" and y not in seen:
                            seen.add(y); q.append(y)
                    break
        return seen

    def test_book_of_some_lines_for_a_reader(self):
        r, book = self.book("--lines", "Krzysztofa Lisa,Doroty Dudziak", "--reader", "Lisa,Dudziak=Marty",
                            "--title", "Księga Marty")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(book.count('<h2 id="r'), 2)
        self.assertIn("<title>Księga Marty</title>", book)
        self.assertIn("Osoba, od której liczy się rozdział — ojciec Marty", book)
        self.assertIn("Rodzice · dla Marty: dziadkowie", book)
        self.assertNotIn('class="doc"', book)                        # no act names anyone in these lines
        self.assertNotIn("Jaworski", book.split('id="idx"')[1])     # the index holds only their people

    def test_book_acts_under_the_entries(self):
        r, book = self.book()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn('id="dok"', book)                           # every act names someone in the chapters
        docs = book.split('<div class="doc" id="d')[1:]
        self.assertEqual([d.split('"')[0] for d in docs], ["1", "2", "3"])   # numbered in book order
        # the birth act right under the child, the marriage and the death after the wife's entry, by year
        self.assertIn("urodzeń 1890", docs[0].split("</h4>")[0])
        self.assertIn("ślubów 1885", docs[1].split("</h4>")[0])
        self.assertIn("zgonów 1895", docs[2].split("</h4>")[0])
        szymon = self.person("Szymon Jaworski", "1890")["id"]
        marianna = self.person("Marianna Sowa", "1862")["id"]
        for who, d in ((szymon, "d1"), (marianna, "d2")):
            n = book.split(f'id="{d}"')[0].rsplit('<section class="os" id="', 1)[1]
            self.assertIn(self.P[who]["n"], n.split("</h4>")[0])
            self.assertTrue(n.split("</section>")[1].lstrip().startswith('<div class="pod">'), d)
        self.assertIn("under entries 3, at the end 0", r.stdout)

    def test_candidate_role_raises_no_tier(self):
        act = ('ACTS.append(dict(id="x-u-1955-1", title="Wola, księga urodzeń 1955, akt 1", date="1955", ref="sygn. 1", '
               'source="", text="", translation="", people={{"@I10@": "dziecko — {role}"}}))')
        for role, tier in (("KANDYDAT (czy to on?)", ""), ("to jego akt", "akt")):
            cfg = self.config(act.format(role=role), name=f"tree_data_cand_{tier or 'none'}.py")
            out = os.path.join(self.tmp, f"cand_{tier or 'none'}.html")
            with redirect_stdout(io.StringIO()):
                res = build_tree.build(cfg, out=out)
            sys.modules.pop("tree_data", None)
            self.assertEqual(res["db"]["people"]["@I10@"]["t"], tier, role)
        r = subprocess.run([sys.executable, os.path.join(SKILL, "scripts", "build_book.py"), os.path.join(self.tmp, "cand_none.html"),
                            "--no-pdf", "--out", os.path.join(self.tmp, "cand_book.html")], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        doc = read(os.path.join(self.tmp, "cand_book.html")).split("Wola, księga urodzeń 1955")[1].split("<pre>")[0]
        self.assertIn('class="t hip">hipoteza', doc)
        self.assertIn("Akt kandydata", doc)

    def test_about_is_on_the_start_screen(self):
        page = read(self.r["out"])
        self.assertIn('<div class="habout" id="habout">${aboutHtml()}</div>', page)
        self.assertNotIn('data-hact="about"', page)
        self.assertIn('e.target.closest("#homescr,#grid")', page)     # the wheel scrolls the start screen

    # ---------------------------------------------------------- 1.5.0: made by, atlas, posters, undated deaths
    def test_page_says_made_by_applied_ai(self):
        page = read(self.r["out"])
        foot = page.split('<footer id="madeby">')[1].split("</footer>")[0]
        self.assertIn("Made by", foot)
        self.assertIn('href="https://appliedai.dev"', foot)
        self.assertEqual(foot.count('src="data:image/png;base64,'), 2)    # wordmark for light and dark
        self.assertIn('<meta name="generator" content="pl-genealogy-tree-viewer · Made by Applied AI', page)
        self.assertIn("https://github.com/plrojek/agent-skills", self.r["db"]["meta"]["generator"])
        self.assertNotIn("__BRAND_", page)

    def test_atlas_inline_and_optional(self):
        page = read(self.r["out"])
        self.assertIn('<script id="tree3d-bundle">', page)
        self.assertIn('<style id="tree3d-style">', page)
        self.assertIn('id="atlasbtn"', page)
        self.assertLess(page.index('<script id="tree3d-bundle">'), page.index("const DB = "))
        out = os.path.join(self.tmp, "no-atlas.html")
        with redirect_stdout(io.StringIO()):
            build_tree.build(self.cfg, out=out, atlas=False)
        bare = read(out)
        self.assertNotIn("tree3d-bundle", bare)
        self.assertIn('<footer id="madeby">', bare)

    def test_own_template_still_gets_the_footer(self):
        tpl = read(os.path.join(SKILL, "templates", "viewer", "tree.html"))
        tpl = tpl.split('<footer id="madeby">')[0] + tpl.split("</footer>", 1)[1]
        tpl = tpl.replace('<meta name="generator"', '<meta name="x-removed"')
        path = os.path.join(self.tmp, "own-template.html")
        with open(path, "w", encoding="utf-8") as f:
            f.write(tpl)
        out = os.path.join(self.tmp, "own.html")
        with redirect_stdout(io.StringIO()):
            build_tree.build(self.cfg, template=path, out=out)
        page = read(out)
        self.assertEqual(page.count('<footer id="madeby">'), 1)
        self.assertIn('<meta name="generator"', page)

    def test_publish_writes_posters_from_published_data(self):
        pub = os.path.join(self.tmp, "pub-posters")
        with redirect_stdout(io.StringIO()):
            res = publish.publish(self.r["out"], pub, living=1926)
        idx = read(os.path.join(pub, "index.html"))
        self.assertIn('id="poster-link" href="poster/" class', idx)            # the link is no longer hidden
        poster = read(os.path.join(pub, "poster", "index.html"))
        self.assertIn('<meta name="poster-root" content="%s">' % self.r["db"]["root"], poster)
        self.assertIn('<footer class="madeby" id="madeby">Made by', poster)
        for f in ("editor.js", "poster.js", "style.css", "assets/background1.jpg", "brand/applied-ai-wordmark-light.png"):
            self.assertTrue(os.path.exists(os.path.join(pub, "poster", f)), f)
        with open(os.path.join(pub, "poster", "people.json"), encoding="utf-8") as f:
            people = json.load(f)
        self.assertEqual(res["posters"], len(people))
        tomasz = self.person("Tomasz Jaworski", "1985")["id"]
        self.assertTrue(people[tomasz]["name"].startswith("Osoba żyjąca"))   # redacted in the posters too
        self.assertEqual(people[tomasz]["born"], "")
        bare = os.path.join(self.tmp, "pub-no-posters")
        with redirect_stdout(io.StringIO()):
            publish.publish(self.r["out"], bare, posters=False)
        self.assertFalse(os.path.exists(os.path.join(bare, "poster")))
        self.assertIn('id="poster-link" href="poster/" hidden', read(os.path.join(bare, "index.html")))

    def test_publish_masks_only_the_data(self):
        page = read(self.r["out"])
        bundle = page.split('<script id="tree3d-bundle">')[1].split("</script>")[0]
        self.assertIsNotNone(publish.PESEL.search(bundle))     # the atlas code holds digit runs that are not numbers
        pub = os.path.join(self.tmp, "pub-code")
        with redirect_stdout(io.StringIO()):
            res = publish.publish(self.r["out"], pub, posters=False)
        self.assertEqual(res["masked"], 0)
        self.assertIn(bundle, read(os.path.join(pub, "index.html")))

    def test_book_last_page_says_made_by(self):
        r, book = self.book()
        self.assertEqual(r.returncode, 0, r.stderr)
        tail = book.split('id="idx"')[1]
        self.assertIn('<div class="madeby">Made by <a href="https://appliedai.dev"><img src="data:image/png;base64,', tail)
        self.assertTrue(book.rstrip().endswith("</div>\n</body></html>") or book.rstrip().endswith("</body></html>"))
        self.assertIn('<meta name="generator" content="pl-genealogy-tree-viewer · Made by Applied AI', book)

    def test_undated_death_is_a_death(self):
        ged = read(os.path.join(EXAMPLE, "example.ged"))
        self.assertIn("0 @I10@ INDI", ged)
        ged = ged.replace("0 @I10@ INDI\n", "0 @I10@ INDI\n1 DEAT Y\n", 1)
        path = os.path.join(self.tmp, "undated-death.ged")
        with open(path, "w", encoding="utf-8") as f:
            f.write(ged)
        cfg = self.config(f"GEDCOM = {path!r}", name="tree_data_undated.py")
        out = os.path.join(self.tmp, "undated.html")
        with redirect_stdout(io.StringIO()):
            res = build_tree.build(cfg, out=out)
        sys.modules.pop("tree_data", None)
        P = res["db"]["people"]
        self.assertEqual(P["@I10@"]["dd"], "data nieznana")
        self.assertEqual(self.P["@I10@"]["dd"], "")                             # without DEAT: nothing
        self.assertNotIn("@I10@", publish.presumed_living(P, res["db"]["fams"], 1926))

    def test_book_unknown_line_refused(self):
        r, _ = self.book("--lines", "Nikogo")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("no line label contains", r.stderr)

    def test_book_fan_holds_every_known_ancestor(self):
        tomasz = self.person("Tomasz Jaworski", "1985")["id"]
        anc = self.ancestors(tomasz)
        r, book = self.book("--fan", "Tomasz Jaworski|1985=Tomasz")
        self.assertEqual(r.returncode, 0, r.stderr)
        front = book.split('<svg class="fan"')[1].split("</svg>")[0]
        for pid in anc:
            given = self.P[pid]["n"].split()[0]
            self.assertIn(">" + given, front, self.P[pid]["n"])
        self.assertIn(f"Wszyscy znani przodkowie w linii prostej: {len(anc)} osób", book)
        self.assertIn("Przerywana ramka", book)                      # Helena Gołąb's parents are a hypothesis

    def test_book_fan_finds_the_common_descendant(self):
        # four lines: Tomasz's parents and Marta's; the fan's centre is one of their children
        tomasz = self.person("Tomasz Jaworski", "1985")["id"]
        marta = self.person("Marta Lis")["id"]
        n = len(self.ancestors(tomasz) | self.ancestors(marta)) + 2
        r, book = self.book("--fan", "Jan i Michał")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Wachlarz przodków — Jan i Michał", book)
        self.assertIn(f"Wszyscy znani przodkowie w linii prostej: {n} osób", book)

    def test_book_print_edition_page_numbers(self):
        pages = os.path.join(self.tmp, "pages.json")
        with open(pages, "w", encoding="utf-8") as f:
            json.dump({"r1": 4, "r2": 7, "dok": 13, "idx": 15, "r2-1": 7}, f)
        r, book = self.book("--print", "--fan", "Tomasz", "--pages", pages, name="print.html")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("@page fan", book)
        self.assertIn('<div class="fanpage">', book)
        self.assertIn('<span class="tp">4</span>', book)
        self.assertIn('<span class="tp">15</span>', book)
        self.assertIn("§1 r.2, s. 7", book)                  # Teresa, Andrzej's wife, has her entry in chapter 2


if __name__ == "__main__":
    unittest.main()
