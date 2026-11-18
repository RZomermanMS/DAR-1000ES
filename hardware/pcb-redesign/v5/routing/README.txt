Independent v5 routing experiments — not a finished PCB
========================================================

Status: experimental v5 synchronized source and provisional placements and
routes exist, but there is NO fabrication-ready board or physical sign-off.
`reference/pcb-v3-placement-base.kicad_pcb` is a v3 reference only, not v5.
The independently produced `synchronized.kicad_pcb` was checked by its author
against the validated `v5/DAR-1000ES-v5.net.xml` and schematic: zero native
schematic-parity issues, 54 schematic parts plus six mounting holes and 319
netlist nodes. This tool does not synchronize boards. Inputs are read-only and
all generated files stay in `routing/`.

## Placement input

`route.py place --board <synchronized-unrouted-board> --netlist
../DAR-1000ES-v5.net.xml --plan <plan.json> --output <new-file.kicad_pcb>`
requires repository-relative or absolute paths. The plan is an explicit JSON
object with:

```
{
  "placements": {
    "REF": [x_mm, y_mm, angle_degrees]
  },
  "antenna_keepouts_mm": [[x_min, y_min, x_max, y_max],
                          [x_min, y_min, x_max, y_max]]
}
```

List **every** board footprint exactly once, including mounting holes and all
new parts. Coordinates are absolute, with outline (0,0) to (100,300) mm.
The source must be unrouted, two-layer, with a single rectangle outline and
no zones. Two rectangular rule areas forbid pads, tracks, vias, fills and
footprints on both copper layers. They are **not** automatically derived from
the modules: determine and independently verify each antenna's actual
orientation, extent and clearance from the module documentation. This script
does not check plug envelopes, cable bend radii, installed module and socket
envelopes, screwheads, courtyard overlaps, component spacing, or local
decoupling distance. Those require an explicit physical review and native DRC
before routing. In particular put U2, J9, U6-AUDIO1, U9 and U11 in the audio
section and the controller, U8 and U10 in the other section.
`candidate-placement-3.json` is an unverified starting hypothesis; its antenna
rectangles and assembly clearances have not been independently measured and
must not be used as evidence of mechanical or RF compliance.

## Routing

Use the official Freerouting v2.5.0 release JAR:
`https://github.com/freerouting/freerouting/releases/download/v2.5.0/freerouting-2.5.0.jar`.
SHA-256: `f6f51bb02245e8e717f9359bd260cc9c5c0b1bc0acc8b7cb2cd5b8ffeb5de3c7`.
Download separately, provide `--jar <path>`; it is rehashed before use. Do not
commit the JAR. Requires Java 25, Docker and `kicad/kicad:10.0.2`.

```
python3 route.py route --board placement.kicad_pcb \
  --netlist ../DAR-1000ES-v5.net.xml --project ../DAR-1000ES-v5.kicad_pro \
  --jar <verified-jar> --mode single --name single-attempt-1 \
  --boundary <y-mm> --audio-side lower
```

Use a different `--name` and `--mode two` for the two-layer attempt. Add
`--rules <matching.kicad_dru>` if applicable. Each new run copies the source
and project, exports DSN with KiCad, invokes the pinned router with bounded
heap, threads, passes and wall time, and imports its SES into a fresh copy.
The project-adjacent `fp-lib-table` and `DAR1000ES.pretty` are copied alongside
the run's board and project so native DRC can find the local footprints.
GUI, analytics and API are disabled, as are automatic neckdown, fanout and
optimizer. Single-layer requests bottom routing; imported tracks and vias
are independently checked. Every track, including any fanout, must be at
least 0.25 mm. KiCad native DRC using the supplied project and custom rules
must pass all severities, including unconnected items. Net-class width,
clearance and edge checks depend on the supplied project/rules being correct.
Input hashes and router log are saved. A failed or timed-out run is not a
valid result; its new directory must be removed or renamed before retrying.
No DSN rewriting or arbitrary front-copper-to-wire conversion is performed.

The horizontal `--boundary` is a design input, not a computed property.
The pre/post audit rejects nets other than GND, LOCAL_5V, SONY_5V_SENSE and
the two inter-ESP UART nets if their pads occupy both sides, or their track/via
bounding box touches the boundary. The UART exceptions are exact net names
`Net-(U1-CONTROLLER1-IO21)` (U1 J3.18 to U6-AUDIO1 J1.19) and
`Net-(U1-CONTROLLER1-IO47)` (U1 J3.17 to U6-AUDIO1 J1.20). Their exact node
sets must match the netlist; name or endpoint changes fail closed. It checks
key component anchors. It also checks the bounding envelope of every
explicitly classified v5 footprint against the section boundary. This does
not model installed module, USB plug, cable/plug or screwhead envelopes.
The router itself does **not** preserve crossing corridors; a candidate
with a forbidden crossing is rejected after routing. This conservative audit
does not establish the correct classification of every individual component
or prove practical signal ownership, RF, cable and assembly clearances.
Explicitly review those facts and the actual signal/pad map independently.

These are experimental tools, not evidence that a complete v5 layout or
route can be achieved. No fabrication approval follows from their checks.

## Post-processing and trial evidence

`route.py silk --board <routed-board> --netlist <xml> --project <project>
--name <new-run-name> --boundary 150 --audio-side lower` moves the visible
MPN and Manufacturer fields on C9/C10/C12 from F.SilkS to F.Fab, retaining
their data, reference labels and original body and polarity artwork. They
were printed directly over pads. It adds a 7.5 mm diameter F.CrtYd to each
mounting hole; this is a provisional assumption, NOT evidence of actual
hardware clearance. The source schematic and library are unchanged. Run this
step again after each fresh schematic/PCB generation; no manually edited
library survives or is required.

The project copy enables `missing_courtyard` and rejects project DRC
exclusions. Other checks inherited as ignored from the project are:
`track_not_centered_on_via`, `tuning_profile_track_geometries`,
`footprint_filters_mismatch`, and `footprint_type_mismatch`. They have not
been signed off. A zero-DRC result is not a mechanical, RF, electrical, or
fabrication approval.

`experiment-single-2`: five passes, 510 segments, zero vias, 0.30 mm minimum,
53 opens, 175 reported violations; 54 were missing local-library errors in
the then-incomplete wrapper, and `missing_courtyard` was ignored in this older
run. `experiment-two-6` has 737 segments, 11 vias, 0.30 mm minimum, zero opens
and 122 native DRC violations before post-processing.
Its router log has no unknown-setting warning; the rejected via-cost option
used in earlier experiments has been removed. `experiment-silk-7` is the
post-processed two-6 board: native KiCad DRC reports zero violations and zero
unconnected with missing-courtyard enabled, subject to the ignored checks and
unverified physical constraints above. An independent native schematic
parity run also reports zero parity issues; board SHA-256:
`44374a3e5e529bad2d6c6b86dc479dcf3c501c83625bc69086c49c34836ce98d`.
The native parity JSON is `experiment-silk-7/schematic-parity.json`.
No exclusion was added.

`route.py pour` creates two experimental GND zones and runs native refill
and DRC. An earlier trial reduced nine opens to eight but introduced a
starved thermal; a later fully-connected trial produced three starved
thermals. Neither establishes a safe return-current strategy. Two-layer
ground, RF antenna keepouts, module/USB access, JST plug and bend clearances,
screw hardware, and power/signal return paths remain unverified.
The silk-7 title block explicitly marks the board experimental;
the original synchronized and earlier trial boards retain their inherited
title blocks. Do not use any experimental board for manufacture.

The measured pad-center distances in `experiment-silk-7/decoupling-distances.txt`
show serious locality problems: C7 is about 70 mm from U9's supply pad and
74 mm from its nearest ground pad; C14 is about 35 mm from U11. Distances
are straight-line lower bounds, not routed loop lengths. Other closer
placements were attempted but did not complete routing; those intermediate
artifacts were removed. Improving local supply/return loops without losing
connectivity is a hard blocker.

The retained inputs and reports are deliberately limited to one trial per
mode and the best post-processed candidate. The single-layer and two-layer
`inputs.sha256` manifests record the original names of their source boards;
the matching retained bytes are their respective `input.kicad_pcb` files.
The two-layer `input.kicad_pcb` is also the former `candidate-3.kicad_pcb`.
The silk-7 manifest's board input is retained as
`experiment-two-6/result.kicad_pcb`; its duplicate copy was removed. Source
netlist and project still live in the parent v5 directory. To repeat native
DRC in `experiment-two-6`, first copy `fp-lib-table` and `DAR1000ES.pretty`
from `experiment-silk-7` alongside that board; their retained library was
byte-identical to the two-layer trial's library.

For further physical review, Espressif publishes the DevKitC-1 v1.1 mechanical
drawing at https://dl.espressif.com/dl/schematics/esp_idf/DXF_ESP32-S3-DevKitC-1_V1.1_20220429.pdf
and its module datasheet at
https://documentation.espressif.com/esp32-s3-wroom-1_wroom-1u_datasheet_en.html .
JST publishes the horizontal XH series dimensions at
https://www.jst-connector.com/datasheet/jst-connector/S4B-XH-A.pdf .
These primary documents could not be fetched in this environment, and exact
installed module and mating connector variants, plug/bend envelopes and
chassis hardware are not established. They are leads for a future review,
not evidence that the present placement meets physical requirements.

The silk-7 folder includes provisional KiCad assembly, two-layer routing and
schematic PDFs. Visual inspection of assembly page 1 and routing pages 1–2 at
150 dpi, and enlarged board tiles at 450 dpi, found:

* The full PCB outline is visible on each page; no board artwork was visibly
  clipped at the PDF page edges. The assembly's yellow component references
  are very small and low-contrast on white at fit-to-page scale, but examples
  including U1-CONTROLLER1, U6-AUDIO1, J5–J8, C9/C10/C12 and R4 are readable
  when enlarged. Hole references H1–H6 touch or intersect the magenta
  courtyard circles in this composite view. The C12 and JP2 references are
  close together but individually distinguishable in the enlarged view.
* Routing page 1 shows red copper; page 2 shows blue copper. Pads and tracks
  are distinguishable when enlarged, but neither page prints a layer name,
  component references or net labels, limiting standalone traceability.
* On all three PCB pages the revision text "v5 experimental" overruns its
  title-block cell and crosses the right-hand frame line. The text remains
  visible; the experimental/not-for-fabrication warning itself is readable.
  These PDFs therefore need improved plotting/layout before use as readable
  assembly or routing documentation.

The schematic PDF's remaining pages have not been fully inspected. This
visual review does not establish physical, electrical or fabrication signoff.

## Focused tests

```
docker run --rm --network none -v "$PWD:/work:ro" \
  --entrypoint /usr/bin/python3 kicad/kicad:10.0.2 \
  /work/hardware/pcb-redesign/v5/routing/test_board_ops.py
```
