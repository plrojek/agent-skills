"""Shared HTTP helpers for the source scripts.

- An honest User-Agent naming this project. Override with GENEALOGY_UA.
- At least GENEALOGY_DELAY seconds (default 1.0) between requests to the same host,
  also across threads. Most of these sites are run by volunteers or small offices.
- Retries with back-off on timeouts, 5xx and truncated downloads.
- A small JSON cache in ~/.cache/pl-genealogy-record-search (GENEALOGY_CACHE_DIR),
  entries older than GENEALOGY_CACHE_DAYS (default 30) are ignored.
"""
import hashlib
import http.client
import json
import os
import ssl
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

VERSION = "1.0.0"
UA = os.environ.get("GENEALOGY_UA") or (
    f"pl-genealogy-record-search/{VERSION} (+https://github.com/plrojek/agent-skills)")
DELAY = float(os.environ.get("GENEALOGY_DELAY", "1.0"))
CACHE_DIR = os.path.expanduser(os.environ.get("GENEALOGY_CACHE_DIR") or os.path.join(
    os.environ.get("XDG_CACHE_HOME") or "~/.cache", "pl-genealogy-record-search"))
CACHE_DAYS = float(os.environ.get("GENEALOGY_CACHE_DAYS", "30"))

_lock = threading.Lock()
_next_slot = {}


def _wait_turn(host):
    """Reserve the next free slot for this host and sleep until it comes."""
    with _lock:
        now = time.monotonic()
        slot = max(now, _next_slot.get(host, 0.0))
        _next_slot[host] = slot + DELAY
    if slot > now:
        time.sleep(slot - now)


def get(url, headers=None, timeout=60, tries=3, verify=True, raw=False, encoding="utf-8"):
    """GET a URL politely. Returns str (or bytes with raw=True). Raises on final failure."""
    host = urllib.parse.urlsplit(url).hostname or ""
    hdr = {"User-Agent": UA}
    hdr.update(headers or {})
    ctx = None if verify else ssl._create_unverified_context()
    for attempt in range(tries):
        _wait_turn(host)
        try:
            req = urllib.request.Request(url, headers=hdr)
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
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


def cache_get(key):
    p = _cache_path(key)
    try:
        if time.time() - os.path.getmtime(p) > CACHE_DAYS * 86400:
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
