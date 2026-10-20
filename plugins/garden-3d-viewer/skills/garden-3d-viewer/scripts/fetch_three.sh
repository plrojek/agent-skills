#!/usr/bin/env bash
# Vendor three.js and the add-ons the viewer imports into <viewer-dir>/vendor.
#   bash fetch_three.sh <viewer-dir> [three-version]
# The add-ons import the bare specifier 'three'. Bare specifiers need an import map, and import
# maps are the one thing here some browsers refused, so each add-on is rewritten to import the
# vendored module by relative path. Re-run this script whenever you change the three.js version.
set -euo pipefail
DIR="${1:?usage: fetch_three.sh <viewer-dir> [version]}"
VER="${2:-0.180.0}"
BASE="https://cdn.jsdelivr.net/npm/three@${VER}"
V="$DIR/vendor"
mkdir -p "$V/addons/environments" "$V/addons/math" "$V/addons/postprocessing" "$V/addons/shaders"
curl -fsSL "$BASE/build/three.module.min.js" -o "$V/three.module.min.js"
curl -fsSL "$BASE/build/three.core.min.js"   -o "$V/three.core.min.js"
for f in environments/RoomEnvironment.js math/SimplexNoise.js \
         postprocessing/EffectComposer.js postprocessing/GTAOPass.js postprocessing/MaskPass.js \
         postprocessing/OutputPass.js postprocessing/Pass.js postprocessing/RenderPass.js postprocessing/ShaderPass.js \
         shaders/CopyShader.js shaders/GTAOShader.js shaders/OutputShader.js shaders/PoissonDenoiseShader.js; do
  curl -fsSL "$BASE/examples/jsm/$f" -o "$V/addons/$f"
  # 'three' -> the vendored build, two levels up from addons/<group>/
  sed -i.bak -E "s#from '(three)';#from '../../three.module.min.js';#" "$V/addons/$f" && rm -f "$V/addons/$f.bak"
done
if grep -rnE "^(import .*|\} )from '(three|three/[^']*)'" "$V/addons" ; then   # doc comments mention 'three/addons/…' — only real imports count
  echo "bare 'three' imports are left in the add-ons above — fix them before publishing" >&2; exit 1
fi
echo "three.js $VER vendored into $V ($(du -sh "$V" | cut -f1))"
