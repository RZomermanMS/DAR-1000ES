#!/bin/bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
R=hardware/pcb-redesign/v5/routing
P=$R/placement-loop
O=$P
if [ "${1:-}" = "--replay" ]; then
  O=$P/replay
  [ ! -e "$O" ] || { echo "replay exists" >&2; exit 1; }
  mkdir "$O"
elif [ "$#" -ne 0 ]; then
  echo "usage: $0 [--replay]" >&2; exit 1
fi
[ ! -e "$O/result.kicad_pcb" ] || { echo "output already exists" >&2; exit 1; }
sha256sum --check <<EOF
06f73f9b662897d0822611513cf09feb3f9ccb1c8e08e6cac4ecad31c147810c  $R/placement-integrated/result.kicad_pcb
c86217ae0f5bfc47f1a15b5cc06b149c8b6f91ff1359970723f73f63fbff52f5  $R/placement-integrated/result.kicad_pro
15ee74c9426113e6603fcf35236f98e3805705cdee1e75e3a9c440a81a5187a9  $R/placement-integrated/result.kicad_sch
5ba001041a5187bca6e25b80524eca8c94dce2dd9b673aea3b9d70a7978f8dd2  $R/placement-integrated/DAR-1000ES-v5-interlock.kicad_sch
730df9ec84cbfc407e9b01ef10a717fd13a1dfc760f410ef2fa1447507ee145a  $R/placement-integrated/DAR-1000ES-v5-power.kicad_sch
39f6b480dc92c14bb8df844b5c09d3353442cfb15d3120ba9c1413e3bde4af92  $R/placement-integrated/fp-lib-table
f8d977f8ef9686d6e21770e716e3b9c2f8e2ddf1f79bbca79b6432d5efe7aead  $R/placement-integrated/clearance.json
EOF
mkdir "$O/.build-work"
trap 'rm -rf "$O/.build-work" "$O/org.kicad.kicad"; rm -f "$O/"*.kicad_prl "$O/"*.lck' EXIT
cp "$R/placement-integrated/result.kicad_pro" "$R/placement-integrated/"*.kicad_sch "$O/"
cp "$R/placement-integrated/fp-lib-table" "$O/"
if [ "$O" != "$P" ]; then
  cp "$P/sym-lib-table" "$O/sym-lib-table"
  sed -i 's|../../DAR1000ES.pretty|../../../DAR1000ES.pretty|' "$O/fp-lib-table"
  sed -i 's|../../DAR1000ES.kicad_sym|../../../DAR1000ES.kicad_sym|' "$O/sym-lib-table"
  LIB_PATH=../../../DAR1000ES.kicad_sym
else
  LIB_PATH=../../DAR1000ES.kicad_sym
fi
grep -Fq '(uri "${KIPRJMOD}/'"$LIB_PATH"'")' "$O/sym-lib-table"
[ "$(realpath -e "$O/$LIB_PATH")" = "$(realpath -e hardware/pcb-redesign/v5/DAR1000ES.kicad_sym)" ]
IMAGE=kicad/kicad@sha256:165c81785b2df23a09892f4cc53bc0095a83b469bfbbe07989670d64049677a7
docker run --rm --network none --user "$(id -u):$(id -g)" \
  -e HOME="/work/$O/.build-work" -e TMPDIR="/work/$O/.build-work" \
  -e PYTHONDONTWRITEBYTECODE=1 -e OUTPUT_DIR="/work/$O" \
  -v "$PWD:/work:ro" -v "$PWD/$O:/work/$O:rw" -w /work \
  --entrypoint /bin/bash "$IMAGE" -c '
    set -euo pipefail
    R=hardware/pcb-redesign/v5/routing
    P=$R/placement-loop
    O=${OUTPUT_DIR#/work/}
    S=$R/placement-integrated/result.kicad_pcb
    /usr/bin/python3 "$P/test_transform.py"
    /usr/bin/python3 "$P/transform.py" "$S" "$O/result.kicad_pcb"
    if /usr/bin/python3 "$P/transform.py" "$O/result.kicad_pcb" "$O/.build-work/bad.kicad_pcb" 2>/dev/null; then
      echo "source hash guard failed" >&2; exit 1
    fi
    kicad-cli pcb drc --refill-zones --save-board --format json --severity-all --exit-code-violations -o "$O/drc.json" "$O/result.kicad_pcb"
    kicad-cli pcb drc --schematic-parity --format json --severity-all --exit-code-violations -o "$O/parity.json" "$O/result.kicad_pcb"
    /usr/bin/python3 "$P/audit.py"
    /usr/bin/python3 "$R/measure_tht_clearance.py" "$O/result.kicad_pcb" --threshold-mm 0.5 > "$O/clearance.json"
    /usr/bin/python3 "$R/pad-clearance-rework/compare.py" "$R/placement-integrated/clearance.json" "$O/clearance.json" > "$O/comparison.json"
    /usr/bin/python3 -c "import json,sys; c=json.load(open(sys.argv[1])); assert c[\"minimum_mm\"][1]>=c[\"minimum_mm\"][0] and c[\"pairs_below_0_3_mm\"][1]<=c[\"pairs_below_0_3_mm\"][0] and not c[\"worsened_under_0_3\"] and not c[\"entered_under_0_3\"]" "$O/comparison.json"
    /usr/bin/python3 "$R/decoupling-trial/crossings.py" "$O/result.kicad_pcb" > "$O/crossings.json"
    sha256sum "$O/result.kicad_pcb" > "$O/board.sha256"
    kicad-cli pcb drc --format json --severity-all --exit-code-violations -o "$O/verification-drc.json" "$O/result.kicad_pcb"
    sha256sum --check "$O/board.sha256"
  '
