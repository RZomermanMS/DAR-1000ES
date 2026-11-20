Bypass return trial — incomplete; NOT for fabrication or power-up
================================================================

Outcome: no compact local return was found in the bounded searches below.
No proposed bridge was retained. result.kicad_pcb is byte-identical to
the newest ../decoupling-trial/result.kicad_pcb (SHA-256
53428c44aaf48bd0ea867c7b11f82e9277dcee58e0993fbcc820f4a65fc4612f).
The source board and all other boards are unchanged. This means ALL
existing copper, return continuity, and other paths are preserved, not
that the existing layout is electrically satisfactory.

Searches and limitations
-----------------------
For each of C1/U3, C2/U4, C3/U2 and C4/U6, search.py tried a straight
segment and sampled single bends (2 mm grid, bounding rectangle plus
4 mm) on F.Cu and B.Cu, from the capacitor GND pad to the IC's actual
GND pin 7. None passed the geometry prefilter. grid_search.py then tried
multi-bend 0.5 mm-grid routes, separately on each copper layer, within
the endpoints' bounding rectangle expanded 8 mm and with a 25-second
per-layer limit. It found none; no vias or inter-layer pad transitions
were explored. See search.json and grid-search.json. The prefilter uses
KiCad copper shapes, 0.30 mm-wide copper, at least 0.301 mm clearance to
unrelated PTH copper and 0.201 mm to other unrelated copper. It does not
model all DRC constraints; any survivor would require native DRC. This
is a discretized, bounded search, not proof no route exists.

bridge_search.py additionally explored same-layer straight and orthogonal
one-bend bridges between existing GND pads within 30 mm, ranked by a
modeled lower bound, capped at 600 pad pairs and 20 seconds per IC pair.
It checked for an actual shortest-path improvement and ran native DRC on
each retained provisional bridge. Three passed DRC, but they are long,
nonlocal shared-network shortcuts rather than compact bypass loops. They
were rejected and removed regardless of DRC and clearance results:

  F.Cu GND 0.30 mm: (45,45) -> (50,45) -> (50,68)
  F.Cu GND 0.30 mm: (9.8,240) -> (25,247)
  F.Cu GND 0.30 mm: (54.62,220) -> (50.24,235)

The first overlaps existing GND copper on part of the second segment;
this is an additional reason not to retain it. bridge-search.json records
the order, search counts and provisional results. evidence.json summarizes
the combined transient result, not the retained board. Its SHA-256 is
recorded there; new segment UUIDs can vary when reproducing. No component
was moved.

Actual modeled capacitor-to-IC-pin-7 lengths, mm:
                     retained/source   rejected combined bridges
  C1.1 -> U3.7          123.004              119.298
  C2.1 -> U4.7          122.190              118.485
  C3.2 -> U2.7          181.309              164.201
  C4.2 -> U6.7          120.790              103.682

These are shortest centerline graph distances, not measurements of
current paths, inductance or bypass effectiveness. The search also
shortened modeled C6 GND by 3.705 mm in the transient result; other
reported paths were unchanged. They may share copper. Direct supply
and return loops remain grossly long; re-placement, layer transitions,
rerouting, and power-integrity engineering may be necessary.

Validation on retained result
-----------------------------
KiCad 10.0.2 native drc.json and parity.json report zero violations,
zero unconnected items and zero parity issues; parity was explicitly
enabled in the latter. Four checks remain ignored as listed in the JSON.
audit.txt checks the v5 netlist and UART nodes, y=150 mm net/domain
boundary, footprint envelopes and placements, rule areas and widths.
crossings.json lists centerline crossings, not corridor or return-current
proof. The path summaries in evidence.json measure actual pin 7, not
grounded logic inputs.

The unrelated track/via-to-PTH-pad copper clearance measurement is
0.201657 mm minimum, with 332 pad/item/layer pairs below 0.30 mm, both
before and after. The rejected bridge combination also measured 0.201657
mm and 332 pairs, and the complete lists of pairs at or below 0.30 mm were
identical (see evidence.json). The global 0.30–0.50 mm
THT target is therefore NOT met. This tool excludes pad-pad clearance,
zones, non-PTH holes and non-PTH pads; counts depend on segmentation.
Native DRC and these checks do not establish assembly, solder access,
physical fit, or power integrity.

Reproduction (Docker KiCad 10.0.2 image; no router dependencies)
----------------------------------------------------------------
Run from the repository root. The commands below replace the trial board
temporarily; the last command restores it. Only use the designated trial
directory; never point them at an existing source board.

  O=hardware/pcb-redesign/v5/routing/bypass-return-trial
  P=hardware/pcb-redesign/v5/routing/decoupling-trial
  cp "$P/result.kicad_pcb" "$O/result.kicad_pcb"
  docker run --rm --network none --user "$(id -u):$(id -g)" \
    -e HOME=/nonexistent -e PYTHONDONTWRITEBYTECODE=1 \
    -v "$PWD:/work:ro" -v "$PWD/$O:/out:rw" --entrypoint /bin/bash \
    kicad/kicad:10.0.2 -c '
      set -e
      /usr/bin/python3 /out/search.py
      /usr/bin/python3 /out/grid_search.py
      /usr/bin/python3 /out/bridge_search.py
      /usr/bin/python3 /work/hardware/pcb-redesign/v5/routing/measure_tht_clearance.py \
        /out/result.kicad_pcb --threshold-mm 0.3 > /out/tht-rejected-bridges.json
      /usr/bin/python3 /work/hardware/pcb-redesign/v5/routing/decoupling-trial/measure_paths.py \
        /out/result.kicad_pcb > /out/paths-rejected-bridges.json
    '
  cp "$P/result.kicad_pcb" "$O/result.kicad_pcb"
  rm -f "$O/result.kicad_prl" "$O/bridge-drc.json" "$O/grid-drc.json" "$O/search-drc.json"

Re-run retained-board checks using the same Docker options with these
commands inside the container (V=/work/hardware/pcb-redesign/v5 and
P=$V/routing/decoupling-trial):

  kicad-cli pcb drc --format json --severity-all --exit-code-violations -o /out/drc.json /out/result.kicad_pcb
  kicad-cli pcb drc --format json --severity-all --schematic-parity --exit-code-violations -o /out/parity.json /out/result.kicad_pcb
  /usr/bin/python3 "$P/audit.py" "$P/result.kicad_pcb" /out/result.kicad_pcb "$V/DAR-1000ES-v5.net.xml" > /out/audit.txt
  /usr/bin/python3 "$P/measure_paths.py" /out/result.kicad_pcb > /out/paths.json
  /usr/bin/python3 "$V/routing/measure_tht_clearance.py" "$P/result.kicad_pcb" --threshold-mm 0.3 > /out/tht-before.json
  /usr/bin/python3 "$V/routing/measure_tht_clearance.py" /out/result.kicad_pcb --threshold-mm 0.3 > /out/tht-after.json
  /usr/bin/python3 "$P/crossings.py" /out/result.kicad_pcb > /out/crossings.json

fp-lib-table maps the local library through /work for this container.
KiCad may report unwritable HOME/font-cache warnings; use exit codes and
report contents. Remove the generated result.kicad_prl session cache.
The detailed path and clearance JSON reports are intentionally not retained;
the reproduction commands regenerate them if needed.
