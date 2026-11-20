#!/bin/bash
set -euo pipefail
ROOT=$(git rev-parse --show-toplevel)
cd "$ROOT"
R=hardware/pcb-redesign/v5/routing
P=$R/integrated-review/clearance-first-corrected
IMAGE=kicad/kicad@sha256:165c81785b2df23a09892f4cc53bc0095a83b469bfbbe07989670d64049677a7
sha256sum --check "$P/inputs.sha256"
for f in clearance.kicad_pcb power.kicad_pcb silk.kicad_pcb result.kicad_pcb org.kicad.kicad; do
  if [ -e "$P/$f" ]; then echo "Refusing existing $P/$f" >&2; exit 1; fi
done
docker run --rm --network none --user "$(id -u):$(id -g)" \
  -e HOME=/nonexistent -e TMPDIR="/work/$P" -e PYTHONDONTWRITEBYTECODE=1 \
  -v "$ROOT:/work:ro" -v "$ROOT/$P:/work/$P:rw" -w /work \
  --entrypoint /bin/bash "$IMAGE" -c '
    set -euo pipefail
    R=hardware/pcb-redesign/v5/routing
    P=$R/integrated-review/clearance-first-corrected
    V=hardware/pcb-redesign/v5
    trap '\''rm -rf "$P/org.kicad.kicad"; rm -f "$P/"*.kicad_prl "$P/clearance.kicad_pro" "$P/power.kicad_pro" "$P/silk.kicad_pro" "$P/clearance.kicad_pcb" "$P/power.kicad_pcb" "$P/silk.kicad_pcb"'\'' EXIT
    /usr/bin/python3 "$R/pad-clearance-rework/apply.py" \
      "$R/decoupling-trial/result.kicad_pcb" "$P/clearance.kicad_pcb"
    cmp "$P/clearance.kicad_pcb" "$R/pad-clearance-rework/result.kicad_pcb"
    /usr/bin/python3 -c "
import importlib.util
from pathlib import Path
spec = importlib.util.spec_from_file_location(\"power\", \"$R/power-rework/generate.py\")
power = importlib.util.module_from_spec(spec)
spec.loader.exec_module(power)
power.SOURCE = Path(\"$P/clearance.kicad_pcb\")
power.OUTPUT = Path(\"$P/power.kicad_pcb\")
power.main()
"
    /usr/bin/python3 "$R/silk-rework/apply_silk.py" \
      "$P/power.kicad_pcb" "$P/silk.kicad_pcb" "$V/DAR-1000ES-v5.net.xml"
    /usr/bin/python3 "$P/repair.py" "$P/silk.kicad_pcb" "$P/result.kicad_pcb"
    /usr/bin/python3 "$P/test_repair.py" "$P/silk.kicad_pcb" "$P/result.kicad_pcb"
    # SaveBoard can synthesize a default same-stem project; restore the actual rules.
    cp "$R/power-rework/result.kicad_pro" "$P/result.kicad_pro"
    set +e
    kicad-cli pcb drc --refill-zones --save-board --format json --severity-all \
      --exit-code-violations -o "$P/drc.json" "$P/result.kicad_pcb"
    drc=$?
    kicad-cli pcb drc --schematic-parity --format json --severity-all \
      --exit-code-violations -o "$P/parity.json" "$P/result.kicad_pcb"
    parity=$?
    set -e
    /usr/bin/python3 "$P/audit.py"
    /usr/bin/python3 -c "
import importlib.util
from pathlib import Path
spec = importlib.util.spec_from_file_location(\"power_audit\", \"$R/power-rework/audit.py\")
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)
audit.BOARD = Path(\"$P/result.kicad_pcb\")
audit.HERE = Path(\"$P\")
audit.main()
"
    /usr/bin/python3 "$R/decoupling-trial/crossings.py" "$P/result.kicad_pcb" > "$P/crossings.json"
    /usr/bin/python3 "$R/measure_tht_clearance.py" "$P/result.kicad_pcb" \
      --threshold-mm 0.5 > "$P/clearance.json"
    /usr/bin/python3 "$R/pad-clearance-rework/compare.py" \
      "$R/pad-clearance-rework/clearance.json" "$P/clearance.json" > "$P/comparison.json"
    /usr/bin/python3 "$R/pad-clearance-rework/compare.py" \
      "$R/decoupling-trial/tht-clearance.json" "$P/clearance.json" > "$P/baseline-comparison.json"
    /usr/bin/python3 "$P/preview/generate.py"
    printf "{\"drc\":%s,\"parity\":%s}\n" "$drc" "$parity" > "$P/check-exits.json"
  '
sha256sum --check "$P/inputs.sha256"
python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); sys.exit(1 if d["drc"] or d["parity"] else 0)' "$P/check-exits.json"
