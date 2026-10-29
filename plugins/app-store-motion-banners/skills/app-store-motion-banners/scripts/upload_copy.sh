#!/bin/bash
# Make a <=10 MB copy of a master loop for browser uploads (the Chrome extension's file upload caps at 10 MB).
# Same specs as the master: H.264 High, level from the macroblock rate, BT.709 in container + bitstream, yuv420p,
# no B-frames (no MP4 edit list -> no black flash at the loop), faststart, no audio. Two-pass at a fixed bitrate.
# usage: upload_copy.sh <master.mp4> <out.mp4> [target_kbps=7200]
set -euo pipefail
in=$1; out=$2; kbps=${3:-7200}
IFS=x read W H <<<"$(ffprobe -v error -select_streams v -show_entries stream=width,height -of csv=p=0:s=x "$in")"
lvl=$(python3 -c "print('5.2' if $W*$H/256*30 > 983040 else '5.1')")
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
common=(-c:v libx264 -preset slow -b:v ${kbps}k -maxrate $((kbps*13/10))k -bufsize $((kbps*2))k -bf 0 -profile:v high -level "$lvl"
        -pix_fmt yuv420p -colorspace bt709 -color_primaries bt709 -color_trc bt709 -color_range tv
        -bsf:v h264_metadata=colour_primaries=1:transfer_characteristics=1:matrix_coefficients=1 -an)
ffmpeg -loglevel error -y -i "$in" "${common[@]}" -pass 1 -passlogfile "$tmp/p" -f mp4 /dev/null
ffmpeg -loglevel error -y -i "$in" "${common[@]}" -pass 2 -passlogfile "$tmp/p" -movflags +faststart "$out"
sz=$(wc -c < "$out" | tr -d " "); echo "$(basename "$out"): $((sz/1024)) KB"; [ "$sz" -le 10000000 ] || { echo "TOO BIG" >&2; exit 3; }
