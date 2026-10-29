# Specs, encoding and upload notes

## Apple's creative assets (header and search result, iOS/iPadOS 27 and later)

| Asset | Image | Video |
|---|---|---|
| Product page header | 21:9 at 3840×1646 (jpg/png), or a universal 16:9 at 5244×2950 (png) | 21:9 at 3840×1646, 30 or 60 fps, 5–30 s, .mov/.m4v/.mp4 |
| Search result | 3:2, min 1920×1280, max 3840×2560 (jpg/png), or the universal 16:9 png | 3:2, min 1920×1280, max 3840×2560, 30/60 fps, 5–30 s |

**Format rules:**
- Images have no alpha.
- Videos are muted by default and loop.
- The **poster frame is set in App Store Connect and cannot be changed after approval.**
- The universal 16:9 asset is image-only, so a video needs separate header (21:9) and search (3:2) files.

**Content rules:**
- No prices or discounts, URLs, copyright symbols, unverifiable claims, or other platforms' logos.
- Everything must suit a 4+ rating.
- Localize every language.

**Review and replacement:**
- Assets can be submitted on their own (Asset Library) and are reviewed against the latest app version.
- Replacing a live asset means a new review.

Check Apple's "Creative assets specifications" page before relying on these numbers; they were current in late 2026.

## Encoding (what `render.mjs` and `upload_copy.sh` do, and why)

| Setting | Value | Why |
|---|---|---|
| Codec / profile | H.264 High | universally accepted |
| Level | 5.1, or 5.2 when W×H/256×fps > 983,040 | the level limits the macroblock **rate**, not only the frame size. 3600×2400 at 30 fps = 1,012,500 MB/s, so it needs 5.2. 3840×2560 exceeds both levels' frame size, so use 3600×2400 for a 3:2 video |
| Pixel format | yuv420p, TV range | compatibility |
| Colour | BT.709 primaries/transfer/matrix in the container **and** the bitstream (`-bsf:v h264_metadata=colour_primaries=1:transfer_characteristics=1:matrix_coefficients=1`) | `-color_*` flags alone don't reach the H.264 VUI |
| RGB→YUV | `scale=out_color_matrix=bt709:out_range=tv` | otherwise the conversion defaults to BT.601 and colours shift |
| B-frames | **`-bf 0`** | B-frames make ffmpeg write an MP4 edit list (media time ≈2 frames). Players that loop by seeking (QuickTime, Quick Look) then flash black at every restart, though no frame is black |
| Audio | none (`-an`) | not needed. If an uploader insists on a track: `ffmpeg -i in.mp4 -f lavfi -i anullsrc=r=48000:cl=stereo -shortest -c:v copy -c:a aac -b:a 64k out.mp4` |
| Container | `+faststart` | the moov atom goes first |
| Master quality | `-preset slow -crf 16` | ~16–28 MB for 10 s at 3840×1646 |
| Upload copy | two-pass at ~7.2 Mbps, maxrate ×1.3 | ≤10 MB: some browser-automation upload paths cap files at 10 MB |

**Check a file by hand:**
- `ffprobe -v error -show_entries stream=profile,level,pix_fmt,color_primaries,color_transfer,color_space,has_b_frames f.mp4`
- `ffprobe -v trace f.mp4 2>&1 | grep 'media time'` must show 0.
- `scripts/qa.py` runs both checks plus the loop seam.

## Deterministic rendering

`render.mjs` loads the page and waits for fonts and images. It then pauses **all** animations (`document.getAnimations()`) and sets each one's `currentTime` for every frame. It screenshots at deviceScaleFactor 2 and pipes the PNGs to ffmpeg.

- **Speed:** rendering speed doesn't affect the result; frame N is always the same image.
- **Phase:** give each element its phase with a **negative** `animation-delay` (start − loop length). Every element is then mid-cycle from time 0, and the loop seam is clean.
- **Offset:** use `--offset` to start the video at a moment that makes a good first frame.
