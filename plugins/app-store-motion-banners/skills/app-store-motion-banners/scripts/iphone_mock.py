"""Show a 3840x1646 header frame the way the App Store on an iPhone shows it (portrait product page).

Measured on a device screenshot (iOS App Store, 2026): the header shows the FULL video height and only the centre
~65% of its width (aspect ~1.52). In artboard CSS px (1920x823, rendered at 2x):
  window          x 336-1584, y 0-823    (393 pt wide -> 3.176 CSS px per pt)
  status bar      y 0-171 (54 pt); clock / battery glyphs y ~66-115
  Dynamic Island  x 760-1160, y 36-154
  back button     x 389-524,  y 186-327   (narrowest phones: to x 554)
  mute + share    x 1219-1533, y 186-327  (narrowest phones: from x 1147)
SAFE for anything readable: y >= 345 inside the window; hero motion in x 430-1490.

The clock and status icons turn dark when the top band of the frame is light, as iOS does.

usage: iphone_mock.py <frame.png> <out.png> [--guides]      one frame with overlays + the white store page below
       iphone_mock.py --overlay <out.png> [--frame <png>]   transparent overlay only (2496x1646) for ffmpeg; --frame picks
                                                            the glyph colour from a frame of the video"""
import sys
from PIL import Image, ImageDraw, ImageFont, ImageStat
A = sys.argv[1:]; OVERLAY = A[0] == '--overlay'; guides = '--guides' in A
src, out = (A[A.index('--frame') + 1] if '--frame' in A else None, A[1]) if OVERLAY else (A[0], A[1])
im = Image.open(src).convert('RGB') if src else Image.new('RGB', (3840, 1646))
if im.size != (3840, 1646): im = im.resize((3840, 1646), Image.LANCZOS)
S = im.width / 1920
X0, X1 = 336, 1584
win = im.crop((int(X0 * S), 0, int(X1 * S), im.height)); W, H = win.size; k = W / (X1 - X0)
def R(x0, y0, x1, y1): return [(x0 - X0) * k, y0 * k, (x1 - X0) * k, y1 * k]
light_top = ImageStat.Stat(win.crop((0, 0, W, int(171 * k))).convert('L')).mean[0] > 150
glyph = (20, 20, 20, 255) if light_top else (255, 255, 255, 255)
ov = Image.new('RGBA', win.size, (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
try: f = ImageFont.truetype('/System/Library/Fonts/SFNS.ttf', int(52 * k))
except Exception: f = ImageFont.load_default()
d.text(((395 - X0) * k, 62 * k), '9:41', font=f, fill=glyph)
d.rounded_rectangle(R(1440, 72, 1520, 108), radius=10 * k, fill=glyph)
d.rounded_rectangle(R(1330, 70, 1420, 110), radius=8 * k, fill=glyph[:3] + (230,))
d.rounded_rectangle(R(760, 36, 1160, 154), radius=59 * k, fill=(0, 0, 0, 255))                 # Dynamic Island
d.ellipse(R(389, 186, 524, 327), fill=(225, 238, 250, 215))                                   # back button
d.rounded_rectangle(R(1219, 186, 1533, 327), radius=70 * k, fill=(225, 238, 250, 215))       # mute + share
d.line([((468 - X0) * k, 230 * k), ((440 - X0) * k, 256 * k), ((468 - X0) * k, 282 * k)], fill=(20, 20, 20, 255), width=int(9 * k))
if guides:
    d.rectangle(R(336, 0, 1584, 171), outline=(255, 60, 60, 255), width=int(3 * k))
    d.line([(0, 345 * k), (W, 345 * k)], fill=(255, 220, 0, 255), width=int(3 * k))
    d.rectangle(R(430, 345, 1490, 815), outline=(0, 255, 120, 255), width=int(3 * k))
if OVERLAY:
    ov.save(out); print('wrote overlay', out, ov.size); sys.exit(0)
win = Image.alpha_composite(win.convert('RGBA'), ov).convert('RGB')
page = Image.new('RGB', (W, int(H * 1.32)), (255, 255, 255)); page.paste(win, (0, 0))
ImageDraw.Draw(page).rounded_rectangle([60 * k, H + 40 * k, 330 * k, H + 310 * k], radius=60 * k, fill=(200, 205, 215))
mask = Image.new('L', page.size, 0); ImageDraw.Draw(mask).rounded_rectangle([0, 0, page.width, page.height + 400], radius=int(170 * k), fill=255)
bg = Image.new('RGB', page.size, (30, 30, 30)); bg.paste(page, (0, 0), mask); bg.thumbnail((900, 900)); bg.save(out); print('wrote', out, bg.size)
