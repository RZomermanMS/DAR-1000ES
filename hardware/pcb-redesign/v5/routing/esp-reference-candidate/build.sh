#!/bin/bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
R=hardware/pcb-redesign/v5/routing
P=$R/esp-reference-candidate
S=$R/esp-edge-candidate
NAME=${1:?usage: build.sh esp-reference-candidate-REPLAY}
[[ "$NAME" =~ ^esp-reference-candidate-[a-zA-Z0-9_-]+$ ]] || { echo "Invalid replay name" >&2; exit 1; }
O=$R/$NAME
[ ! -e "$O" ] || { echo "Output already exists" >&2; exit 1; }
sha256sum --check <<EOF
5673845460e297290b65e6abe500a5d0790fd1cf6a52cc6211d78d1d00863e8b  $S/result.kicad_pcb
c86217ae0f5bfc47f1a15b5cc06b149c8b6f91ff1359970723f73f63fbff52f5  $S/result.kicad_pro
EOF
mkdir -p "$O/.work" "$O/preview"
trap 'rm -rf "$O/.work"; rm -f "$O/"*.kicad_prl' EXIT
cp "$P/"{correct.py,audit.py,verify.py,render.py} "$O/"
cp "$S/result.kicad_pro" "$S/"*.kicad_sch "$S/fp-lib-table" "$S/sym-lib-table" "$O/"
IMAGE=kicad/kicad@sha256:165c81785b2df23a09892f4cc53bc0095a83b469bfbbe07989670d64049677a7
run() {
  docker run --rm --network none --user "$(id -u):$(id -g)" \
    -e HOME="/work/$O/.work" -e TMPDIR="/work/$O/.work" -e PYTHONDONTWRITEBYTECODE=1 \
    -v "$PWD:/work:ro" -v "$PWD/$O:/work/$O:rw" -w /work --entrypoint "$1" "$IMAGE" "${@:2}"
}
run /usr/bin/python3 "$O/correct.py"
run /usr/bin/kicad-cli pcb drc --refill-zones --save-board --format json --severity-all \
  --exit-code-violations -o "$O/drc.json" "$O/result.kicad_pcb"
run /usr/bin/kicad-cli pcb drc --schematic-parity --format json --severity-all \
  --exit-code-violations -o "$O/parity.json" "$O/result.kicad_pcb"
run /usr/bin/python3 "$O/audit.py"
run /usr/bin/python3 "$O/verify.py"
run /usr/bin/python3 "$R/measure_tht_clearance.py" "$O/result.kicad_pcb" --threshold-mm 0.5 > "$O/clearance.json"
python3 - "$O/clearance.json" <<'PY'
import json, sys
report = json.load(open(sys.argv[1]))
assert report["minimum"]["clearance_mm"] >= .30
PY
run /usr/bin/python3 "$R/decoupling-trial/crossings.py" "$O/result.kicad_pcb" > "$O/crossings.json"
for plot in assembly front-copper back-copper; do
  case "$plot" in
    assembly) layers=F.SilkS,F.Fab,F.CrtYd,Edge.Cuts ;;
    front-copper) layers=F.Cu,Edge.Cuts ;;
    back-copper) layers=B.Cu,Edge.Cuts ;;
  esac
  run /usr/bin/kicad-cli pcb export pdf --mode-single --scale 0 --layers "$layers" \
    -o "$O/preview/$plot.pdf" "$O/result.kicad_pcb"
done
run /usr/bin/python3 "$O/render.py" "$O"
sha256sum "$O/result.kicad_pcb" > "$O/board.sha256"
run /usr/bin/kicad-cli pcb drc --format json --severity-all --exit-code-violations \
  -o "$O/verification-drc.json" "$O/result.kicad_pcb"
sha256sum --check "$O/board.sha256"
cmp "$S/result.kicad_pro" "$O/result.kicad_pro"
