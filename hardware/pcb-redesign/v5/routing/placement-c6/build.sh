#!/bin/bash
set -euo pipefail
ROOT=$(git rev-parse --show-toplevel)
cd "$ROOT"
R=hardware/pcb-redesign/v5/routing
P=$R/placement-c6
S=$R/integrated-review/clearance-first-corrected
IMAGE=kicad/kicad@sha256:165c81785b2df23a09892f4cc53bc0095a83b469bfbbe07989670d64049677a7
if [ -e "$P/result.kicad_pcb" ] || [ -e "$P/.work" ]; then
  echo "Remove the previous result and inspect/remove .work before rebuilding." >&2
  exit 1
fi
mkdir "$P/.work"
trap 'rm -rf "$P/.work" "$P/org.kicad.kicad"; rm -f "$P/"*.kicad_prl' EXIT
cp "$S/"*.kicad_sch "$S/result.kicad_pro" "$P/"
sed 's@../../../DAR1000ES.pretty@../../DAR1000ES.pretty@' "$S/fp-lib-table" > "$P/fp-lib-table"
docker run --rm --network none --user "$(id -u):$(id -g)" \
  -e HOME="/work/$P/.work" -e TMPDIR="/work/$P/.work" -e PYTHONDONTWRITEBYTECODE=1 \
  -v "$ROOT:/work:ro" -v "$ROOT/$P:/work/$P:rw" -w /work \
  --entrypoint /bin/bash "$IMAGE" -c '
    set -euo pipefail
    R=hardware/pcb-redesign/v5/routing
    P=$R/placement-c6
    S=$R/integrated-review/clearance-first-corrected
    /usr/bin/python3 "$P/test_generate.py"
    /usr/bin/python3 "$P/generate.py" "$S/result.kicad_pcb" "$P/result.kicad_pcb"
    cp "$S/result.kicad_pro" "$P/result.kicad_pro"
    kicad-cli pcb drc --refill-zones --save-board --format json --severity-all \
      --exit-code-violations -o "$P/drc.json" "$P/result.kicad_pcb"
    kicad-cli pcb drc --schematic-parity --format json --severity-all \
      --exit-code-violations -o "$P/parity.json" "$P/result.kicad_pcb"
    /usr/bin/python3 "$P/audit.py"
    /usr/bin/python3 "$R/measure_tht_clearance.py" "$P/result.kicad_pcb" \
      --threshold-mm 0.5 > "$P/clearance.json"
    /usr/bin/python3 "$R/pad-clearance-rework/compare.py" \
      "$S/clearance.json" "$P/clearance.json" > "$P/comparison.json"
    /usr/bin/python3 "$P/preview/generate.py"
    sha256sum "$P/result.kicad_pcb" > "$P/.work/before"
    kicad-cli pcb drc --format json --severity-all --exit-code-violations \
      -o "$P/verification-drc.json" "$P/result.kicad_pcb"
    sha256sum "$P/result.kicad_pcb" > "$P/.work/after"
    cmp "$P/.work/before" "$P/.work/after"
    cp "$P/.work/after" "$P/board.sha256"
  '
