#!/bin/bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
R=hardware/pcb-redesign/v5/routing
P=$R/placement-integrated
NAME=${1:-placement-integrated}
[[ "$NAME" =~ ^placement-integrated([_-][a-zA-Z0-9_-]+)?$ ]] || {
  echo "Output must be placement-integrated or a placement-integrated-NAME sibling" >&2; exit 1;
}
O=$R/$NAME
S=$R/integrated-review/clearance-first-corrected
C6=$R/placement-c6/result.kicad_pcb
IMAGE=kicad/kicad@sha256:165c81785b2df23a09892f4cc53bc0095a83b469bfbbe07989670d64049677a7
check() { echo "$1  $2" | sha256sum --check --status; }
check fb1f06735ecc218e2946121efeb44f91a6d88a2804b6029a4e8973fffa8e859e "$C6"
check c63fa89924e244bbf6bfd92f2c72e6c9d34117106b4bd87cf46f7971078920c5 "$S/result.kicad_pcb"
check 9b39d88bdaa1e6fb1a85d79803cdc88bf6968271ec6fe3afc315bed73a01f02b "$R/placement-controller/result.kicad_pcb"
check 1240e33f02655776918eeb6e967bab29241e4b5989a53370e44e0d4fd4a142b1 "$R/placement-audio/result.kicad_pcb"
check ecb68db85598d475af1b20ec5be40f3d330991a4b8ae8eb20d879b0d009dd67b "$R/placement-supervisor/result.kicad_pcb"
if [ "$O" != "$P" ]; then
  [ ! -e "$O" ] || { echo "Output directory exists: $O" >&2; exit 1; }
  mkdir "$O"
fi
for f in "$O/result.kicad_pcb" "$O/.work" "$O/drc.json"; do
  [ ! -e "$f" ] || { echo "Refusing existing output: $f" >&2; exit 1; }
done
mkdir -p "$O/.work" "$O/preview"
trap 'rm -rf "$O/.work" "$O/org.kicad.kicad"; rm -f "$O/"*.kicad_prl "$O/"*.lck' EXIT
cp "$C6" "$O/.work/source.kicad_pcb"
cp "$R/placement-c6/result.kicad_pro" "$R/placement-c6/"*.kicad_sch "$O/"
cp "$R/placement-c6/fp-lib-table" "$O/"
cp "$R/placement-c6/sym-lib-table" "$O/"
test -r "$O/../../DAR1000ES.kicad_sym"
docker run --rm --network none --user "$(id -u):$(id -g)" \
  -e HOME="/work/$O/.work" -e TMPDIR="/work/$O/.work" -e PYTHONDONTWRITEBYTECODE=1 \
  -e OUTPUT_DIR="/work/$O" -v "$PWD:/work:ro" -v "$PWD/$O:/work/$O:rw" \
  -w /work --entrypoint /bin/bash "$IMAGE" -c '
    set -euo pipefail
    R=hardware/pcb-redesign/v5/routing
    P=$R/placement-integrated
    O=${OUTPUT_DIR#/work/}
    S=$R/integrated-review/clearance-first-corrected/result.kicad_pcb
    /usr/bin/python3 "$P/controller.py" "$O/.work/source.kicad_pcb" "$O/.work/controller.kicad_pcb"
    /usr/bin/python3 "$P/verify_stage.py" "$O/.work/source.kicad_pcb" "$O/.work/controller.kicad_pcb" "$S" "$R/placement-controller/result.kicad_pcb"
    if /usr/bin/python3 "$P/controller.py" "$O/.work/controller.kicad_pcb" "$O/.work/repeated.kicad_pcb" 2>/dev/null; then
      echo "Controller replay guard failed" >&2; exit 1
    fi
    if /usr/bin/python3 "$P/audio.py" "$O/.work/controller.kicad_pcb" "$O/.work/bad-audio.kicad_pcb" wrong 2>/dev/null; then
      echo "Audio hash guard failed" >&2; exit 1
    fi
    H=$(sha256sum "$O/.work/controller.kicad_pcb" | cut -d" " -f1)
    /usr/bin/python3 "$P/audio.py" "$O/.work/controller.kicad_pcb" "$O/.work/audio.kicad_pcb" "$H"
    /usr/bin/python3 "$P/verify_stage.py" "$O/.work/controller.kicad_pcb" "$O/.work/audio.kicad_pcb" "$S" "$R/placement-audio/result.kicad_pcb"
    H=$(sha256sum "$O/.work/audio.kicad_pcb" | cut -d" " -f1)
    if /usr/bin/python3 "$P/supervisor.py" "$O/.work/audio.kicad_pcb" "$O/.work/bad-supervisor.kicad_pcb" wrong 2>/dev/null; then
      echo "Supervisor hash guard failed" >&2; exit 1
    fi
    /usr/bin/python3 "$P/supervisor.py" "$O/.work/audio.kicad_pcb" "$O/result.kicad_pcb" "$H"
    /usr/bin/python3 "$P/verify_stage.py" "$O/.work/audio.kicad_pcb" "$O/result.kicad_pcb" "$S" "$R/placement-supervisor/result.kicad_pcb"
    cp "$R/placement-c6/result.kicad_pro" "$O/result.kicad_pro"
    kicad-cli pcb drc --refill-zones --save-board --format json --severity-all --exit-code-violations -o "$O/drc.json" "$O/result.kicad_pcb"
    kicad-cli pcb drc --schematic-parity --format json --severity-all --exit-code-violations -o "$O/parity.json" "$O/result.kicad_pcb"
    /usr/bin/python3 "$P/audit.py"
    /usr/bin/python3 "$R/measure_tht_clearance.py" "$O/result.kicad_pcb" --threshold-mm 0.5 > "$O/clearance.json"
    /usr/bin/python3 "$R/pad-clearance-rework/compare.py" "$R/placement-c6/clearance.json" "$O/clearance.json" > "$O/comparison.json"
    /usr/bin/python3 "$R/decoupling-trial/crossings.py" "$O/result.kicad_pcb" > "$O/crossings.json"
    /usr/bin/python3 "$P/preview/generate.py"
    sha256sum "$O/result.kicad_pcb" > "$O/board.sha256"
    kicad-cli pcb drc --format json --severity-all --exit-code-violations -o "$O/verification-drc.json" "$O/result.kicad_pcb"
    sha256sum --check "$O/board.sha256"
  '
