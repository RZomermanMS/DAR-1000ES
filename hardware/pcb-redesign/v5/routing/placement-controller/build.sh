#!/bin/bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
P=hardware/pcb-redesign/v5/routing/placement-controller
S=${1:-hardware/pcb-redesign/v5/routing/integrated-review/clearance-first-corrected/result.kicad_pcb}
STEM=${2:-result}
if [[ ! "$STEM" =~ ^[a-zA-Z0-9_-]+$ ]] || [ ! -f "$S" ]; then
  echo "Usage: $0 [source-board-relative-to-root] [new-output-stem]" >&2
  exit 1
fi
case "$(realpath "$S")" in "$(pwd)"/*) ;; *) echo "source must be inside repository" >&2; exit 1;; esac
for f in "$P/$STEM.kicad_pcb" "$P/$STEM.kicad_pro" "$P/$STEM.kicad_sch" \
  "$P/$STEM-drc.json" "$P/$STEM-parity.json" "$P/$STEM-audit.json" \
  "$P/$STEM-clearance.json" "$P/$STEM-verify-drc.json" "$P/$STEM-sha256.txt" \
  "$P/.kicad-home" "$P/org.kicad.kicad"; do
  [ ! -e "$f" ] || { echo "Refusing existing $f" >&2; exit 1; }
done
mkdir "$P/.kicad-home"
trap 'rm -rf "$P/.kicad-home" "$P/org.kicad.kicad"; rm -f "$P/"*.kicad_prl' EXIT
IMAGE=kicad/kicad@sha256:165c81785b2df23a09892f4cc53bc0095a83b469bfbbe07989670d64049677a7
docker run --rm --network none --user "$(id -u):$(id -g)" \
  -e HOME="/work/$P/.kicad-home" -e TMPDIR="/work/$P" -e PYTHONDONTWRITEBYTECODE=1 \
  -e SOURCE="$S" -e STEM="$STEM" -v "$PWD:/work:ro" -v "$PWD/$P:/work/$P:rw" \
  -w /work --entrypoint /bin/bash "$IMAGE" -c '
    set -euo pipefail
    P=hardware/pcb-redesign/v5/routing/placement-controller
    B=hardware/pcb-redesign/v5/routing/integrated-review/clearance-first-corrected
    for test in test_replay_and_refuse_reapplication test_incident_trace_mutation_rejected test_pad_geometry_mutation_rejected; do
      /usr/bin/python3 "$P/test_apply.py" "ReplayTests.$test"
    done
    /usr/bin/python3 "$P/apply.py" "$SOURCE" "$P/$STEM.kicad_pcb"
    cp "$B/result.kicad_pro" "$P/$STEM.kicad_pro"
    cp "$B/result.kicad_sch" "$P/$STEM.kicad_sch"
    kicad-cli pcb drc --refill-zones --save-board --format json --severity-all \
      --exit-code-violations -o "$P/$STEM-drc.json" "$P/$STEM.kicad_pcb"
    kicad-cli pcb drc --schematic-parity --format json --severity-all \
      --exit-code-violations -o "$P/$STEM-parity.json" "$P/$STEM.kicad_pcb"
    /usr/bin/python3 "$P/audit.py" "$SOURCE" "$P/$STEM.kicad_pcb"
    /usr/bin/python3 hardware/pcb-redesign/v5/routing/measure_tht_clearance.py \
      "$P/$STEM.kicad_pcb" --threshold-mm 0.5 > "$P/$STEM-clearance.json"
    before=$(sha256sum "$P/$STEM.kicad_pcb" | cut -d" " -f1)
    kicad-cli pcb drc --format json --severity-all --exit-code-violations \
      -o "$P/$STEM-verify-drc.json" "$P/$STEM.kicad_pcb"
    after=$(sha256sum "$P/$STEM.kicad_pcb" | cut -d" " -f1)
    [ "$before" = "$after" ]
    printf "source " > "$P/$STEM-sha256.txt"
    sha256sum "$SOURCE" >> "$P/$STEM-sha256.txt"
    printf "saved-board-before-and-after-read-only-drc %s\n" "$after" >> "$P/$STEM-sha256.txt"
  '
