#!/bin/bash
# Preview a 3840x1646 header video exactly as an iPhone shows it: crop the measured window (full height, x 672-3168),
# overlay the status bar, Dynamic Island and the App Store buttons. Writes <stem>-iphone.mp4 (small) and <stem>-iphone.gif.
# usage: iphone_preview.sh <header.mp4> <out_dir>
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd); in=$1; out=$2; stem=$(basename "${in%.*}"); mkdir -p "$out"
ov="$out/.iphone_overlay.png"
if [ ! -f "$ov" ]; then   # needs Pillow: system python3 first, then uv as a fallback
  python3 -I "$here/iphone_mock.py" --overlay "$ov" >/dev/null 2>&1 || uv run --with pillow python -I "$here/iphone_mock.py" --overlay "$ov" >/dev/null
fi
ffmpeg -loglevel error -y -i "$in" -i "$ov" -filter_complex "[0]crop=2496:1646:672:0[w];[w][1]overlay=0:0,scale=1248:-2:flags=lanczos,format=yuv420p" \
  -c:v libx264 -preset slow -crf 22 -bf 0 -movflags +faststart -an "$out/$stem-iphone.mp4"
ffmpeg -loglevel error -y -i "$out/$stem-iphone.mp4" -vf "fps=12,scale=560:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=160[p];[b][p]paletteuse=dither=bayer:bayer_scale=4" "$out/$stem-iphone.gif"
ls -la "$out/$stem-iphone.mp4" "$out/$stem-iphone.gif"
