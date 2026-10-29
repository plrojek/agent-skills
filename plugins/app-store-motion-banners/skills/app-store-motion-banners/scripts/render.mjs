// Render a page's CSS animations frame by frame into a seamless loop video (or stills).
// Deterministic: every animation is paused and seeked to each frame time, so the output never depends on speed.
// Output: H.264 High, level picked from the macroblock rate (5.1, or 5.2 above 983,040 MB/s), yuv420p, BT.709 in the
// container AND the bitstream, faststart, NO B-frames (B-frames make ffmpeg write an MP4 edit list, and players that
// loop by seeking then flash black at every restart), no audio.
// usage: node render.mjs <page.html> <cssW> <cssH> <out.mp4> [--offset s] [--dur 10] [--fps 30] [--dpr 2] [--stills t1,t2]
// Playwright: resolved from PW_FROM (path to a package.json that depends on playwright) or ./package.json.
// Browser: installed Google Chrome (PW_CHANNEL=chrome, default), falling back to Playwright's Chromium.
import { createRequire } from 'module';
import { spawn } from 'child_process';
import { pathToFileURL } from 'url';
import path from 'path';
const from = process.env.PW_FROM || path.join(process.cwd(), 'package.json');
let chromium;
try { ({ chromium } = createRequire(from)('playwright')); }
catch { console.error(`Playwright not found from ${from}. Run "npm i playwright" in the working folder, or set PW_FROM.`); process.exit(2); }
const [pagePath, W, H, out] = process.argv.slice(2);
const arg = (k, d) => { const i = process.argv.indexOf(k); return i > 0 ? process.argv[i + 1] : d; };
const OFFSET = parseFloat(arg('--offset', '0')), DUR = parseFloat(arg('--dur', '10')), FPS = parseInt(arg('--fps', '30')), DPR = parseFloat(arg('--dpr', '2'));
const stills = arg('--stills', '');
const browser = await chromium.launch({ channel: process.env.PW_CHANNEL || 'chrome' }).catch(() => chromium.launch());
const page = await browser.newPage({ viewport: { width: +W, height: +H }, deviceScaleFactor: DPR });
await page.goto(pathToFileURL(path.resolve(pagePath)).href, { waitUntil: 'networkidle' });
const info = await page.evaluate(async () => {
  await document.fonts.ready;
  await Promise.all([...document.images].map(i => i.decode().catch(() => 'bad')));
  const bad = [...document.images].filter(i => !i.naturalWidth).map(i => i.src);
  const fonts = [...document.fonts].filter(f => f.status === 'loaded').map(f => `${f.family} ${f.weight}`);
  document.getAnimations().forEach(a => a.pause());
  return { bad, fonts: [...new Set(fonts)], anims: document.getAnimations().length };
});
console.error(JSON.stringify(info));
if (info.bad.length) { console.error('missing images'); process.exit(2); }
const seek = t => page.evaluate(ms => { document.getAnimations().forEach(a => { a.currentTime = ms; }); }, t * 1000);
if (stills) {
  for (const t of stills.split(',').map(Number)) { await seek(t); await page.screenshot({ path: `${out}_t${t}.png` }); }
  await browser.close(); process.exit(0);
}
const pw = Math.round(+W * DPR), ph = Math.round(+H * DPR);
const level = pw * ph / 256 * FPS > 983040 ? '5.2' : '5.1';
const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'png', '-i', '-',
  '-vf', 'scale=out_color_matrix=bt709:out_range=tv,format=yuv420p',
  '-c:v', 'libx264', '-preset', 'slow', '-crf', '16', '-bf', '0', '-profile:v', 'high', '-level', level,
  '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-color_range', 'tv',
  '-bsf:v', 'h264_metadata=colour_primaries=1:transfer_characteristics=1:matrix_coefficients=1',
  '-movflags', '+faststart', '-an', out], { stdio: ['pipe', 'inherit', 'inherit'] });
const N = Math.round(DUR * FPS);
for (let i = 0; i < N; i++) {
  await seek(OFFSET + i / FPS);
  const buf = await page.screenshot({ type: 'png' });
  if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
  if (i % 30 === 29) process.stderr.write(`${i + 1}/${N}\r`);
}
ff.stdin.end();
await new Promise((res, rej) => ff.on('close', c => c ? rej(new Error('ffmpeg ' + c)) : res()));
await browser.close();
console.error(`done ${out} ${N} frames (level ${level})`);
