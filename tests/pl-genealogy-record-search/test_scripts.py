"""Offline tests for pl-genealogy-record-search. No network: the source scripts are tested
on their parsing and sanity logic only.

Run from the repository root:
    python3 -m unittest discover -s tests/pl-genealogy-record-search
"""
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

TESTS = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(os.path.dirname(os.path.dirname(TESTS)), "plugins", "pl-genealogy-record-search",
                       "skills", "pl-genealogy-record-search", "scripts")
sys.path.insert(0, SCRIPTS)
os.environ["GENEALOGY_CACHE_DIR"] = tempfile.mkdtemp(prefix="genealogy-test-cache-")

import audit_tree      # noqa: E402
import crossmatch      # noqa: E402
import geneteka        # noqa: E402
import grobonet        # noqa: E402
import inventory       # noqa: E402
import parse_ged       # noqa: E402
import sweep_all       # noqa: E402
import validate_ged    # noqa: E402

FIXTURE = os.path.join(TESTS, "fixture.ged")


class GedcomTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.tree = parse_ged.parse(FIXTURE)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def variant(self, edit):
        with open(FIXTURE, encoding="utf-8") as f:
            text = f.read()
        path = os.path.join(self.tmp, "t.ged")
        with open(path, "w", encoding="utf-8") as f:
            f.write(edit(text))
        return path

    def test_parse(self):
        P, F = self.tree["people"], self.tree["fams"]
        self.assertEqual(len(P), 5)
        self.assertEqual(len(F), 2)
        self.assertEqual(P["@I2@"]["surn"], "Kowal")          # taken from /Kowal/
        self.assertEqual(P["@I2@"]["givn"], "Piotr")
        self.assertEqual(P["@I4@"]["marnm"], "Kowal")
        self.assertEqual(P["@I5@"]["notes"], ["First line of a note\nsecond line continued"])
        self.assertEqual(F["@F2@"]["marr"], ["1925", "Wola Zielona"])

    def test_parse_cp1250(self):
        path = os.path.join(self.tmp, "cp.ged")
        with open(path, "wb") as f:
            f.write("0 @I1@ INDI\n1 NAME Józef /Łęcki/\n0 TRLR\n".encode("cp1250"))
        self.assertEqual(parse_ged.parse(path)["people"]["@I1@"]["surn"], "Łęcki")

    def test_validate_ok(self):
        self.assertEqual(validate_ged.check(FIXTURE)[2:], ([], [], []))

    def test_validate_record_after_trailer(self):
        path = self.variant(lambda t: t + "0 @I9@ INDI\n1 NAME Late /Added/\n")
        err = validate_ged.check(path)[2]
        self.assertTrue(any("TRLR" in e and "follow" in e for e in err), err)

    def test_validate_missing_trailer(self):
        path = self.variant(lambda t: t.replace("0 TRLR\n", ""))
        self.assertIn("no 0 TRLR record", validate_ged.check(path)[2])

    def test_validate_one_way_link(self):
        path = self.variant(lambda t: t.replace("1 CHIL @I5@\n", ""))
        err = validate_ged.check(path)[2]
        self.assertTrue(any("@I5@" in e and "CHIL" in e for e in err), err)

    def test_validate_duplicate_xref(self):
        path = self.variant(lambda t: t.replace("0 TRLR", "0 @I1@ INDI\n1 NAME X /Y/\n0 TRLR"))
        self.assertEqual(validate_ged.check(path)[3], ["@I1@"])

    def test_audit(self):
        found = audit_tree.audit(self.tree)
        self.assertTrue(any("after the mother's death" in x for x in found), found)

    def test_inventory(self):
        walls, holes, freq = inventory.inventory(self.tree, root="@I1@")
        self.assertEqual({w[1] for w in walls}, {"@I2@", "@I3@"})
        reasons = {(i, r) for i, r in holes}
        self.assertIn(("@I5@", "no given name"), reasons)
        self.assertTrue(any(i == "@I3@" and "husband" in r for i, r in holes))
        self.assertEqual(freq[("Kowal", "Wola Zielona")], 2)

    def test_crossmatch_marriage_matches_both_spouses(self):
        index = os.path.join(self.tmp, "s.json")
        row = ["1925", "12", "Jan", "Kowal", "Piotr, Anna", "Maria", "Lis", "Józef, Ewa",
               "Wola Zielona", "~ 12.05.1925"]
        with open(index, "w", encoding="utf-8") as f:
            json.dump({"bdm": "S", "rows": [row]}, f)
        res = crossmatch.crossmatch(self.tree, crossmatch.load_index([index]), years=40)
        self.assertEqual({r[0] for r in res}, {"@I1@", "@I4@"})

    def test_crossmatch_year_window(self):
        index = os.path.join(self.tmp, "b.json")
        with open(index, "w", encoding="utf-8") as f:
            json.dump({"bdm": "B", "rows": [["1801", "1", "Jan", "Kowal", "", "", "", "", "", ""]]}, f)
        self.assertEqual(crossmatch.crossmatch(self.tree, crossmatch.load_index([index]), years=10), [])


class GenetekaTest(unittest.TestCase):
    REAL = {"recordsTotal": 4, "parishes": {"13sk": [[7602, "Kielce Katedra", "0.0", "x"]]},
            "data": [["1901", "371", " Michalina", "Nowak ", "n", "Anna", "Nowakowski",
                      "Kielce Katedra", "", ""]]}

    def test_real_answer_passes(self):
        self.assertEqual(geneteka.sanity_reasons(self.REAL, "Nowak", "7602"), [])

    def test_pooled_answer_is_rejected(self):
        pooled = {"recordsTotal": 31544, "parishes": [],
                  "data": [["1850", "3", "Jan", "Wiśniewski", "", "", "", "Karniewo", "", ""]]}
        reasons = geneteka.sanity_reasons(pooled, "Nowak", "7602")
        self.assertEqual(len(reasons), 3, reasons)

    def test_wrong_parish_is_rejected(self):
        other = dict(self.REAL, parishes={"07mz": [[176, "Somewhere", "0", "x"]]})
        self.assertTrue(geneteka.sanity_reasons(other, "Nowak", "7602"))

    def test_diacritics_and_l_stroke(self):
        d = dict(self.REAL, data=[["1900", "1", "Jan", "Michałek", "", "", "", "", "", ""]])
        self.assertEqual(geneteka.sanity_reasons(d, "Michalek", "7602"), [])

    def test_strip_reads_remarks_from_tooltips(self):
        cell = ('<img title="Indeks dodał: someone"><span title="mąż Jan&#013;12.05.1925"></span>'
                '<a href="fix.php?gid=1"><img title="Zgłoś poprawkę"></a>')
        self.assertEqual(geneteka.strip(cell), "mąż Jan 12.05.1925")

    def test_links_keep_scans_drop_profiles(self):
        raw = ['<a href="http://www.kielce.ap.gov.pl"><img></a>'
               '<a href="https://www.genealodzy.pl/user.php?op=userinfo&amp;uname=x"></a>'
               '<a class="gt" target="doc" href="https://metryki.genealodzy.pl/id1-sy1911-kt2">s</a>'
               '<a href="fix.php?gid=1"></a>']
        self.assertEqual(geneteka.links(raw), ["https://metryki.genealodzy.pl/id1-sy1911-kt2"])


class OtherSourcesTest(unittest.TestCase):
    def test_grobonet_list_item(self):
        h = ('<ul class="results_list"><li><a href="https://x.grobonet.com/osoba/1149">'
             '<span class="sp">śp. <span>Jan Nowak</span></span><br>'
             '<span class="szary">ur. 1937-03-25</span><br><span class="szary">zm. 2003-02-03</span><br>'
             '<p><span class="szary">Cmentarz Parafialny</span></p><p class="gn-list-location">'
             '<span><strong>Sektor:</strong> F</span><span><strong>Rząd:</strong> 1</span>'
             '<span><strong>Nr grobu:</strong> 24</span></p></a></li></ul>')
        self.assertEqual(grobonet._items(h), [{
            "id": "1149", "name": "Jan Nowak", "born": "1937-03-25", "died": "2003-02-03",
            "cemetery": "Cmentarz Parafialny", "sector": "F", "row": "1", "grave": "24"}])

    def test_female_variants(self):
        self.assertEqual(sweep_all.variants("Zawadzki"), ["Zawadzki", "Zawadzka"])
        self.assertEqual(sweep_all.variants("Wilecka"), ["Wilecka", "Wilecki"])
        self.assertEqual(sweep_all.variants("Nowak"), ["Nowak"])

    def test_sweep_needs_a_source(self):
        with self.assertRaises(SystemExit), redirect_stdout(io.StringIO()):
            with open(os.devnull, "w") as null:
                old, sys.stderr = sys.stderr, null
                try:
                    sweep_all.main(["Nowak"])
                finally:
                    sys.stderr = old


if __name__ == "__main__":
    unittest.main()
