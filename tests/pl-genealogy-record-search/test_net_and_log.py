"""Offline tests for the robots.txt delays (_net.py) and the research log (search_log.py).
No network: robots.txt answers and clocks are faked.

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
from contextlib import redirect_stderr

TESTS = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(os.path.dirname(os.path.dirname(TESTS)), "plugins", "pl-genealogy-record-search",
                       "skills", "pl-genealogy-record-search", "scripts")
sys.path.insert(0, SCRIPTS)
os.environ.setdefault("GENEALOGY_CACHE_DIR", tempfile.mkdtemp(prefix="genealogy-test-cache-"))
os.environ["GENEALOGY_LOG"] = os.path.join(tempfile.mkdtemp(prefix="genealogy-test-log-"), "searches.jsonl")

import _net        # noqa: E402
import geneteka    # noqa: E402
import search_log  # noqa: E402

GENETEKA = "https://geneteka.genealodzy.pl/api/getAct.php?op=gt&w=09pk"
ROBOTS_PTG = "User-agent: *\nDisallow: \nCrawl-delay: 120\nDisallow: /cgi-bin/\n"


class RobotsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.old = (_net.CACHE_DIR, _net.DELAY, _net._robots_record)
        _net.CACHE_DIR = self.tmp
        _net._robots.clear()
        _net._next_slot.clear()

    def tearDown(self):
        _net.CACHE_DIR, _net.DELAY, _net._robots_record = self.old
        _net._robots.clear()
        _net._next_slot.clear()
        shutil.rmtree(self.tmp)

    def fake(self, status, text=""):
        _net._robots_record = lambda host, scheme, verify: {"status": status, "text": text, "t": 0}

    def test_crawl_delay_is_the_wait(self):
        self.fake(200, ROBOTS_PTG)
        self.assertEqual(_net.delay_for(GENETEKA), 120.0)

    def test_env_delay_is_a_floor_not_a_ceiling(self):
        self.fake(200, ROBOTS_PTG)
        _net.DELAY = 200.0
        self.assertEqual(_net.delay_for(GENETEKA), 200.0)
        _net._robots.clear()
        self.fake(200, "User-agent: *\nDisallow:\n")
        _net.DELAY = 1.0
        self.assertEqual(_net.delay_for("https://example.org/x"), 1.0)

    def test_disallowed_path_is_not_requested(self):
        self.fake(200, ROBOTS_PTG)
        with self.assertRaises(_net.Refused):
            _net._wait_turn("https://geneteka.genealodzy.pl/cgi-bin/x")

    def test_forbidden_robots_means_no_automation(self):
        self.fake(403)
        with self.assertRaises(_net.Refused):
            _net._wait_turn("https://example.org/page")

    def test_missing_robots_has_no_rules(self):
        self.fake(404)
        self.assertEqual(_net.delay_for("https://example.org/page"), _net.DELAY)

    def test_unreadable_robots_falls_back_to_known_delay(self):
        self.fake(503)
        self.assertEqual(_net.delay_for(GENETEKA), 120.0)
        _net._robots.clear()
        self.assertEqual(_net.delay_for("https://metbox1.genealodzy.pl/metryka_get.php"), _net.DELAY)

    def test_slot_holds_across_runs(self):
        self.assertEqual(_net._reserve("geneteka.genealodzy.pl", 120, now=1000.0), 1000.0)
        _net._next_slot.clear()                      # a new process forgets its memory, not the file
        self.assertEqual(_net._reserve("geneteka.genealodzy.pl", 120, now=1010.0), 1120.0)
        self.assertEqual(_net._reserve("other.example", 1, now=1010.0), 1010.0)

    def test_clock_jump_does_not_block_for_days(self):
        with open(os.path.join(self.tmp, "next-request.json"), "w") as f:
            json.dump({"geneteka.genealodzy.pl": 10_000_000.0}, f)
        self.assertEqual(_net._reserve("geneteka.genealodzy.pl", 120, now=1000.0), 1000.0)

    def test_long_wait_is_announced(self):
        self.fake(200, ROBOTS_PTG)
        slept = []
        old_sleep, old_reserve = _net.time.sleep, _net._reserve
        _net.time.sleep, _net._reserve = slept.append, lambda host, delay, now=None: _net.time.time() + 90
        try:
            err = io.StringIO()
            with redirect_stderr(err):
                _net._wait_turn(GENETEKA)
        finally:
            _net.time.sleep, _net._reserve = old_sleep, old_reserve
        self.assertIn("Crawl-delay 120", err.getvalue())
        self.assertTrue(slept and 85 < slept[0] <= 90)


class SearchLogTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        os.environ["GENEALOGY_LOG"] = os.path.join(self.tmp, "searches.jsonl")
        self.err = io.StringIO()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def rec(self, *a, **k):
        with redirect_stderr(self.err):
            return search_log.record(*a, **k)

    def test_check_finds_earlier_search_across_spellings_and_years(self):
        self.rec("geneteka", "podkarpackie (09pk) rid 4321", "Wierzbic", "negative", rtype="B",
                 years="1812-1826", count=0)
        rep = search_log.check_report(source="geneteka", surname="wierzbic", years="1820-1830")
        self.assertIn("1 earlier search", rep)
        self.assertIn("covers only the years", rep)
        self.assertIn("no earlier search", search_log.check_report(surname="Wierzbic", years="1850-1860"))

    def test_inconclusive_does_not_count_as_searched(self):
        self.rec("geneteka", "podkarpackie (09pk) whole province", "Nowak", "inconclusive", rtype="S")
        self.assertIn("does not count as searched", search_log.check_report(surname="Nowak"))

    def test_bad_result_word_is_rejected(self):
        with self.assertRaises(ValueError):
            search_log.record("x", "y", "Nowak", "nothing")

    def test_geneteka_logs_each_query_once_a_day(self):
        with redirect_stderr(self.err):
            geneteka.log_search("09pk", "B", "Nowak", "", "4321", "", "", 3, [])
            geneteka.log_search("09pk", "B", "Nowak", "", "4321", "", "", 3, [])
            geneteka.log_search("09pk", "D", "Nowak", "", None, "", "", 40000, ["over 3000 rows"])
        es = search_log.entries("search")
        self.assertEqual([e["result"] for e in es], ["found", "inconclusive"])
        self.assertIn("rid 4321", es[0]["where"])
        self.assertIn("logged to", self.err.getvalue())

    def test_page_to_scan(self):
        with redirect_stderr(self.err):
            search_log.main(["calibrate", "--book", "Dębina 1850-1870", "--page", "100", "--scan", "51"])
            self.assertEqual(search_log.where_is("Dębina 1850-1870", 107)[0], 58)   # one pair: offset
            search_log.main(["calibrate", "--book", "dębina  1850-1870", "--page", "120", "--scan", "61"])
        self.assertEqual(search_log.where_is("Dębina 1850-1870", 110)[0], 56)       # two pages per scan
        self.assertEqual(search_log.where_is("Dębina 1850-1870", 120), (61, "measured"))
        self.assertIsNone(search_log.where_is("another book", 3)[0])

    def test_lessons_by_book(self):
        with redirect_stderr(self.err):
            search_log.main(["lesson", "add", "--book", "AP 35/1234/0/2/7", "two", "years", "per", "page"])
        self.assertEqual(search_log.lessons("35/1234/0/2/7")[0]["text"], "two years per page")
        self.assertEqual(search_log.lessons("other"), [])


class PagingNoticeTest(unittest.TestCase):
    def test_paging_time_is_announced(self):
        old = _net.delay_for
        _net.delay_for = lambda url, verify=True: 120.0
        try:
            err = io.StringIO()
            with redirect_stderr(err):
                geneteka._announce_pages(total=230, first=50, max_rows=250)
                geneteka._announce_pages(total=30, first=30, max_rows=250)
        finally:
            _net.delay_for = old
        self.assertIn("4 more page(s)", err.getvalue())
        self.assertEqual(err.getvalue().count("more page"), 1)


if __name__ == "__main__":
    unittest.main()
