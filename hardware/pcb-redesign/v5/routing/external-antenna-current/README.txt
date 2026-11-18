External-whip current review — NOT FOR FABRICATION, ASSEMBLY OR POWER
=====================================================================

Open result.kicad_pcb with adjacent result.kicad_pro, result.kicad_sch,
child sheets and library tables. Keep the v5 directory structure: custom
libraries resolve via ../../DAR1000ES.pretty and ../../DAR1000ES.kicad_sym.
The unchanged schematic PDF and 59-finding ERC report are in v5/.
This is one new review checkpoint, not a replacement for prior boards.
Saved, refilled board SHA-256:
4c8f37b11bd763e8fd1f9b1dcc80108237feb31861463b5faef0e5c6a775f538

The chosen concept is an external whip connected to each dev board's own
IPEX connector. This motherboard has no added RF connector, feed, matching
network, antenna cutout or fabricated antenna keepout. This choice does
NOT establish that the fitted board has the required connector, that its
antenna selector is set correctly, or that the whip, cable or connector
can be installed safely. Confirm the exact board and module variant,
selector configuration, antenna, cable routing, bend radius, chassis and
nearby metal before any fabrication, assembly or power. A board with a
PCB antenna or an inaccessible/mismatched IPEX would need reassessment.

Placement and assembly
----------------------
All placements and pads are unchanged from placement-current, including
two provisional 2x22 sockets, 2.54 mm pitch and 22.86 mm row spacing:
controller (65,30,0 degrees), audio (65,190,0 degrees). No fit or pinout
of the identified dual-USB-C XH-S3E board is established. Keeping these
positions is deliberate: the independent four-orientation coarse study in
../esp-orientation-comparison/ gives signal-link proxies 1113/990 mm versus
1396/1397 mm for the edge candidate; no antenna-overhang rationale applies
to the external whip. These are not routed lengths, timing, or exhaustive
optimization. The 100 x 300 mm outline and functional domains remain.

The non-copper Dwgs.User boxes are only a *hypothesis*: carrier bounds
x=-1.27..24.13, y=-1.40..61.34 mm relative to J1.1, from the previously
supplied v1.1 reference, and one assumed 12 x 15 mm USB access rectangle
x=5.43..17.43, y=61.34..76.34. No Micro-USB artwork is asserted.
The two body rectangles are x=63.73..89.13, y=28.6..91.34 and
188.6..251.34; their hypothetical USB areas are x=70.43..82.43,
y=91.34..106.34 and 251.34..266.34. The existing coarse study reports
no positive-area overlaps against the other components' courtyard bounding
boxes for these assumptions, with closest assumed mounting-hole courtyard
gaps of 5.26 and 2.095 mm respectively. These are not measurements of
the installed board, either USB port, plug, cable or mounting hardware.
In particular USB cables/plugs can conflict with nearby parts, jumpers,
sockets or chassis even though the hypothetical box passes. The IPEX
position, mated connector, coax direction and bend are not modeled and
may conflict with components, board, housing or USB access. Height,
clearance tolerances, solder access and connector insertion remain unknown.

J2-J11 and JP1/JP2 legends were moved from the remote bottom legend block
toward their connectors; per-pin labels remain. J8's long legend is just
above the section divider, not across it. Each long legend center is within
30 mm of its connector origin; this is a geometric screen, not proof of
readability after assembly. The fitted assembly plots omit F.Fab text to
avoid overlapping hidden component metadata. Mechanical-hypothesis plots
show the provisional boxes; their colors and scale are inspection aids.
Inspect full-size silkscreen, connector labels, fitted-part obstruction and
print legibility before manufacture.

Routing and verification
------------------------
The source route and zones were removed. Freerouting 2.5.0 generated 700
segments and 25 vias. A guarded local edit replaces six B.Cu detour
segments with two F.Cu segments at 0.30 mm for C8/U10, leaving 696 segments
and 25 vias; all segments are at least 0.30 mm. The prior review board is
preserved in checkpoint b0e0072. For routing only, all
netclass clearances were raised to at least 0.30 mm; the source project was
then restored byte-for-byte before DRC. The router reports eight unfixable
0.30 mm pin-to-pin clearance warnings at the unchanged U10/U11 close-pitch
pads; these are not a claim that every pad gap is 0.30 mm. Native KiCad
10.0.2 refill/save DRC: zero violations, zero unconnected; schematic parity:
zero issues; repeat read-only DRC: zero violations and unconnected. The four
inherited ignored checks in the reports are track_not_centered_on_via,
tuning_profile_track_geometries, footprint_filters_mismatch and
footprint_type_mismatch. No project rules or exclusions were weakened.

audit.json verifies exact board/netlist nodes, the two exact UART endpoints,
unchanged footprint positions/pad geometry, outline, classified component
envelopes, allowed section crossings and two filled GND zones with thermal
connections and island removal. crossings.json inventories the actual
centerline crossings at y=150. Only common GND, LOCAL_5V, SONY_5V_SENSE
and the two exact inter-ESP UART nets may cross. R4/R11 pad zone settings
are unchanged. Filled planes and connectivity do not prove return-current
continuity, impedance, thermal solderability or an appropriate bypass loop.

clearance.json measures unrelated PTH-pad to track/via copper on common
layers: minimum 0.301699 mm, zero pairs below 0.30 mm (placement-current
minimum 0.201700 mm, 137 pairs below 0.30 mm). The enforced minimum is
0.30 mm. This partial shape metric excludes zone edges, pad-to-pad,
non-PTH holes, SMD pads, mask, manufacturing and assembly tolerances.
Native DRC applies the original project rules, not a universal 0.30 mm
rule. No manufacturing clearance approval is implied.

Actual bypass paths: audit.json records pad-center and routed track-only
shortest paths including both power and ground. Supply paths C1-C8, C14,
C10-C13 are respectively 3.380, 3.380, 3.880, 3.124, 4.380, 6.380,
4.380, 7.769, 7.429, 15.331, 8.331, 15.331, 8.331 mm. C8 decreases
from 14.375 mm in b0e0072 (8.396 mm in placement-current); C6 increased
from 5.472 mm and C10 from 13.731 mm relative to placement-current. C13's modeled
ground track-only path increased from 15.168 to 32.637 mm. Other ground
track-only paths include C1 79.679, C2 75.655, C3 28.767, C4 44.769,
C5 39.861 and C6 46.060 mm; a plane can provide a different path but the
model omits it. These are review blockers, not compact-loop proof. An
attempt to retain old C6/C8/C10 source traces failed the >=0.30 mm width
gate; those traces were not accepted and no check was relaxed. Future
local rerouting should improve these paths while maintaining the new
clearance and all checks. Local decoupling, plane return distribution and
ESP module bypass must be independently designed and measured.

preview/ contains fitted assembly, mechanical-hypothesis and unmirrored
F.Cu/B.Cu PDFs and labeled PNGs with controller/audio closeups. These are
not fabrication artwork. Sony/local supply sequencing, back-powering,
inrush, mute/relay behavior, antenna configuration and the unresolved
schematic ERC findings all require engineering and bench review.

Reproduction
------------
From repository root, Docker with the pinned KiCad image, Java 25 and the
official Freerouting 2.5.0 JAR (SHA-256 verified by the script) are required:

  bash hardware/pcb-redesign/v5/routing/external-antenna-current/build.sh \
    external-antenna-replay /absolute/path/to/freerouting-2.5.0.jar

The script uses JAVA_HOME/bin/java when JAVA_HOME is nonempty, otherwise
java from PATH. It requires Java major version 25 and checks it before
creating the output directory. Alternatively use --local-replay in place
of the output name to build in this candidate's temporary .replay folder;
remove that folder after review.

The output sibling must not exist. Source board, source project, netlist
and JAR hashes are checked. The script re-routes, restores the exact source
project, runs native refill DRC and parity, exact netlist/domain/placement/
plane and clearance audits, plots, hashes, and performs a read-only DRC.
Generated UUIDs can change hashes. Review the replay's own reports.
