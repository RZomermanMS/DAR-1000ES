#!/bin/bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
R=hardware/pcb-redesign/v5/routing
P=$R/placement-clearance
NAME=${1:-placement-clearance}
[[ "$NAME" =~ ^placement-clearance([_-][a-zA-Z0-9_-]+)?$ ]] || {
  echo "Output must be placement-clearance or a placement-clearance-NAME sibling" >&2; exit 1;
}
O=$R/$NAME
S=$R/placement-integrated
IMAGE=kicad/kicad@sha256:165c81785b2df23a09892f4cc53bc0095a83b469bfbbe07989670d64049677a7
echo "06f73f9b662897d0822611513cf09feb3f9ccb1c8e08e6cac4ecad31c147810c  $S/result.kicad_pcb" | sha256sum --check
if [ "$O" != "$P" ]; then
  [ ! -e "$O" ] || { echo "Output already exists: $O" >&2; exit 1; }
fi
for f in "$O/result.kicad_pcb" "$O/drc.json" "$O/.work"; do
  [ ! -e "$f" ] || { echo "Refusing existing output: $f" >&2; exit 1; }
done
mkdir -p "$O/.work" "$O/preview"
trap 'rm -rf "$O/.work" "$O/org.kicad.kicad"; rm -f "$O/"*.kicad_prl "$O/"*.lck' EXIT
cp "$S/result.kicad_pro" "$S/"*.kicad_sch "$S/fp-lib-table" "$S/sym-lib-table" "$O/"
docker run --rm --network none --user "$(id -u):$(id -g)" \
  -e HOME="/work/$O/.work" -e TMPDIR="/work/$O/.work" -e PYTHONDONTWRITEBYTECODE=1 \
  -e OUTPUT_DIR="/work/$O" -v "$PWD:/work:ro" -v "$PWD/$O:/work/$O:rw" \
  -w /work --entrypoint /bin/bash "$IMAGE" -c '
    set -euo pipefail
    R=hardware/pcb-redesign/v5/routing
    P=$R/placement-clearance
    S=$R/placement-integrated
    O=${OUTPUT_DIR#/work/}
    /usr/bin/python3 "$P/apply.py" "$S/result.kicad_pcb" "$O/result.kicad_pcb"
    if /usr/bin/python3 "$P/apply.py" "$O/result.kicad_pcb" "$O/.work/duplicate.kicad_pcb" 2>/dev/null; then
      echo "Source hash guard failed" >&2; exit 1
    fi
    kicad-cli pcb drc --refill-zones --save-board --format json --severity-all --exit-code-violations -o "$O/drc.json" "$O/result.kicad_pcb"
    kicad-cli pcb drc --schematic-parity --format json --severity-all --exit-code-violations -o "$O/parity.json" "$O/result.kicad_pcb"
    /usr/bin/python3 "$P/audit.py"
    /usr/bin/python3 "$R/measure_tht_clearance.py" "$O/result.kicad_pcb" --threshold-mm 0.5 > "$O/clearance.json"
    /usr/bin/python3 "$R/pad-clearance-rework/compare.py" "$S/clearance.json" "$O/clearance.json" > "$O/comparison.json"
    /usr/bin/python3 "$P/check_comparison.py" "$O/comparison.json"
    /usr/bin/python3 "$R/decoupling-trial/crossings.py" "$O/result.kicad_pcb" > "$O/crossings.json"
    /usr/bin/python3 "$P/preview/generate.py"
    sha256sum "$O/result.kicad_pcb" > "$O/board.sha256"
    kicad-cli pcb drc --format json --severity-all --exit-code-violations -o "$O/verification-drc.json" "$O/result.kicad_pcb"
    sha256sum --check "$O/board.sha256"
  '
