#!/bin/bash
set -euo pipefail
ROOT=$(git rev-parse --show-toplevel)
cd "$ROOT"
R=hardware/pcb-redesign/v5/routing
P=$R/placement-audio
S=$R/integrated-review/clearance-first-corrected
IMAGE=kicad/kicad@sha256:165c81785b2df23a09892f4cc53bc0095a83b469bfbbe07989670d64049677a7
sha256sum --check "$P/inputs.sha256"
if [ -e "$P/result.kicad_pcb" ]; then echo "Refusing existing result" >&2; exit 1; fi
cp "$S/result.kicad_pro" "$P/result.kicad_pro"
cp "$S/result.kicad_sch" "$S/DAR-1000ES-v5-interlock.kicad_sch" "$S/DAR-1000ES-v5-power.kicad_sch" "$P/"
cp "$R/decoupling-trial/fp-lib-table" "$P/fp-lib-table"
docker run --rm --network none --user "$(id -u):$(id -g)" \
  -e HOME=/nonexistent -e TMPDIR="/work/$P" -e PYTHONDONTWRITEBYTECODE=1 \
  -v "$ROOT:/work:ro" -v "$ROOT/$P:/work/$P:rw" -w /work \
  --entrypoint /bin/bash "$IMAGE" -c '
    set -euo pipefail
    R=hardware/pcb-redesign/v5/routing
    P=$R/placement-audio
    S=$R/integrated-review/clearance-first-corrected
    trap '\''rm -rf "$P/org.kicad.kicad"; rm -f "$P/"*.kicad_prl'\'' EXIT
    /usr/bin/python3 "$P/transform.py" "$S/result.kicad_pcb" "$P/result.kicad_pcb"
    /usr/bin/python3 "$P/test_transform.py" "$S/result.kicad_pcb" "$P/result.kicad_pcb"
    cp "$S/result.kicad_pro" "$P/result.kicad_pro"
    kicad-cli pcb drc --refill-zones --save-board --format json --severity-all \
      --exit-code-violations -o "$P/drc.json" "$P/result.kicad_pcb"
    kicad-cli pcb drc --schematic-parity --format json --severity-all \
      --exit-code-violations -o "$P/parity.json" "$P/result.kicad_pcb"
    /usr/bin/python3 "$P/audit.py"
    /usr/bin/python3 "$R/decoupling-trial/crossings.py" "$P/result.kicad_pcb" > "$P/crossings.json"
    /usr/bin/python3 "$R/measure_tht_clearance.py" "$P/result.kicad_pcb" \
      --threshold-mm 0.5 > "$P/clearance.json"
    /usr/bin/python3 "$R/pad-clearance-rework/compare.py" \
      "$S/clearance.json" "$P/clearance.json" > "$P/comparison.json"
    before=$(sha256sum "$P/result.kicad_pcb" | cut -d" " -f1)
    kicad-cli pcb drc --format json --severity-all --exit-code-violations \
      -o "$P/verification-drc.json" "$P/result.kicad_pcb"
    after=$(sha256sum "$P/result.kicad_pcb" | cut -d" " -f1)
    test "$before" = "$after"
    printf "{\"before\":\"%s\",\"after\":\"%s\"}\n" "$before" "$after" > "$P/verification.json"
  '
sha256sum "$P/result.kicad_pcb" > "$P/board.sha256"
