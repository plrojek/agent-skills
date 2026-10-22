# Speaker matching against lines checked by ear.
# 1. compares voice models by leave-one-out accuracy on the checked lines (picks the best, unless forced)
# 2. scores every 2 s window (step 0.5 s) of speech against each person's average voice
# 3. averages per 0.25 s frame and writes <workdir>/voices.json = [{s, e, spk, m}] (m = margin best - second)
# Rules from project.json: "rare" people only where pinned; "only_in" people only inside their windows (e.g. a phone call).
# usage (via tr.py voices): python voices.py <workdir> <auto|campplus|eres2netv2|eres2net>
import json, os, sys, urllib.request, wave
import numpy as np, sherpa_onnx

W, CHOICE = sys.argv[1:3]
MD = os.path.expanduser(os.environ.get("ASR_MODELS", "~/asr-models")) + "/speaker/"
REL = "https://github.com/k2-fsa/sherpa-onnx/releases/download/speaker-recongition-models/"
MODELS = {"campplus": "3dspeaker_speech_campplus_sv_zh_en_16k-common_advanced.onnx",
          "eres2netv2": "3dspeaker_speech_eres2netv2_sv_zh-cn_16k-common.onnx",
          "eres2net": "3dspeaker_speech_eres2net_base_sv_zh-cn_3dspeaker_16k.onnx"}
pj = json.load(open(f"{W}/project.json")); enr = json.load(open(f"{W}/enroll.json"))
speech = json.load(open(f"{W}/speech.json"))
rare = set(pj.get("rare", [])); only_in = pj.get("only_in", {})
with wave.open(f"{W}/audio/raw16.wav") as f:
    A = np.frombuffer(f.readframes(f.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0

def extractor(name):
    p = MD + MODELS[name]
    if not os.path.exists(p): os.makedirs(MD, exist_ok=True); urllib.request.urlretrieve(REL + MODELS[name], p)
    return sherpa_onnx.SpeakerEmbeddingExtractor(sherpa_onnx.SpeakerEmbeddingExtractorConfig(model=p, num_threads=8))

def emb(ex, s, e):
    st = ex.create_stream(); st.accept_waveform(16000, A[int(s * 16000):int(e * 16000)]); st.input_finished()
    v = np.array(ex.compute(st)); return v / np.linalg.norm(v)

def span_emb(ex, s, e):
    vs = []; t = s
    while t + 0.8 <= e:
        vs.append(emb(ex, t, min(e, t + 2.0))); t += 0.75
        if t + 2.0 > e and t < e - 0.8: vs.append(emb(ex, max(s, e - 2.0), e)); break
    if not vs: return None
    m = np.mean(vs, axis=0); return m / np.linalg.norm(m)

def allowed_at(k, t):
    if k in rare: return False
    if k in only_in: return any(a <= t <= b for a, b in only_in[k])
    return True

# 1. choose the voice model
samples = [(k, s, e) for k, v in enr.items() for s, e in v]
if CHOICE == "auto":
    scores = {}
    for name in MODELS:
        ex = extractor(name); E = [span_emb(ex, s, e) for _, s, e in samples]
        ok = n = 0
        for i, ((k, s, e), v) in enumerate(zip(samples, E)):
            if v is None or k in rare: continue
            cents = {}
            for j, ((k2, _, _), v2) in enumerate(zip(samples, E)):
                if j != i and v2 is not None: cents.setdefault(k2, []).append(v2)
            sc = {k2: float((np.mean(vs, 0) / np.linalg.norm(np.mean(vs, 0))) @ v) for k2, vs in cents.items() if allowed_at(k2, (s + e) / 2)}
            if sc: n += 1; ok += max(sc, key=sc.get) == k
        scores[name] = ok / max(1, n); print(f"  {name:11s} leave-one-out accuracy {ok}/{n} = {100 * ok / max(1, n):.1f}%")
    CHOICE = max(scores, key=scores.get)
print("voice model:", CHOICE)

# 2. window scores
ex = extractor(CHOICE)
names = [k for k in enr if enr[k]]
C = []
for k in names:
    vs = [v for v in (span_emb(ex, s, e) for s, e in enr[k]) if v is not None]
    c = np.mean(vs, 0); C.append(c / np.linalg.norm(c))
C = np.stack(C)
F = 0.25; n = int(len(A) / 16000 / F) + 1
acc = np.zeros((n, len(names))); cnt = np.zeros(n)
for s, e in speech:
    if e - s < 0.8: continue
    starts = [s] if e - s <= 2.0 else list(np.arange(s, e - 2.0 + 1e-6, 0.5)) + [e - 2.0]
    for t in starts:
        sc = C @ emb(ex, t, min(e, t + 2.0)); a, b = int(t / F), int(min(e, t + 2.0) / F)
        acc[a:b] += sc; cnt[a:b] += 1

# 3. frame labels under the rules (pinned stretches are applied later, at line building)
segs = []
for i in range(n):
    if cnt[i] == 0: continue
    t = i * F + F / 2; sc = acc[i] / cnt[i]
    ok = [j for j, k in enumerate(names) if allowed_at(k, t)]
    if not ok: continue
    o = sorted(ok, key=lambda j: -sc[j]); lab = names[o[0]]; mg = float(sc[o[0]] - sc[o[1]]) if len(o) > 1 else 1.0
    if segs and segs[-1]["spk"] == lab and abs(segs[-1]["e"] - i * F) < 1e-6: segs[-1]["e"] = round((i + 1) * F, 2); segs[-1]["ms"].append(mg)
    else: segs.append({"s": round(i * F, 2), "e": round((i + 1) * F, 2), "spk": lab, "ms": [mg]})
for x in segs: x["m"] = round(float(np.mean(x.pop("ms"))), 3)
json.dump(segs, open(f"{W}/voices.json", "w"))
print("voices.json:", len(segs), "segments")
