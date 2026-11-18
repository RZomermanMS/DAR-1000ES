Placement-first C6 milestone — experimental, NOT FOR FABRICATION OR POWER-UP
============================================================================

Source: ../integrated-review/clearance-first-corrected/result.kicad_pcb
SHA-256 c63fa89924e244bbf6bfd92f2c72e6c9d34117106b4bd87cf46f7971078920c5
Saved refilled result.kicad_pcb SHA-256:
fb1f06735ecc218e2946121efeb44f91a6d88a2804b6029a4e8973fffa8e859e
The source is unchanged. board.sha256 is checked after a separate read-only
native DRC; audit.json, clearance.json and comparison.json also identify the
saved board by hash.

C6 moved from (45,68) to (55.5,41.5) mm, orientation 0 degrees. Its
LOCAL_5V pad 1 moved from (45,68) to (55.5,41.5); GND pad 2 moved from
(50,68) to (60.5,41.5). U8's true VCC is pad 14 at (52.62,45), not a
nearby ground pin. Pad-center distance and direct F.Cu track centerline
are 4.533 mm, versus 24.229 mm and 40.998 mm respectively in the source.
The former C6 power junction remains connected through a new through via at
(45,68); both old power branches remain. Two obsolete GND branches to the
old pad are removed. A new 0.30 mm F.Cu track connects C6.1 to U8.14.
All other tracks, board artwork, footprint/pad positions and pad nets and
geometries are checked unchanged in audit.json; C6's visible F.SilkS
reference and its footprint artwork move with it.

KiCad 10.0.2 native refill/save DRC: zero violations, zero unconnected.
Schematic-parity DRC: zero violations, zero unconnected, zero parity issues.
Read-only DRC on the saved board: zero violations and zero unconnected;
the board hash matched before and after. The inherited ignored checks are
track_not_centered_on_via, tuning_profile_track_geometries,
footprint_filters_mismatch and footprint_type_mismatch. Domain audit checks
the netlist, exact UART mappings, section boundaries, component envelopes,
unchanged antenna rule areas, and both filled common-GND zones. The saved
C6 GND thermal-gap samples find fill on both copper layers (60/45 samples
out of 360); U8.7 has 60/30. These samples do not establish return paths
or thermal or high-frequency performance.

Actual saved-board THT pad-to-unrelated-track/via measurements, per layer
and below 0.5 mm, are in clearance.json and comparison.json. Minimum remains
0.201700 mm; pairs below 0.30 mm remain 144 and below 0.25 mm remain 45.
There is no aggregate clearance improvement: one measured pair leaves the
0.5 mm reporting range and one enters it. The new pair is C6.2 GND to the
IO5 B.Cu track at 0.390 mm. Counts are segment-specific, not independent
pad locations. Measurements exclude zones, pad-pad, non-PTH holes, SMD
pads and installed parts.

preview/closeup-assembly-c6-u8.png shows the actual saved F.SilkS and
F.CrtYd (not a decorative overlay); front/back copper closeups and full
plots are also provided. The shown C6 reference is legible and the modeled
courtyards do not overlap under native DRC; this verifies footprint
geometry, not the physical body or its tolerance. Real component body fit,
solder/tool access and reference readability after assembly remain
unverified. Crops are unmirrored inspection aids, not fabrication artwork.

Reproduce: from the repository root remove only this directory's
result.kicad_pcb, then run bash hardware/pcb-redesign/v5/routing/placement-c6/build.sh.
The build requires the pinned KiCad 10.0.2 Docker image, checks the exact
source hash, tests replay and rejects repeated or in-place generation,
refills/saves, rechecks parity, runs audits and regenerates previews.
Generated UUIDs and timestamps may change, so the rebuilt board hash may
differ; use newly generated reports rather than this recorded hash.

The other bypass placements remain as in the source. GND connectivity in
DRC and sampled fills do not prove a short return loop, adequate power
integrity, RF behavior, mechanical fit, safety, assembly or bench behavior.
No fabrication or power-up approval is implied.
