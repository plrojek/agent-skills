"""Check rendered loops. Per file: codec, profile, level, pix_fmt, colour tags, frames, duration, audio, size,
B-frames, MP4 edit list, the loop seam and the largest step between neighbouring frames.

usage: qa.py <dir with .mp4>      (needs ffmpeg/ffprobe, numpy)
PASS: High profile, level 5.1 (5.2 when W*H/256*fps > 983040), yuv420p, bt709 x3, no audio, b_frames=0, no edit list
offset, and a seam about as small as a normal frame step (a large seam means some period does not divide the loop)."""
import json, pathlib, re, subprocess, sys
from fractions import Fraction
import numpy as np
OUT = pathlib.Path(sys.argv[1]).resolve()
def frame(f, n, W, H):
    raw = subprocess.run(['ffmpeg', '-loglevel', 'error', '-i', str(f), '-vf', f'select=eq(n\\,{n})', '-vframes', '1', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(H, W, 3).astype(np.int16)
bad = 0
for f in sorted(OUT.glob('*.mp4')):
    p = json.loads(subprocess.run(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(f)], capture_output=True, text=True).stdout)
    v = [s for s in p['streams'] if s['codec_type'] == 'video'][0]; na = sum(s['codec_type'] == 'audio' for s in p['streams'])
    W, H, N = v['width'], v['height'], int(v['nb_frames']); fps = float(Fraction(v['r_frame_rate']))
    trace = subprocess.run(['ffprobe', '-v', 'trace', str(f)], capture_output=True, text=True).stderr
    elst = [int(m) for m in re.findall(r'media time[:=]\s*(-?\d+)', trace)]
    d = lambda a, b: float(np.abs(frame(f, a, W, H) - frame(f, b, W, H)).mean())
    seam = d(N - 1, 0); step = max(d(i, i + 1) for i in range(0, N - 1, max(1, N // 6)))
    want_lvl = 52 if W * H / 256 * fps > 983040 else 51
    ok = (v['profile'] == 'High' and v['level'] == want_lvl and v['pix_fmt'] == 'yuv420p' and v.get('color_primaries') == 'bt709'
          and v.get('color_transfer') == 'bt709' and v.get('color_space') == 'bt709' and na == 0 and int(v.get('has_b_frames', 0)) == 0
          and all(e == 0 for e in elst) and seam <= max(4.0, 2 * step))
    bad += not ok
    print(f'{"PASS" if ok else "FAIL"} {f.name}: {W}x{H} {v["codec_name"]} {v["profile"]} L{v["level"]} {v["pix_fmt"]} '
          f'{v.get("color_primaries")}/{v.get("color_transfer")}/{v.get("color_space")} {v["r_frame_rate"]} frames={N} '
          f'dur={float(p["format"]["duration"]):.2f}s audio={na} b_frames={v.get("has_b_frames")} elst={elst or "none"} '
          f'size={f.stat().st_size / 1e6:.1f}MB seam={seam:.2f} step_max={step:.2f}')
sys.exit(1 if bad else 0)
