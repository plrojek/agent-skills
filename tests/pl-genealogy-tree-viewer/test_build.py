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


if __name__ == "__main__":
    unittest.main()
