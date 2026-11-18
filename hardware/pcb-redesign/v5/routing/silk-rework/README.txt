v5 silk rework — experimental, NOT for fabrication or power-up
=============================================================

result.kicad_pcb starts from ../decoupling-trial/result.kicad_pcb, without
changing that source. It adds 60 board-level F.SilkS texts and one 0.2 mm
horizontal line at y=150 mm; no copper, footprint, pad, zone, rule area,
outline or existing artwork is changed. Controller is above the line and
audio below. The section split is an annotation, not an electrical barrier.
Source SHA-256:
  53428c44aaf48bd0ea867c7b11f82e9277dcee58e0993fbcc820f4a65fc4612f
This result SHA-256:
  a46a6668287fbf6cfe683f042e2ea08dc502d9e10ea7c8cfbd2c2bb61b709780

All external J2–J12 connectors and JP1/JP2 have individual pin labels
outside their footprint courtyards, plus a two-column full-net pin legend
on the bottom of the board. J4 explicitly reads 1 FLSTB, 2 FLSDATA,
3 FLSCLK. Left-edge connector pins increase downwards; top-edge connector
pins increase leftwards. The added "1" labels align with the KiCad pad 1
locations, not with an assumed cable orientation. The existing JST triangle
also marks pad 1; the jumper "1 LOCAL" identifies pad 1 even though some
inherited artwork visually boxes the other pin. On J7, the 1 IN4 and 2 IN5
labels are shifted slightly downward to clear U5's reference; use their
printed numbers, not row alignment alone.

The short local names have these exact expansions: J2 "2 5V" is LOCAL_5V;
J12 "2 SENSE" is SONY_5V_SENSE; JP1 "1 LOCAL"/"2 CTRL" are LOCAL_5V and
ESP_CTRL_5V; JP2 "1 LOCAL"/"2 AUDIO" are LOCAL_5V and ESP_AUDIO_5V.
Other names omit only the leading schematic hierarchy slash. The complete
names and pin numbers are printed in the bottom legend. On-module header
pins are not individually relabeled; their existing J1.1/J3.1 or JP1.1/
JP4.1 markings remain. This is not a replacement for a harness pinout,
polarity, mating-connector or assembly review.

The local labels use 0.8 mm characters and 0.12 mm strokes, while the
legend uses 1 mm and 0.15 mm. They are legible in the rendered closeups,
but actual printing depends on the fabricator. The labels lie outside
footprint courtyard bounding boxes, not necessarily outside installed
plug, cable, daughterboard or chassis envelopes; visibility after assembly
and silkscreen print quality remain unverified. In particular J7/J8 are
close to the U5 module courtyard; physical access must be checked.
assembly.pdf and assembly-controller.png / assembly-audio.png are unmirrored
KiCad F.SilkS/F.CrtYd/Edge.Cuts plots. The PNG headings and warning are
off-board, not physical markings. Images are inspection aids, not signoff.

Validation for this result
--------------------------
KiCad 10.0.2 drc.json and parity.json: zero violations, zero unconnected,
zero schematic-parity issues. Four inherited checks remain ignored, as
listed in the reports. audit.txt records the v5 netlist and UART checks,
section and footprint-envelope checks, unchanged footprint/pad placement,
rule area bounds, 720 segments, seven vias and 0.30 mm minimum track width.
test_overlay.py compares native normalized boards after stripping exactly
the new drawing UUIDs, checks reproducible text geometry, and rejects a
moved connector and duplicate application. Overlay preflight checks all
connector numbers, nets, rotations and actual pad positions, as well as
the full v5 netlist. It conservatively rejects added drawing bounding boxes
against footprint courtyard boxes plus 0.2 mm, pad boxes plus 0.3 mm,
visible footprint reference boxes, other new items and the board edge.
Native DRC checks actual silk/mask; visual inspection is still needed for
other existing silkscreen and for the physical assembly.

The upstream decoupling trial remains electrically incomplete; in
particular several bypass return paths are very long. The previous trial's
physical, RF, power integrity and solder-access warnings all still apply.
No DRC result proves those properties.

Power-rework compatibility test
-------------------------------
Applied the same script to ../power-rework/result.kicad_pcb with SHA-256
e19e9908fe62e82e88d0f32ed86c2eb219e02af9a60c4565729e243f000d3387.
The transient integration-test.kicad_pcb SHA-256 was
d47f0bbf9583b3b1b4d19807cf143e646b7a37c7552e71ed4d5f0eba9abda1a4.
integration-drc.json and integration-parity.json both reported zero
violations and opens; the latter also reports zero parity issues. The
transient integration board was removed: these reports are evidence only
for those exact input bytes, not any later power candidate. Reapply and
rerun native DRC, parity, domain audits and preview after any changes.
The transformation assigns new UUIDs, so regenerate and compare geometry
rather than byte hashes. It does not refill or otherwise change zones.

Reproduction from repository root
---------------------------------
Requires KiCad 10.0.2, e.g. Docker image kicad/kicad:10.0.2 digest
sha256:165c81785b2df23a09892f4cc53bc0095a83b469bfbbe07989670d64049677a7.
Choose an unused output filename inside the repository; the script never
overwrites an existing file or the input. Example:

  P=hardware/pcb-redesign/v5/routing/silk-rework
  V=hardware/pcb-redesign/v5
  docker run --rm --network none --user "$(id -u):$(id -g)" \
    -e HOME=/nonexistent -e TMPDIR=/work/$P -e PYTHONDONTWRITEBYTECODE=1 \
    -v "$PWD:/work" --entrypoint /usr/bin/python3 kicad/kicad:10.0.2 \
    /work/$P/apply_silk.py /work/$V/routing/decoupling-trial/result.kicad_pcb \
    /work/$P/new-result.kicad_pcb /work/$V/DAR-1000ES-v5.net.xml

For the power board, substitute its input path. Review any preflight
failure instead of bypassing it. For native parity, use the candidate's
matching project, schematic hierarchy and library table with the new
board's basename; run kicad-cli pcb drc --severity-all
--exit-code-violations --format json, then again with --schematic-parity.
Run ../decoupling-trial/audit.py with an appropriate placement baseline,
new board and netlist. To reproduce the retained views and regression:

  docker run --rm --network none --user "$(id -u):$(id -g)" \
    -e HOME=/nonexistent -e TMPDIR=/work/$P -e PYTHONDONTWRITEBYTECODE=1 \
    -v "$PWD:/work" --workdir /work/$P --entrypoint /bin/bash \
    kicad/kicad:10.0.2 -c 'python3 preview.py && python3 test_overlay.py'

KiCad may report unwritable configuration directories with HOME set this
way; verify exit status and JSON content. Delete generated *.kicad_prl and
cache directories after running. Keep the candidate's source intact.
