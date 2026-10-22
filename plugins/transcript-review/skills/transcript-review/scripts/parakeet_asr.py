# NVIDIA Parakeet-TDT-0.6B-v3 (MLX build, 25 European languages) on the chunk WAVs.
# Used for precise word timings and as a second opinion for flagging - not for the text itself.
# usage (via tr.py asr): python parakeet_asr.py <workdir> <variant raw|flt>
import json, os, sys
from parakeet_mlx import from_pretrained

W, V = sys.argv[1:3]
out = f"{W}/asr/parakeet__{V}.json"
meta = json.load(open(f"{W}/chunks/chunks.json"))
model = from_pretrained("mlx-community/parakeet-tdt-0.6b-v3")
res = json.load(open(out))["chunks"] if os.path.exists(out) else {}
for m in meta:
    if str(m["i"]) in res: continue
    r = model.transcribe(f"{W}/chunks/{V}/c{m['i']:03d}.wav")
    words = []
    for sent in r.sentences:
        for tok in sent.tokens:
            conf = getattr(tok, "confidence", None)
            if tok.text.startswith(" ") or not words:
                words.append([tok.text.strip(), m["s"] + tok.start, m["s"] + tok.end, conf if conf is not None else 1.0])
            else:
                words[-1][0] += tok.text; words[-1][2] = m["s"] + tok.end
                if conf is not None: words[-1][3] = min(words[-1][3], conf)
    res[str(m["i"])] = [w for w in words if w[0]]
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump({"chunks": res}, open(out, "w"), ensure_ascii=False)
print("parakeet__" + V, sum(len(v) for v in res.values()), "words")
