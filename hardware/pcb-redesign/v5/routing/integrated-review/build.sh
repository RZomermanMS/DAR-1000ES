#!/bin/bash
set -euo pipefail

ROOT=$(git rev-parse --show-toplevel)
cd "$ROOT"
R=hardware/pcb-redesign/v5/routing
P=$R/integrated-review
V=hardware/pcb-redesign/v5
IMAGE=kicad/kicad@sha256:165c81785b2df23a09892f4cc53bc0095a83b469bfbbe07989670d64049677a7
sha256sum --check "$P/inputs.sha256"
if [ -e "$P/result.kicad_pcb" ]; then
    echo "Refusing to overwrite result.kicad_pcb; remove it from this candidate first." >&2
    exit 1
fi
if [ -e "$P/org.kicad.kicad" ]; then
    echo "Temporary KiCad directory already exists; inspect it first." >&2
    exit 1
fi

docker run --rm --network none --user "$(id -u):$(id -g)" \
  -e HOME=/nonexistent -e TMPDIR="/work/$P" -e PYTHONDONTWRITEBYTECODE=1 \
  -v "$ROOT:/work:ro" -v "$ROOT/$P:/work/$P:rw" -w /work \
  --entrypoint /bin/bash "$IMAGE" -c '
    set -euo pipefail
    R=hardware/pcb-redesign/v5/routing
    P=$R/integrated-review
    V=hardware/pcb-redesign/v5
    trap '\''rm -rf "$P/org.kicad.kicad"; rm -f "$P/result.kicad_prl"'\'' EXIT
    /usr/bin/python3 "$R/silk-rework/apply_silk.py" \
      "$R/power-rework/result.kicad_pcb" "$P/result.kicad_pcb" "$V/DAR-1000ES-v5.net.xml"
    kicad-cli pcb drc --refill-zones --save-board --format json --severity-all \
      --exit-code-violations -o "$P/drc.json" "$P/result.kicad_pcb"
    kicad-cli pcb drc --schematic-parity --format json --severity-all \
      --exit-code-violations -o "$P/parity.json" "$P/result.kicad_pcb"
    /usr/bin/python3 "$P/audit_integration.py"
    /usr/bin/python3 "$R/test_board_ops.py"
    /usr/bin/python3 "$R/decoupling-trial/test_measure_paths.py"
    /usr/bin/python3 "$R/test_measure_tht_clearance.py"
    /usr/bin/python3 -c "
import sys, unittest
from pathlib import Path
sys.path.insert(0, \"$R/power-rework\")
import test_audit
test_audit.audit.BOARD = Path(\"$P/result.kicad_pcb\")
suite = unittest.defaultTestLoader.loadTestsFromModule(test_audit)
if not unittest.TextTestRunner().run(suite).wasSuccessful():
    sys.exit(1)
"
    /usr/bin/python3 "$R/decoupling-trial/crossings.py" "$P/result.kicad_pcb" > "$P/crossings.json"
    /usr/bin/python3 "$R/measure_tht_clearance.py" "$P/result.kicad_pcb" \
      --threshold-mm 0.3 > "$P/tht-clearance.json"
    /usr/bin/python3 "$P/preview/generate.py"
    rm -f "$P/result.kicad_prl"
  '
sha256sum --check "$P/inputs.sha256"
