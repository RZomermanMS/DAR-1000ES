#!/bin/bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
R=hardware/pcb-redesign/v5/routing
P=$R/placement-current
S=$R/placement-integrated
NAME=${1:-placement-current}
[[ "$NAME" =~ ^placement-current([_-][a-zA-Z0-9_-]+)?$ ]] || {
  echo "Output must be placement-current or a placement-current-NAME sibling" >&2; exit 1;
}
O=$R/$NAME
IMAGE=kicad/kicad@sha256:165c81785b2df23a09892f4cc53bc0095a83b469bfbbe07989670d64049677a7
sha256sum --check <<EOF
06f73f9b662897d0822611513cf09feb3f9ccb1c8e08e6cac4ecad31c147810c  $S/result.kicad_pcb
c1bb512a1d64567e40e9b5d1b4575b3344dc071ce7f61d6110152f85d02a7dfe  $R/placement-loop/result.kicad_pcb
943231dff205f6002cc8ae35e5011da886671f8ab1f16bf03c6b5b88d6374de3  $R/placement-clearance/result.kicad_pcb
f8d977f8ef9686d6e21770e716e3b9c2f8e2ddf1f79bbca79b6432d5efe7aead  $S/clearance.json
c86217ae0f5bfc47f1a15b5cc06b149c8b6f91ff1359970723f73f63fbff52f5  $S/result.kicad_pro
15ee74c9426113e6603fcf35236f98e3805705cdee1e75e3a9c440a81a5187a9  $S/result.kicad_sch
5ba001041a5187bca6e25b80524eca8c94dce2dd9b673aea3b9d70a7978f8dd2  $S/DAR-1000ES-v5-interlock.kicad_sch
730df9ec84cbfc407e9b01ef10a717fd13a1dfc760f410ef2fa1447507ee145a  $S/DAR-1000ES-v5-power.kicad_sch
39f6b480dc92c14bb8df844b5c09d3353442cfb15d3120ba9c1413e3bde4af92  $S/fp-lib-table
347e5bc61482c02d9e0eeaaadcb4727dc416ede0e1fbe14b3759076092510c5d  $S/sym-lib-table
25425722196793fac11106c167d13f7b946e159045e53b8776e0d9d18465bfee  hardware/pcb-redesign/v5/DAR1000ES.kicad_sym
40c7ebf0398ba594e2b3e867fbf1ab50d393997a5e24e6c27c38a1d2b85a8118  $R/placement-clearance/moves.json
EOF
if [ "$O" != "$P" ]; then
  [ ! -e "$O" ] || { echo "Output directory exists: $O" >&2; exit 1; }
fi
for f in "$O/result.kicad_pcb" "$O/drc.json" "$O/.work"; do
  [ ! -e "$f" ] || { echo "Refusing existing output: $f" >&2; exit 1; }
done
mkdir -p "$O/.work" "$O/preview"
trap 'rm -rf "$O/.work" "$O/org.kicad.kicad"; rm -f "$O/"*.kicad_prl "$O/"*.lck' EXIT
cp "$S/result.kicad_pro" "$S/"*.kicad_sch "$S/fp-lib-table" "$S/sym-lib-table" "$O/"
test -r "$O/../../DAR1000ES.kicad_sym"
docker run --rm --network none --user "$(id -u):$(id -g)" \
  -e HOME="/work/$O/.work" -e TMPDIR="/work/$O/.work" -e PYTHONDONTWRITEBYTECODE=1 \
  -e OUTPUT_DIR="/work/$O" -v "$PWD:/work:ro" -v "$PWD/$O:/work/$O:rw" \
  -w /work --entrypoint /bin/bash "$IMAGE" -c '
    set -euo pipefail
    R=hardware/pcb-redesign/v5/routing
    P=$R/placement-current
    S=$R/placement-integrated
    O=${OUTPUT_DIR#/work/}
    /usr/bin/python3 "$R/placement-loop/test_transform.py"
    /usr/bin/python3 "$R/placement-clearance/apply.py" "$S/result.kicad_pcb" "$O/.work/clearance.kicad_pcb"
    /usr/bin/python3 "$S/verify_stage.py" "$S/result.kicad_pcb" "$O/.work/clearance.kicad_pcb" "$S/result.kicad_pcb" "$R/placement-clearance/result.kicad_pcb"
    H=$(sha256sum "$O/.work/clearance.kicad_pcb" | cut -d" " -f1)
    if /usr/bin/python3 "$P/compose.py" "$O/.work/clearance.kicad_pcb" "$O/.work/bad.kicad_pcb" wrong 2>/dev/null; then
      echo "stage hash guard failed" >&2; exit 1
    fi
    /usr/bin/python3 "$P/compose.py" "$O/.work/clearance.kicad_pcb" "$O/result.kicad_pcb" "$H"
    /usr/bin/python3 "$S/verify_stage.py" "$O/.work/clearance.kicad_pcb" "$O/result.kicad_pcb" "$S/result.kicad_pcb" "$R/placement-loop/result.kicad_pcb"
    cp "$S/result.kicad_pro" "$O/result.kicad_pro"
    kicad-cli pcb drc --refill-zones --save-board --format json --severity-all --exit-code-violations -o "$O/drc.json" "$O/result.kicad_pcb"
    kicad-cli pcb drc --schematic-parity --format json --severity-all --exit-code-violations -o "$O/parity.json" "$O/result.kicad_pcb"
    /usr/bin/python3 "$R/placement-loop/audit.py"
    /usr/bin/python3 -c "import json,sys; p=json.load(open(sys.argv[1]))[\"pairs\"]; find=lambda cap,net: next(x for x in p if x[\"capacitor\"]==cap and x[\"net\"]==net); assert find(\"C6\",\"LOCAL_5V\")[\"track_only_shortest_mm\"]==5.472 and find(\"C6\",\"GND\")[\"pad_centers_mm\"]==17.185 and find(\"C8\",\"SONY_5V_SENSE\")[\"track_only_shortest_mm\"]==8.396" "$O/audit.json"
    /usr/bin/python3 "$R/measure_tht_clearance.py" "$O/result.kicad_pcb" --threshold-mm 0.5 > "$O/clearance.json"
    /usr/bin/python3 "$R/pad-clearance-rework/compare.py" "$S/clearance.json" "$O/clearance.json" > "$O/comparison.json"
    /usr/bin/python3 -c "import json,sys; c=json.load(open(sys.argv[1])); assert c[\"minimum_mm\"][1]>=c[\"minimum_mm\"][0] and c[\"pairs_below_0_3_mm\"][1]<=c[\"pairs_below_0_3_mm\"][0] and not c[\"worsened_under_0_3\"] and not c[\"entered_under_0_3\"]" "$O/comparison.json"
    /usr/bin/python3 "$R/decoupling-trial/crossings.py" "$O/result.kicad_pcb" > "$O/crossings.json"
    /usr/bin/python3 "$P/preview/generate.py"
    sha256sum "$O/result.kicad_pcb" > "$O/board.sha256"
    kicad-cli pcb drc --format json --severity-all --exit-code-violations -o "$O/verification-drc.json" "$O/result.kicad_pcb"
    sha256sum --check "$O/board.sha256"
    cmp "$S/result.kicad_pro" "$O/result.kicad_pro"
    /usr/bin/python3 -c "import json,sys; expected={\"track_not_centered_on_via\",\"tuning_profile_track_geometries\",\"footprint_filters_mismatch\",\"footprint_type_mismatch\"}; assert {x[\"key\"] for x in json.load(open(sys.argv[1]))[\"ignored_checks\"]}==expected" "$O/drc.json"
  '
