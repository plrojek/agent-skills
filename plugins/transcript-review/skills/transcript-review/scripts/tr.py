#!/usr/bin/env python3
"""Accurate transcript of a noisy, multi-speaker recording: local models + a human review page.

Run every step from the skill's scripts/ folder:
    uv run --python 3.13 --with num2words python tr.py <step> <workdir> [options]

Steps, in order:
    init      <workdir> --audio FILE      create workdir + project.json (edit it: language, prompt, speakers)
    prepare   <workdir>                   16 kHz WAVs (raw + light filter), FLAC for the page, optional denoised FLAC
    speech    <workdir>                   speech regions (pyannote segmentation via sherpa-onnx)
    chunks    <workdir>                   speech chunks <= 28 s, cut at the quietest point
    asr       <workdir>                   Whisper large-v3 (filtered + raw), Whisper turbo (raw), Parakeet v3 (raw)
    review    <workdir>                   build data.json for the review page (keeps existing corrections)
    serve     <workdir> [--port 8765]     run the review page on http://127.0.0.1:PORT/
    score     <workdir>                   score every system against the finished test passages; test flag rules
    voices    <workdir> [--model M]       speaker matching from the reviewed lines (+ pins); compares voice models
    build     <workdir> [--out FILE]      final markdown transcript
"""
import argparse, array, json, math, os, re, shutil, subprocess, sys, time, urllib.request, wave

HERE = os.path.dirname(os.path.abspath(__file__))
WHISPER_DIR = os.path.expanduser(os.environ.get("WHISPER_MODELS", "~/whisper-models"))
ASR_DIR = os.path.expanduser(os.environ.get("ASR_MODELS", "~/asr-models"))
WHISPER = {"whisper-v3": "ggml-large-v3.bin", "whisper-turbo": "ggml-large-v3-turbo.bin"}
WHISPER_URL = "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/"
FILTER = "highpass=f=80,afftdn=nf=-25,dynaudnorm=f=150:g=15"   # the only preprocessing that helped (see references)
MAXLEN, PAD = 28.0, 0.3
COLORS = ["#2f6fdf", "#1f8a4c", "#c2410c", "#0f766e", "#7c3aed", "#b45309", "#be185d", "#4d7c0f"]
FILL = {"yy", "yyy", "yyyy", "ee", "eee", "eh", "em", "emm", "mhm", "hm", "hmm", "uhm", "um", "mm", "uh", "erm"}
SYSTEMS = [("whisper-v3", "flt"), ("whisper-v3", "raw"), ("whisper-turbo", "raw"), ("parakeet", "raw")]


# ---------------------------------------------------------------- helpers
def P(w, *a): return os.path.join(w, *a)
def jload(p, default=None):
    return json.load(open(p)) if os.path.exists(p) else default
def jdump(obj, p):
    tmp = p + ".tmp"
    with open(tmp, "w") as f: json.dump(obj, f, ensure_ascii=False)
    os.replace(tmp, p)
def run(cmd, **kw):
    r = subprocess.run(cmd, **kw)
    if r.returncode: sys.exit(f"command failed ({r.returncode}): {' '.join(map(str, cmd))[:200]}")
    return r
def project(w):
    pj = jload(P(w, "project.json"))
    if not pj: sys.exit(f"no project.json in {w} - run: tr.py init {w} --audio FILE")
    return pj
def ffmpeg(*args): run(["ffmpeg", "-loglevel", "error", "-y", *args])
def uvpy(script, *args, deps=("sherpa-onnx", "numpy>=2.3"), py="3.13"):
    cmd = ["uv", "run", "-q", "--python", py]
    for d in deps: cmd += ["--with", d]
    run(cmd + ["python", "-I", P(HERE, script), *map(str, args)])
def fmt(t): t = max(0, t); return f"{int(t // 60):02d}:{int(t % 60):02d}"

def norm_tokens(word, lang="pl"):
    """lowercase, no punctuation, digits spelled out (num2words if available) -> list of tokens"""
    t = re.sub(r"\[[^\]]*\]", " ", str(word).lower())
    t = re.sub(r"(\d+)\s*/\s*(\d+)", r"\1 przez \2" if lang == "pl" else r"\1 \2", t)
    t = re.sub(r"(\d+)-(\d+)", r"\1 \2", t)
    try:
        from num2words import num2words
        t = re.sub(r"\d+", lambda m: " " + num2words(int(m.group(0)), lang=lang) + " ", t)
    except Exception:
        pass
    t = re.sub(r"[^\w\s]", " ", t)
    return [x for x in t.split() if x not in FILL]

def read_wav(path):
    with wave.open(path) as f:
        a = array.array("h"); a.frombytes(f.readframes(f.getnframes())); return a, f.getframerate()

def words_of(w, name):
    d = jload(P(w, "asr", name + ".json"))
    if not d: return []
    return sorted((x for v in d["chunks"].values() for x in v), key=lambda x: x[1])


# ---------------------------------------------------------------- init / prepare / speech / chunks
def cmd_init(a):
    w = a.workdir; os.makedirs(w, exist_ok=True)
    if os.path.exists(P(w, "project.json")): sys.exit("project.json already exists")
    pj = {"title": os.path.splitext(os.path.basename(a.audio))[0], "audio": os.path.abspath(a.audio), "language": "pl",
          "prompt": "Names, places, numbers and technical terms likely to be said, comma-separated.",
          "speakers": [{"key": "s1", "name": "Speaker 1"}, {"key": "s2", "name": "Speaker 2"}],
          "rare": [], "only_in": {}, "pins": [], "test_passages": [], "extra_passages": [],
          "main": "whisper-v3__flt"}
    jdump(pj, P(w, "project.json")); print("edit", P(w, "project.json"))

def cmd_prepare(a):
    w = a.workdir; pj = project(w); os.makedirs(P(w, "audio"), exist_ok=True)
    ffmpeg("-i", pj["audio"], "-vn", "-ac", "1", "-ar", "16000", "-acodec", "pcm_s16le", P(w, "audio", "raw16.wav"))
    ffmpeg("-i", P(w, "audio", "raw16.wav"), "-af", FILTER, "-acodec", "pcm_s16le", P(w, "audio", "flt16.wav"))
    ffmpeg("-i", pj["audio"], "-vn", "-ac", "1", "-c:a", "flac", P(w, "audio", "orig.flac"))   # Chrome cannot play ALAC
    df = shutil.which("deep-filter") or os.path.join(ASR_DIR, "bin", "deep-filter")
    if os.path.exists(df):   # for listening only - it makes every ASR model worse
        tmp = P(w, "audio", "df"); os.makedirs(tmp, exist_ok=True)
        ffmpeg("-i", pj["audio"], "-vn", "-ac", "1", "-ar", "48000", "-acodec", "pcm_s16le", P(tmp, "in48.wav"))
        run([df, "-D", "-o", P(tmp, "out"), P(tmp, "in48.wav")], capture_output=True)
        ffmpeg("-i", P(tmp, "out", "in48.wav"), "-c:a", "flac", P(w, "audio", "clean.flac")); shutil.rmtree(tmp)
    print("audio ready in", P(w, "audio"))

def cmd_speech(a):
    uvpy("speech.py", a.workdir)

def cmd_chunks(a):
    w = a.workdir
    regs = []
    for s, e in sorted(map(tuple, jload(P(w, "speech.json")))):
        if regs and s - regs[-1][1] < 0.6: regs[-1][1] = max(regs[-1][1], e)
        else: regs.append([s, e])
    x, sr = read_wav(P(w, "audio", "raw16.wav")); dur = len(x) / sr
    def quietest(s, e):
        f = int(0.2 * sr); best, bt = None, s
        i = int(s * sr)
        while i + f <= int(e * sr):
            seg = x[i:i + f]; v = sum(q * q for q in seg[::4])
            if best is None or v < best: best, bt = v, i / sr + 0.1
            i += f
        return bt
    pieces = []
    for s, e in regs:
        while e - s > MAXLEN:
            c = quietest(s + 15, s + MAXLEN); pieces.append([s, c]); s = c
        pieces.append([s, e])
    chunks = []
    for s, e in pieces:
        if chunks and s - chunks[-1][1] < 1.5 and e - chunks[-1][0] <= MAXLEN: chunks[-1][1] = e
        else: chunks.append([s, e])
    meta = []
    for v, src in (("raw", "raw16.wav"), ("flt", "flt16.wav")):
        os.makedirs(P(w, "chunks", v), exist_ok=True)
    for i, (s, e) in enumerate(chunks):
        s0, e0 = max(0, s - PAD), min(dur, e + PAD)
        meta.append({"i": i, "s": round(s0, 3), "e": round(e0, 3)})
        for v, src in (("raw", "raw16.wav"), ("flt", "flt16.wav")):
            ffmpeg("-ss", f"{s0:.3f}", "-t", f"{e0 - s0:.3f}", "-i", P(w, "audio", src), "-acodec", "pcm_s16le", P(w, "chunks", v, f"c{i:03d}.wav"))
    jdump(meta, P(w, "chunks", "chunks.json"))
    print(len(meta), "chunks,", round(sum(m["e"] - m["s"] for m in meta) / 60, 1), "min of speech")


# ---------------------------------------------------------------- ASR
def ensure_whisper(model):
    p = os.path.join(WHISPER_DIR, WHISPER[model])
    if not os.path.exists(p):
        os.makedirs(WHISPER_DIR, exist_ok=True); print("downloading", WHISPER[model], "(~1.6-3 GB)")
        urllib.request.urlretrieve(WHISPER_URL + WHISPER[model], p + ".part"); os.replace(p + ".part", p)
    return p

BAD = re.compile(r"subskryb|zafollow|oglądanie|napisy|wszelkie prawa|thanks for watching|subscribe", re.I)

def run_whisper(w, pj, model, var):
    mf = ensure_whisper(model); name = f"{model}__{var}"
    rd = P(w, "runs", name); os.makedirs(rd, exist_ok=True)
    meta = jload(P(w, "chunks", "chunks.json"))
    args = []
    for m in meta:
        f = P(rd, f"c{m['i']:03d}.wav")
        if os.path.exists(f + ".json"): continue
        if not os.path.exists(f): os.symlink(P(w, "chunks", var, f"c{m['i']:03d}.wav"), f)
        args += ["-f", f]
    # several files in one call give identical output to one call per file, and load the model once
    for k in range(0, len(args), 80):
        run(["whisper-cli", "-l", pj.get("language", "pl"), "-t", "8", "-m", mf, "-sns", "-bs", "5", "--prompt", pj.get("prompt", ""),
             "-ojf", *args[k:k + 80]], capture_output=True)
    prompt_words = set(norm_tokens(pj.get("prompt", ""), pj.get("language", "pl")))
    res = {}
    for m in meta:
        d = jload(P(rd, f"c{m['i']:03d}.wav.json"), {"transcription": []}); ws = []
        for seg in d["transcription"]:
            t = seg["text"]
            # drop stock fillers and verbatim echoes of the prompt
            if BAD.search(t): continue
            st = norm_tokens(t, pj.get("language", "pl"))
            if len(st) >= 4 and sum(1 for q in st if q in prompt_words) / len(st) > 0.8 and "," in t: continue
            for tok in seg["tokens"]:
                if tok["text"].startswith("[_"): continue
                s, e = m["s"] + tok["offsets"]["from"] / 1000, m["s"] + tok["offsets"]["to"] / 1000
                if tok["text"].startswith(" ") or not ws: ws.append([tok["text"].strip(), s, e, tok["p"]])
                else: ws[-1][0] += tok["text"]; ws[-1][2] = e; ws[-1][3] = min(ws[-1][3], tok["p"])
        res[m["i"]] = [q for q in ws if q[0]]
    os.makedirs(P(w, "asr"), exist_ok=True); jdump({"chunks": res}, P(w, "asr", name + ".json"))
    print(name, sum(len(v) for v in res.values()), "words")

def cmd_asr(a):
    w = a.workdir; pj = project(w)
    systems = list(SYSTEMS)
    for model, var in systems:
        if model.startswith("whisper"): run_whisper(w, pj, model, var)
        elif model == "parakeet": uvpy("parakeet_asr.py", w, var, deps=("parakeet-mlx",))


# ---------------------------------------------------------------- shared: flags, timing, lines
def flag_support(w, pj, main):
    """for each word of the main system: how many other systems heard the same word within 1.2 s"""
    lang = pj.get("language", "pl")
    others = [os.path.basename(f)[:-5] for f in sorted(os.listdir(P(w, "asr"))) if f.endswith(".json") and f[:-5] != main]
    idx = {}
    for o in others:
        d = {}
        for q in words_of(w, o):
            for t in norm_tokens(q[0], lang)[:1]: d.setdefault(t, []).append(q[1])
        idx[o] = d
    need = max(1, math.ceil(len(others) / 2))
    def support(q):
        t = norm_tokens(q[0], lang)
        if not t: return len(others)
        return sum(1 for o in others if any(abs(s - q[1]) < 1.2 for s in idx[o].get(t[0], [])))
    return support, need, others

def timing_words(w):
    """precise word times: Parakeet first (Whisper's own word times drift), else turbo"""
    for name in ("parakeet__raw", "whisper-turbo__raw"):
        ws = words_of(w, name)
        if ws: return name, ws
    return None, []

def retime(ws, timed, lang):
    """start/end of a run of words from the precise timer (monotonic LCS, plausible jump only)"""
    toks = [(x, k) for k, q in enumerate(ws) for x in norm_tokens(q[0], lang)]
    if not toks or not timed: return ws[0][1], ws[-1][2]
    T = [(x, p) for p in timed if ws[0][1] - 8 <= p[1] <= ws[-1][2] + 8 for x in norm_tokens(p[0], lang)]
    n, m = len(toks), len(T)
    if not m: return ws[0][1], ws[-1][2]
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            dp[i][j] = dp[i - 1][j - 1] + 1 if toks[i - 1][0] == T[j - 1][0] else max(dp[i - 1][j], dp[i][j - 1])
    hits = []; i, j = n, m
    while i and j:
        if toks[i - 1][0] == T[j - 1][0] and dp[i][j] == dp[i - 1][j - 1] + 1: hits.append(T[j - 1][1]); i -= 1; j -= 1
        elif dp[i - 1][j] >= dp[i][j - 1]: i -= 1
        else: j -= 1
    if not hits: return ws[0][1], ws[-1][2]
    hits.reverse(); s, e = hits[0][1], hits[-1][2]
    jump = abs(s - ws[0][1])
    if len(hits) < max(1, len(toks) // 3) or jump > 12 or (jump > 2 and len(hits) < 2): return ws[0][1], ws[-1][2]
    return s, max(e, s + 0.3)

def machine_lines(w, pj, drop=None):
    """main-system words -> lines (one speaker each when voices.json exists), with flags and precise times.
    drop: words (text, start, end) to leave out, i.e. the ones a checked passage replaces"""
    lang = pj.get("language", "pl"); main = pj.get("main", "whisper-v3__flt")
    ws = words_of(w, main)
    if not ws: sys.exit(f"no ASR output asr/{main}.json - run the asr step")
    support, need, _ = flag_support(w, pj, main)
    voices = jload(P(w, "voices.json"))   # [{s,e,spk,m}] frame labels from the voices step
    pins = pj.get("pins", [])
    def spk_of(q):
        mid = (q[1] + q[2]) / 2
        for a, b, k in pins:
            if a <= mid <= b: return k, 1.0, True
        if not voices: return None, None, False
        best, bo = None, 0.0
        for v in voices:
            o = min(q[2], v["e"]) - max(q[1], v["s"])
            if o > bo: best, bo = v, o
        if best is None:
            best = min(voices, key=lambda v: min(abs(mid - v["s"]), abs(mid - v["e"])))
        return best["spk"], best["m"], False
    if drop: ws = [q for q in ws if (q[0], q[1], q[2]) not in drop]
    lab = [spk_of(q) for q in ws]
    # smooth: a run of < 1.2 s inside one sentence takes its neighbour's speaker unless pinned
    runs = []
    for q, (k, m, pin) in zip(ws, lab):
        if runs and runs[-1]["k"] == k and q[1] - runs[-1]["ws"][-1][2] < 1.5: runs[-1]["ws"].append(q); runs[-1]["ms"].append(m); runs[-1]["pin"] |= pin
        else: runs.append({"k": k, "ws": [q], "ms": [m], "pin": pin})
    changed = True
    while changed:
        changed = False
        for i, r in enumerate(runs):
            d = r["ws"][-1][2] - r["ws"][0][1]
            if r["pin"] or d >= 1.2 or len(runs) == 1: continue
            nb = [j for j in (i - 1, i + 1) if 0 <= j < len(runs) and runs[j]["ws"][0][1] - r["ws"][-1][2] < 1.5 and r["ws"][0][1] - runs[j]["ws"][-1][2] < 1.5]
            if not nb: continue
            j = max(nb, key=lambda j: runs[j]["ws"][-1][2] - runs[j]["ws"][0][1])
            a_, b_ = sorted((i, j)); k = runs[j]["k"]
            runs[a_:b_ + 1] = [{"k": k, "ws": runs[a_]["ws"] + runs[b_]["ws"], "ms": runs[a_]["ms"] + runs[b_]["ms"], "pin": runs[a_]["pin"] or runs[b_]["pin"]}]
            changed = True; break
    # split long runs at sentence ends (or pauses) into lines of <= 14 s
    tname, timed = timing_words(w)
    lines = []
    for r in runs:
        cur = []
        for k, q in enumerate(r["ws"]):
            if cur and (q[1] - cur[-1][2] > 0.8 and voices is None):
                lines.append((r, cur)); cur = []
            cur.append(q)
            dur = cur[-1][2] - cur[0][1]; rest = r["ws"][-1][2] - q[2]
            if (re.search(r"[.?!…]$", q[0]) and dur >= 4 and rest >= 3) or (dur >= 14 and rest >= 3):
                lines.append((r, cur)); cur = []
        if cur:
            if lines and lines[-1][0] is r and cur[-1][2] - cur[0][1] < 2: lines[-1] = (r, lines[-1][1] + cur)
            else: lines.append((r, cur))
    margins = sorted(m for r in runs if not r["pin"] for m in r["ms"] if m is not None)
    weak_cut = margins[int(len(margins) * 0.12)] if margins else 0
    names = {s["key"]: s["name"] for s in pj["speakers"]}
    out = []
    for r, lw in lines:
        s, e = retime(lw, timed, lang)
        ms = [m for m in r["ms"] if m is not None]
        weak = (r["k"] is None) or (not r["pin"] and ms and sum(ms) / len(ms) < weak_cut)
        out.append({"s": round(s, 2), "e": round(e, 2), "spk": names.get(r["k"], "?"), "spk_weak": bool(weak),
                    "w0": round(lw[0][1], 3), "w1": round(lw[-1][2], 3),   # the main system's own times of the first/last word
                    "words": [[q[0], support(q) < need and any(c.isalnum() for c in q[0])] for q in lw]})
    out.sort(key=lambda l: l["s"])
    for i in range(len(out) - 1):
        if out[i]["e"] > out[i + 1]["s"] > out[i]["s"]: out[i]["e"] = out[i + 1]["s"]
    return out


# ---------------------------------------------------------------- review page data
def cmd_review(a):
    w = a.workdir; pj = project(w); lang = pj.get("language", "pl")
    lines = machine_lines(w, pj)
    sections = [{"id": f"t{i+1}", "title": f"Test {i+1}", "s": s, "e": e, "kind": "test"} for i, (s, e) in enumerate(pj.get("test_passages", []))]
    sections += [{"id": f"x{i+1}", "title": x.get("title", f"Passage {i+1}"), "s": x["s"], "e": x["e"], "kind": "extra"}
                 for i, x in enumerate(pj.get("extra_passages", []))]
    if not sections: sys.exit("project.json has no test_passages / extra_passages")
    tname, timed = timing_words(w)
    t2 = words_of(w, "whisper-turbo__raw")
    data = {"title": pj.get("title", ""), "speakers": [{"name": s["name"], "color": s.get("color", COLORS[i % len(COLORS)])} for i, s in enumerate(pj["speakers"])]
            + [{"name": "several at once", "color": "#64748b"}, {"name": "?", "color": "#9ca3af"}],
            "sections": sections, "has_clean": os.path.exists(P(w, "audio", "clean.flac")),
            "lines": [{"id": f"L{i:04d}", "s": l["s"], "e": max(l["e"], l["s"] + 0.5), "w0": l["w0"], "w1": l["w1"], "spk": l["spk"],
                       "text": " ".join(q for q, _ in l["words"]), "unsure": [q for q, u in l["words"] if u]} for i, l in enumerate(lines)],
            "timed": [[q[0], round(q[1], 2), round(q[2], 2)] for q in timed], "timed2": [[q[0], round(q[1], 2), round(q[2], 2)] for q in t2]}
    jdump(data, P(w, "data.json"))
    print(f"data.json: {len(data['lines'])} lines, {len(sections)} passages; open with: tr.py serve {w}")

def cmd_serve(a):
    run([sys.executable, P(HERE, "review", "review_server.py"), a.workdir, str(a.port)])


# ---------------------------------------------------------------- reviewed passages
def finished(w, kinds=("test", "extra")):
    """passages marked finished: their rows, a padded time span, and "shown" = the span (in the main system's own
    word times) of the machine lines the page put in front of the user, saved by the page when it opened the passage"""
    D = jload(P(w, "data.json"), {}); C = jload(P(w, "corrections.json"), {})
    out = []
    for s in D.get("sections", []):
        sec = C.get("sections", {}).get(s["id"])
        if not sec or not sec.get("done") or s.get("kind", "test") not in kinds: continue
        rows = sec["rows"]; shown = sec.get("shown")
        if not shown:
            ls = [l for l in D.get("lines", []) if l["s"] <= s["e"] and l["e"] >= s["s"] and "w0" in l]
            shown = [min(l["w0"] for l in ls), max(l["w1"] for l in ls)] if ls else None
        out.append({"id": s["id"], "s": min([r["s"] for r in rows] + [s["s"]]) - 0.3, "e": max([r["e"] for r in rows] + [s["e"]]) + 0.3,
                    "rows": rows, "shown": shown})
    return out

def ed_sid(a, b):
    n, m = len(a), len(b)
    D = [[(0, 0, 0, 0)] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1): D[i][0] = (i, 0, 0, i)
    for j in range(1, m + 1): D[0][j] = (j, 0, j, 0)
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            c, s_, i_, d_ = D[i - 1][j - 1]; best = (c + (a[i - 1] != b[j - 1]), s_ + (a[i - 1] != b[j - 1]), i_, d_)
            c, s_, i_, d_ = D[i][j - 1]
            if c + 1 < best[0]: best = (c + 1, s_, i_ + 1, d_)
            c, s_, i_, d_ = D[i - 1][j]
            if c + 1 < best[0]: best = (c + 1, s_, i_, d_ + 1)
            D[i][j] = best
    return D[n][m][1:]

def cmd_score(a):
    w = a.workdir; pj = project(w); lang = pj.get("language", "pl")
    secs = finished(w, ("test",))
    if not secs: sys.exit("no finished test passage yet")
    for S in secs:   # score inside the checked lines' own span (Parakeet-timed), not the padded passage window
        if S["rows"]: S["s"], S["e"] = min(r["s"] for r in S["rows"]) - 0.3, max(r["e"] for r in S["rows"]) + 0.3
    refs = [(S, [t for r in S["rows"] for t in norm_tokens(r["text"], lang)]) for S in secs]
    N = sum(len(r) for _, r in refs)
    print(f"finished test passages: {[S['id'] for S in secs]} - reference words: {N}\n")
    print(f"{'system__audio':28s} {'WER':>6s}  wrong  missing")
    rows = []
    for f in sorted(os.listdir(P(w, "asr"))):
        if not f.endswith(".json"): continue
        name = f[:-5]; ws = words_of(w, name); S_ = I_ = D_ = 0
        for S, ref in refs:
            hyp = [t for q in ws if S["s"] <= (q[1] + q[2]) / 2 <= S["e"] for t in norm_tokens(q[0], lang)]
            s, i, d = ed_sid(ref, hyp); S_ += s; I_ += i; D_ += d
        rows.append((100 * (S_ + I_ + D_) / max(1, N), name, S_ + I_, D_))
    for wer, name, wrong, miss in sorted(rows): print(f"{name:28s} {wer:6.1f}  {wrong:5d}  {miss:7d}")
    best = sorted(rows)[0][1]
    print(f"\nbest single system: {best}  (project.json 'main' is {pj.get('main')})")
    # which flag rule marks the main system's real errors best
    main = pj.get("main", "whisper-v3__flt"); support, need, others = flag_support(w, pj, main)
    items = []
    for S, ref in refs:
        hw = [q for q in words_of(w, main) if S["s"] <= (q[1] + q[2]) / 2 <= S["e"] and norm_tokens(q[0], lang)]
        hyp = [norm_tokens(q[0], lang)[0] for q in hw]
        n, m = len(ref), len(hyp); dp = [[0] * (m + 1) for _ in range(n + 1)]
        for i in range(1, n + 1):
            for j in range(1, m + 1): dp[i][j] = dp[i - 1][j - 1] + 1 if ref[i - 1] == hyp[j - 1] else max(dp[i - 1][j], dp[i][j - 1])
        ok = set(); i, j = n, m
        while i and j:
            if ref[i - 1] == hyp[j - 1] and dp[i][j] == dp[i - 1][j - 1] + 1: ok.add(j - 1); i -= 1; j -= 1
            elif dp[i - 1][j] >= dp[i][j - 1]: i -= 1
            else: j -= 1
        items += [(j not in ok, q[3], support(q)) for j, q in enumerate(hw)]
    E = sum(x[0] for x in items)
    print(f"\nflag rules on {main} ({len(items)} words, {E} wrong):")
    for label, f in [("model confidence < 0.35", lambda x: x[1] < 0.35),
                     (f"fewer than {need} of {len(others)} other systems heard it (used)", lambda x: x[2] < need)]:
        fl = [x for x in items if f(x)]; tp = sum(x[0] for x in fl)
        print(f"  {label:58s} flags {100*len(fl)/max(1,len(items)):3.0f}% | {100*tp/max(1,len(fl)):3.0f}% of flagged wrong | catches {100*tp/max(1,E):3.0f}% of errors")


# ---------------------------------------------------------------- speakers
def cmd_voices(a):
    w = a.workdir; pj = project(w)
    enr = {s["key"]: [] for s in pj["speakers"]}; key = {s["name"]: s["key"] for s in pj["speakers"]}
    secs = finished(w)
    for S in secs:
        for r in S["rows"]:
            if r["spk"] in key and r["e"] - r["s"] >= 0.8: enr[key[r["spk"]]].append([r["s"], r["e"]])
    for s, e, k in pj.get("pins", []):
        if e - s >= 0.8 and not any(S["s"] <= e and S["e"] >= s for S in secs): enr.setdefault(k, []).append([s, e])
    jdump(enr, P(w, "enroll.json"))
    print("voice samples:", {k: f"{len(v)} lines / {sum(e - s for s, e in v):.0f} s" for k, v in enr.items()}, flush=True)
    uvpy("voices.py", w, a.model or "auto")


# ---------------------------------------------------------------- final transcript
def lev(a, b):
    d = list(range(len(b) + 1))
    for i in range(1, len(a) + 1):
        p, d[0] = d[0], i
        for j in range(1, len(b) + 1):
            p, d[j] = d[j], min(d[j] + 1, d[j - 1] + 1, p + (a[i - 1] != b[j - 1]))
    return d[len(b)]

def repeated(user, cand, lang, after, limit):
    """How many machine words next to a checked passage repeat its edge, because the user typed them while listening
    past the lines the page showed. after=True: cand = words after the passage in time order, compared with the end
    of the user's text; after=False: cand = words before it, nearest first, compared with its start. At least two
    tokens, at most a quarter different, and only words the user's lines reach in time (limit)."""
    best, best_m = 0, 0
    for k in range(1, min(len(cand), 30) + 1):
        if (after and cand[k - 1][1] > limit) or (not after and cand[k - 1][2] < limit): break
        mt = [t for q in (cand[:k] if after else cand[:k][::-1]) for t in norm_tokens(q[0], lang)]
        if len(mt) < 2: continue
        if len(mt) > len(user) + 2: break
        for L in range(max(1, len(mt) - 2), min(len(user), len(mt) + 2) + 1):
            d = lev(mt, user[-L:] if after else user[:L])
            if d <= 0.25 * max(len(mt), L) and len(mt) - d > best_m: best, best_m = k, len(mt) - d
    return best

def cmd_build(a):
    w = a.workdir; pj = project(w); lang = pj.get("language", "pl")
    secs = finished(w)
    # A checked passage replaces exactly the machine words the page showed for it. Whisper's word times drift, so
    # a time window around the passage would drop words nobody checked; words the user deleted stay deleted.
    allw = words_of(w, pj.get("main", "whisper-v3__flt")); mid = [(q[1] + q[2]) / 2 for q in allw]
    drop = set()
    for S in secs:
        rows = sorted(S["rows"], key=lambda r: r["s"])
        U = [t for r in rows for t in norm_tokens(r["text"], lang)]
        if S["shown"]: lo, hi = S["shown"]
        elif rows: lo, hi = rows[0]["s"] - 0.3, max(r["e"] for r in rows) + 0.3   # no record of what was shown
        else: lo, hi = S["s"], S["e"]
        drop.update(i for i, m in enumerate(mid) if lo - 0.002 <= m <= hi + 0.002)
        if not U: continue
        rs, re_ = rows[0]["s"], max(r["e"] for r in rows)
        after = [i for i, m in enumerate(mid) if hi + 0.002 < m and allw[i][1] <= hi + 15]
        drop.update(after[:repeated(U, [allw[i] for i in after], lang, True, re_ + 1.0)])
        before = [i for i in range(len(allw) - 1, -1, -1) if mid[i] < lo - 0.002 and allw[i][2] >= lo - 15]
        drop.update(before[:repeated(U, [allw[i] for i in before], lang, False, rs - 1.0)])
    lines = [l for l in machine_lines(w, pj, drop={(allw[i][0], allw[i][1], allw[i][2]) for i in drop}) if l["words"]]
    items = []
    for l in lines:
        txt = " ".join((f"*{q.rstrip('.,?!…:;')}*{q[len(q.rstrip('.,?!…:;')):]}" if u and q.rstrip('.,?!…:;') else q) for q, u in l["words"])
        items.append({"s": l["s"], "lab": l["spk"] + (" (?)" if l["spk_weak"] and l["spk"] != "?" else ""), "text": txt, "ver": False,
                      "nw": len(l["words"]), "nu": sum(1 for _, u in l["words"] if u)})
    for S in secs:
        for r in S["rows"]:
            if r["text"].strip():
                t = re.sub(r"\[([^\]]+)\]", lambda m: f"[{m.group(1)}]" if m.group(1) in ("?", "niezrozumiałe", "inaudible") else f"*[{m.group(1)}]*", r["text"].strip())
                items.append({"s": r["s"], "lab": r["spk"], "text": t, "ver": True, "nw": 0, "nu": 0})
    items.sort(key=lambda x: x["s"])
    nw = sum(i["nw"] for i in items); nu = sum(i["nu"] for i in items); nv = sum(1 for i in items if i["ver"])
    nweak = sum(1 for i in items if i["lab"].endswith("(?)"))
    spans = ", ".join(f"{fmt(S['s'] + 0.3)}–{fmt(S['e'] - 0.3)}" for S in secs)
    L = ["---", f"tags: [type/transcript]", f"created: {time.strftime('%Y-%m-%d')}", f'source: "{os.path.basename(pj["audio"])}"',
         f"language: {lang}", "---", "", f"# Transcript: {pj.get('title', '')}", "",
         "**How to read it:**",
         f"- **✓ after the time** = checked and corrected by ear ({nv} lines; passages {spans or 'none'}). Treat as exact.",
         f"- *Italic words* = fewer than half of the other speech models heard that word ({nu} of {nw} machine words). Listen before quoting.",
         f"- **(?)** after a name = weak voice match ({nweak} lines). A bare **?** = speaker unknown.",
         "- Unmarked machine text is not verified. Nothing was filled in by guessing from context.", "",
         f"**Method:** {pj.get('main')} on speech chunks of ≤ 28 s with a vocabulary prompt; other models only flag doubtful words; "
         "speakers matched by voice against the checked lines (transcript-review skill).", "", "---", ""]
    for it in items:
        L += [f"**[{fmt(it['s'])}]{' ✓' if it['ver'] else ''} {it['lab']}:** {it['text']}", ""]
    out = a.out or P(w, "transcript.md")
    open(out, "w").write("\n".join(L))
    print(f"{out}: {len(items)} lines, {nv} checked by ear, {nu}/{nw} machine words in italics, {nweak} weak speakers")


# ---------------------------------------------------------------- main
if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="step", required=True)
    for name in ["init", "prepare", "speech", "chunks", "asr", "review", "serve", "score", "voices", "build"]:
        p = sp.add_parser(name); p.add_argument("workdir")
        if name == "init": p.add_argument("--audio", required=True)
        if name == "serve": p.add_argument("--port", type=int, default=8765)
        if name == "voices": p.add_argument("--model", choices=["campplus", "eres2netv2", "eres2net"])
        if name == "build": p.add_argument("--out")
    a = ap.parse_args(); a.workdir = os.path.abspath(os.path.expanduser(a.workdir))
    globals()["cmd_" + a.step](a)
