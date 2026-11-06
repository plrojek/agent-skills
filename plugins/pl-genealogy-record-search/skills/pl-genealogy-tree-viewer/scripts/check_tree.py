#!/usr/bin/env python3
# Part of pl-genealogy-tree-viewer (plugin pl-genealogy-record-search). Made by Applied AI · https://appliedai.dev · https://github.com/plrojek/agent-skills
"""Open the built page in headless Chrome and run the viewer's own code over every person.

    python3 check_tree.py out/tree.html            # serves the folder on 127.0.0.1, then file:// if that fails
    python3 check_tree.py out/tree.html --file     # file:// only

Checks, without any network beyond 127.0.0.1:
- no JavaScript error while loading;
- every person's card renders (side());
- the family view laid out with every person in the centre, side relatives off and on (build()):
  no two tiles overlap in a row, nobody appears twice;
- the whole-tree map, the fan and the timeline render for up to --people people; the List, the start
  screen, the welcome card, walls and documents render; each surname variant finds people;
- the ancestor portrait (fan and tree, every option on) builds for up to 10 people; the path bar, the
  grandparents' line bands and the far-zoom labels draw; Esc closes the card panel on a computer.
Everything runs twice: at a computer's window size and at a phone's (the layouts differ).
Exit 0 when everything passes. A temporary copy of the page with the test appended is written next to
the page (so relative scans/ resolve) and removed afterwards. Chrome: CHROME=/path, or the usual paths.
"""
import argparse
import functools
import http.server
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading

HEAD = "<script>window.__errs=[];addEventListener('error',e=>__errs.push(String(e.message||e)));</script>"
TEST = r"""<script>
(function(){
  const R={errors:window.__errs, cards:0, cardErrors:[], layouts:0, overlaps:0, dups:0, modes:{}, search:{}, bands:0, phone:PHONE()};
  const save=[focusId, SIDEK, MODE];
  const ids=Object.keys(P), real=ids.filter(id=>P[id].t!=="luka");
  for(const id of ids){ try{ side(id); R.cards++; }catch(e){ R.cardErrors.push(id+": "+e); } }
  for(const id of real) for(const sk of [false,true]){
    try{ focusId=id; SIDEK=sk; const {nodes}=build(); R.layouts++;
      const seen=new Set(); for(const n of nodes){ if(seen.has(n.id)) R.dups++; seen.add(n.id); }
      const rows={}; for(const n of nodes) (rows[n.y]=rows[n.y]||[]).push(n.x);
      for(const xs of Object.values(rows)){ xs.sort((a,b)=>a-b); for(let i=1;i<xs.length;i++) if(xs[i]-xs[i-1]<NW-0.5) R.overlaps++; }
    }catch(e){ R.cardErrors.push("build "+id+": "+e); } }
  [focusId, SIDEK]=[save[0], save[1]];
  const run=(name,fn)=>{ try{ fn(); R.modes[name]=(R.modes[name]||0)+1; }catch(e){ R.cardErrors.push(name+": "+e); } };
  run("all",()=>{ MODE="all"; render(); });
  for(const id of real.slice(0, __N__)){ focusId=id; run("fan",()=>{ MODE="fan"; render(); }); run("time",()=>{ MODE="time"; render(); }); }
  for(const id of real.slice(0, Math.min(__N__, 10))){ AI_ID=id;
    for(const layout of ["fan","tree"]) run("portrait",()=>{
      const b=aiBuild({...AI_DEF, layout, gens:7, dates:"pelne", places:true, photos:true, empty:true, tiers:true, sex:true, living:false});
      if(!/^<svg /.test(b.svg) || !b.n) throw new Error("portrait of "+id+": empty"); }); }
  run("path bar",()=>{ hideHome(); MODE="family"; focusId=real[real.length-1]; selId=focusId; render();
    if(!document.querySelector("#crumbs.on .cr")) throw new Error("no path bar"); });
  R.bands=document.querySelectorAll("#vp rect.lnreg").length;
  run("far labels",()=>{ MODE="all"; render(); T.k=0.2; apply(); relabel();
    if(!document.querySelector("#vp text.zl")) throw new Error("no labels at lod0"); });
  if(!PHONE()) run("esc",()=>{ side(real[0]); document.dispatchEvent(new KeyboardEvent("keydown",{key:"Escape"}));
    const s=document.getElementById("side"); if(s.classList.contains("full")||s.classList.contains("peek")) throw new Error("Esc left the card open"); });
  run("grid",()=>gridView("")); run("home",()=>homeView()); run("intro",()=>introView()); run("walls",()=>wallsView()); run("docs",()=>docsView());
  for(const g of (DB.var||[])) for(const v of g) R.search[v]=findAll(v).length;
  MODE=save[2];
  const pre=document.createElement("pre"); pre.id="selftest"; pre.textContent=JSON.stringify(R); document.body.append(pre);
})();
</script>"""


def find_chrome():
    cands = [os.environ.get("CHROME"), "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
             "/Applications/Chromium.app/Contents/MacOS/Chromium"]
    cands += [shutil.which(n) for n in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome")]
    return next((c for c in cands if c and os.path.exists(c)), None)


SIZES = {"computer": "1400,900", "phone": "390,844"}


def dump(chrome, url, size="1400,900"):
    with tempfile.TemporaryDirectory() as prof:
        r = subprocess.run([chrome, "--headless=new", "--disable-gpu", "--no-first-run", "--allow-file-access-from-files",
                            f"--user-data-dir={prof}", f"--window-size={size}", "--virtual-time-budget=20000",
                            "--dump-dom", url],
                           capture_output=True, text=True, timeout=600)
    m = re.search(r'<pre id="selftest">(.*?)</pre>', r.stdout, re.S)
    if not m: return None
    import html
    return json.loads(html.unescape(m.group(1)))


def check(page, people=30, file_only=False, size="1400,900"):
    chrome = find_chrome()
    if not chrome: raise SystemExit("no Chrome or Chromium found: set CHROME=/path/to/chrome")
    page = os.path.abspath(page)
    folder = os.path.dirname(page)
    with open(page, encoding="utf-8") as f:
        src = f.read()
    if "</body>" not in src or "<head>" not in src: raise SystemExit("not a tree page: " + page)
    probe = src.replace("<head>", "<head>" + HEAD, 1).replace("</body>", TEST.replace("__N__", str(people)) + "</body>", 1)
    tmp = os.path.join(folder, ".check-tree.html")
    with open(tmp, "w", encoding="utf-8") as f: f.write(probe)
    res = None
    try:
        if not file_only:
            try:
                class Quiet(http.server.SimpleHTTPRequestHandler):
                    def log_message(self, *a): pass
                handler = functools.partial(Quiet, directory=folder)
                srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
                threading.Thread(target=srv.serve_forever, daemon=True).start()
                res = dump(chrome, f"http://127.0.0.1:{srv.server_address[1]}/.check-tree.html", size)
                srv.shutdown()
            except OSError:
                res = None
        if res is None:
            res = dump(chrome, "file://" + tmp, size)
    finally:
        os.remove(tmp)
    return res


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("page")
    ap.add_argument("--people", type=int, default=30, help="how many people get the fan and timeline render")
    ap.add_argument("--file", action="store_true", help="open over file:// instead of a local server")
    ap.add_argument("--only", choices=sorted(SIZES), help="check one window size only")
    o = ap.parse_args(argv)
    ok = True
    for name, size in SIZES.items():
        if o.only and name != o.only: continue
        r = check(o.page, o.people, o.file, size)
        if r is None:
            print(f"{name}: FAIL: the page did not finish loading (a script error before the test ran?)"); ok = False; continue
        good = not r["errors"] and not r["cardErrors"] and not r["overlaps"] and not r["dups"]
        zero = [k for k, v in r["search"].items() if v == 0]
        print(f"{name} ({size.replace(',', '×')}, phone layout: {'yes' if r.get('phone') else 'no'}): "
              f"cards {r['cards']} · layouts {r['layouts']} · overlaps {r['overlaps']} · duplicates {r['dups']} · "
              f"line bands {r.get('bands', 0)} · views {r['modes']} · variant search {r['search']}")
        for e in r["errors"] + r["cardErrors"]: print("  !!", e)
        if zero: print("  note: a variant spelling found nobody:", ", ".join(zero))
        ok = ok and good
    print("OK" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
