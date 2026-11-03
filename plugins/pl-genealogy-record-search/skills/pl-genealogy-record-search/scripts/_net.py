"""Shared HTTP helpers for the source scripts.

- An honest User-Agent naming this project. Override with GENEALOGY_UA.
- Each site's robots.txt is read (once a day, cached) and obeyed: a path it disallows is
  not requested, and its Crawl-delay is the wait between two requests to that site.
  Geneteka asks for 120 s, Metryki and Skanoteka for 60 s. Where a site publishes no
  Crawl-delay, the wait is GENEALOGY_DELAY seconds (default 1.0). GENEALOGY_DELAY can make
  the wait longer, never shorter than what the site asks for.
- The wait holds across separate runs of the scripts, not only within one: the time of the
  next allowed request per site is kept in the cache folder (with a file lock on macOS and
  Linux). Waits longer than a few seconds are announced on stderr.
- Retries with back-off on timeouts, 5xx and truncated downloads.
- A small JSON cache in ~/.cache/pl-genealogy-record-search (GENEALOGY_CACHE_DIR),
  entries older than GENEALOGY_CACHE_DAYS (default 30) are ignored.
"""
import hashlib
import http.client
import json
import os
import ssl
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser

try:
    import fcntl
except ImportError:          # Windows: the wait still holds within one run
    fcntl = None

VERSION = "1.1.0"
UA = os.environ.get("GENEALOGY_UA") or (
    f"pl-genealogy-record-search/{VERSION} (+https://github.com/plrojek/agent-skills)")
DELAY = float(os.environ.get("GENEALOGY_DELAY", "1.0"))
CACHE_DIR = os.path.expanduser(os.environ.get("GENEALOGY_CACHE_DIR") or os.path.join(
    os.environ.get("XDG_CACHE_HOME") or "~/.cache", "pl-genealogy-record-search"))
CACHE_DAYS = float(os.environ.get("GENEALOGY_CACHE_DAYS", "30"))

# Used only when a site's robots.txt can't be read (server error, no connection): the
# Crawl-delay these sites published when this was written, so a bad day doesn't mean 1 s.
KNOWN_CRAWL_DELAY = {
    "geneteka.genealodzy.pl": 120.0,
    "metryki.genealodzy.pl": 60.0,
    "skanoteka.genealodzy.pl": 60.0,
}
ROBOTS_TTL = 86400            # a robots.txt that was read (or is absent) is trusted for a day
ROBOTS_RETRY = 3600           # after a server error, try again in an hour
ANNOUNCE_WAIT = 5             # seconds; shorter waits are not printed

_lock = threading.Lock()
_next_slot = {}               # host -> epoch seconds of the next allowed request (this run)
_robots = {}                  # host -> (RobotFileParser, crawl delay or None, how it was read)


class Refused(Exception):
    """A site's robots.txt does not allow this request, or refuses automated access."""


def _context(verify):
    return None if verify else ssl._create_unverified_context()


def _robots_record(host, scheme, verify):
    """robots.txt of a host as {"status", "text", "t"}: from the cache, else fetched."""
    key = f"robots:{scheme}://{host}"
    rec = cache_get(key, max_age=ROBOTS_TTL)
    if rec is not None and (rec["status"] < 500 or time.time() - rec["t"] < ROBOTS_RETRY):
        return rec
    status, text = 0, ""
    req = urllib.request.Request(f"{scheme}://{host}/robots.txt", headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=20, context=_context(verify)) as r:
            status, text = r.status, r.read(512 * 1024).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        status = e.code
    except (urllib.error.URLError, TimeoutError, ConnectionError, http.client.HTTPException, OSError):
        status = 599          # no connection: treated like a server error
    rec = {"status": status, "text": text, "t": time.time()}
    cache_put(key, rec)
    return rec


def robots(url, verify=True):
    """(parser, crawl delay in seconds or None, note) for the host of url."""
    parts = urllib.parse.urlsplit(url)
    host = parts.hostname or ""
    if host in _robots:
        return _robots[host]
    rec = _robots_record(host, parts.scheme or "https", verify)
    rp = urllib.robotparser.RobotFileParser()
    if rec["status"] in (401, 403):
        rp.disallow_all = True                    # same reading as urllib.robotparser.read()
        rp.modified()
        delay, note = None, f"robots.txt answers {rec['status']}: the site refuses automated access"
    elif 200 <= rec["status"] < 300:
        rp.parse(rec["text"].splitlines())
        delay, note = rp.crawl_delay(UA), "robots.txt"
    elif rec["status"] < 500:
        rp.parse([])                              # no robots.txt: no rules
        delay, note = None, "no robots.txt"
    else:
        rp.parse([])
        delay = KNOWN_CRAWL_DELAY.get(host)
        note = "robots.txt unreadable now" + (", using the delay it asked for before" if delay else "")
    _robots[host] = (rp, float(delay) if delay is not None else None, note)
    return _robots[host]


def delay_for(url, verify=True):
    """Seconds to wait between two requests to the host of url."""
    _, crawl, _ = robots(url, verify)
    return max(DELAY, crawl or 0.0)


class _StateLock:
    """Exclusive lock on the shared slot file, so parallel runs don't race."""

    def __enter__(self):
        os.makedirs(CACHE_DIR, exist_ok=True)
        self.f = open(os.path.join(CACHE_DIR, "next-request.lock"), "a+")
        if fcntl:
            fcntl.flock(self.f, fcntl.LOCK_EX)
        return self

    def __exit__(self, *exc):
        if fcntl:
            fcntl.flock(self.f, fcntl.LOCK_UN)
        self.f.close()


def _state_file():
    return os.path.join(CACHE_DIR, "next-request.json")


def _reserve(host, delay, now=None):
    """Reserve the next free slot for host; returns the epoch time it starts."""
    now = time.time() if now is None else now
    with _lock, _StateLock():
        try:
            with open(_state_file(), encoding="utf-8") as f:
                state = json.load(f)
        except (OSError, ValueError):
            state = {}
        slot = max(now, float(state.get(host, 0.0)), _next_slot.get(host, 0.0))
        if slot > now + max(delay, 1.0) * 100:   # a clock that jumped back: don't wait for days
            slot = now
        state[host] = _next_slot[host] = slot + delay
        tmp = _state_file() + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(state, f)
        os.replace(tmp, _state_file())
    return slot


def _wait_turn(url, verify=True):
    host = urllib.parse.urlsplit(url).hostname or ""
    rp, crawl, note = robots(url, verify)
    if not rp.can_fetch(UA, url):
        if rp.disallow_all:
            raise Refused(f"{host}: {note}. Open it in a browser instead; don't work around it.")
        raise Refused(f"{host}/robots.txt disallows {urllib.parse.urlsplit(url).path}; not requested.")
    delay = max(DELAY, crawl or 0.0)
    now = time.time()
    slot = _reserve(host, delay, now)
    wait = slot - now
    if wait > ANNOUNCE_WAIT:
        why = f"robots.txt Crawl-delay {crawl:g} s" if crawl else f"GENEALOGY_DELAY {DELAY:g} s"
        print(f"  waiting {wait:.0f} s for {host} ({why})", file=sys.stderr, flush=True)
    if wait > 0:
        time.sleep(wait)


def get(url, headers=None, timeout=60, tries=3, verify=True, raw=False, encoding="utf-8"):
    """GET a URL politely. Returns str (or bytes with raw=True). Raises on final failure,
    and raises Refused without sending anything when the site's robots.txt says no."""
    hdr = {"User-Agent": UA}
    hdr.update(headers or {})
    for attempt in range(tries):
        _wait_turn(url, verify)
        try:
            req = urllib.request.Request(url, headers=hdr)
            with urllib.request.urlopen(req, timeout=timeout, context=_context(verify)) as r:
                data = r.read()
            return data if raw else data.decode(encoding, "replace")
        except urllib.error.HTTPError as e:
            if e.code < 500 or attempt == tries - 1:
                raise
        except (urllib.error.URLError, TimeoutError, ConnectionError, http.client.IncompleteRead):
            if attempt == tries - 1:
                raise
        time.sleep(3 * (attempt + 1))


def _cache_path(key):
    return os.path.join(CACHE_DIR, hashlib.sha256(key.encode("utf-8")).hexdigest()[:40] + ".json")


def cache_get(key, max_age=None):
    p = _cache_path(key)
    try:
        if time.time() - os.path.getmtime(p) > (CACHE_DAYS * 86400 if max_age is None else max_age):
            return None
        with open(p, encoding="utf-8") as f:
            return json.load(f)["value"]
    except (OSError, ValueError, KeyError):
        return None


def cache_put(key, value):
    os.makedirs(CACHE_DIR, exist_ok=True)
    tmp = _cache_path(key) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"key": key, "value": value}, f, ensure_ascii=False)
    os.replace(tmp, _cache_path(key))


def norm(s):
    """Lower case, no diacritics, ł -> l. For comparing names across spellings."""
    import unicodedata
    s = unicodedata.normalize("NFD", (s or "").lower().replace("ł", "l"))
    return "".join(c for c in s if not unicodedata.combining(c))
