ESP rigid-assembly orientation experiment

**Exploratory placement evidence, not a routed board or fabrication/RF
approval.** Input: `../placement-current/result.kicad_pcb`, SHA-256
`1639ae39478dff811224cf6ff1e299ec685bb6e8568631e4d861dfafcb36eafa`.
Each ESP is analyzed independently with the other one and all other
footprints fixed. Pads stay attached to their own 22-pin rows. No board is
written; tracks/zones are not moved or rerouted. The actual existing edge
candidate has *both* ESPs moved; independent metrics here do not establish
joint routing, electrical performance, fit or DRC.

## References, datum and limits

The user supplied the official ESP32-S3-DevKitC-1 v1.1 carrier bounds in
J1.1 coordinates: x=-1.27..24.13, y=-1.40..61.34 mm (25.40 × 62.74).
These replace the prior assumed y=-5..57.74 alignment. The baseline
footprint says pin 1 is at the antenna end; local +y points toward the USB
end and successive row pins. This experiment takes those axes as correct.
For 0/90/180/270°, the pin-1 end points respectively up/left/down/right
in KiCad's y-down coordinates.

Primary sources:
* Espressif dimensional drawing, Rev 1.1 (2022-04-29):
  https://dl.espressif.com/dl/schematics/esp_idf/DXF_ESP32-S3-DevKitC-1_V1.1_20220429.pdf
* Espressif guide:
  https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32s3/esp32-s3-devkitc-1/user_guide_v1.1.html

The original PDF/guide could not be fetched in this environment (DNS
unavailable), so the supplied datum alignment was not independently
verified against the primary drawing. The guide's indexed text distinguishes
WROOM-1/-2 PCB antennas from a WROOM-1U external antenna connector. The
installed variant is not established.

A secondary raster reproduction was inspected during this run, from
`JamelHammoud/basecase`, `tools/parts/specs/esp32-s3-devkitc-1/dim-1.png`.
It shows a MINI-ANT-TYPEB label extending past the pin-1 end and two USB
ports at the other end. The rough pixel-derived rectangle
x≈2.4..20.5, y≈-7.9..-1.5 relative to J1.1 is not an authoritative,
toleranced antenna measurement or an RF clearance boundary. It is not
used by the search. Actual module, antenna/connector and installed-part
envelopes and RF clearance remain unknown. In particular a carrier inside
the board does not imply the module or its antenna is inside it, nor does
a carrier at the edge imply RF compliance. The previous arbitrary
full-width y=-10..-5 appendage, associated substrate areas and proposed
notches have been removed; they did not describe a verified antenna.

For comparison only, USB plug/cable-access is a single *hypothetical*
12 × 15 mm rectangle x=5.43..17.43, y=61.34..76.34, outside the
opposite end of the carrier. It is not a measurement of either USB port,
plug, cable, or their positioning; it is not an antenna or an RF keepout.
It may extend off the PCB. Account for both real ports and cable bends
separately before design approval.

## Method

The board is the input's 0..100 × 0..300 mm rectangle. Controller carrier
must fit x=0..100, y=0..150; audio carrier must fit x=0..100, y=150..300.
Touching an edge/domain line is allowed, with **no** manufacturing
tolerance. These comparison domains are not validated electrical
partitions or an enclosure.

KiCad native footprint courtyard primitive bounding boxes are unioned per
footprint, with pad boxes as fallback; the other ESP uses the corrected
carrier. These AABBs are conservative but not exact courtyard polygons or
fitted parts. H1–H6 use their assumed 7.5 mm courtyard, not verified mounting
hardware. Positive-area intersections of carrier or hypothetical USB access
with these boxes are counted; boundary contact is not a collision. A 5 mm
expanded numbered-J courtyard is a sensitivity flag, not a real connector
plug model or search rejection. Pad-to-other-pad AABB distance is a
conservative lower bound, not exact copper clearance or DRC. Pad edge
>=0.25 mm is only a screening assumption.

For each orientation sample origins on a 2 mm global grid where the carrier
fits its domain. Rank by count of carrier and hypothetical USB-access box
collisions, then pad-edge failure, then distance from the carrier pin-1 end
to the board edge in its outward direction, then signal distance and grid
congestion. Edge distance is a geometric preference, **not antenna
substrate overlap or RF clearance**. Also record the shortest-signal
candidate meeting the zero-collision/pad-edge screen. The USB assumption
affects feasibility and ranking; changing it may change the result.
Infeasible angles retain a least-overlap example. Grid sampling does not
prove that no other placement exists.

The ratsnest proxy joins each connected ESP pad to its nearest external pad
on the same net. It is not KiCad's dynamic ratsnest or an MST, and can
double-count fanout; the other ESP remains at its original location.
"Signal" excludes only GND, LOCAL_5V and SONY_5V_SENSE. The congestion proxy
draws each signal link as a horizontal-then-vertical Manhattan L and counts
touched 5 mm cells once per link, reporting maximum occupancy and cells
with at least three links. It ignores obstacles, track widths, layers,
existing copper, via costs and net topology; it is not a router or capacity
estimate.

## Results

Edge-first representative per orientation; "free" is the number of grid
points satisfying the carrier/assumed-USB no-overlap and pad-edge screen.
Lengths are signal-link Euclidean mm; peak/cells are L-grid metrics.

| ESP | ° | origin | free / tested | pin-1 end to edge mm | signal mm | peak / cells ≥3 | conflicts |
|---|---:|---|---:|---:|---:|---:|---|
| controller | 0 | (62,2) | 131 / 1628 | 0.6 | 1398.819 | 8 / 37 | none |
| controller | 90 | (16,144) | 0 / 1178 | 14.6 | 1253.133 | 9 / 29 | carrier U5 |
| controller | 180 | (86,148) | 132 / 1628 | 150.6 | 1460.217 | 8 / 40 | none |
| controller | 270 | (98,120) | 0 / 1178 | 0.6 | 1313.755 | 11 / 40 | carrier and USB U5 |
| audio | 0 | (54,152) | 205 / 1628 | 150.6 | 1017.498 | 5 / 21 | none |
| audio | 90 | (16,200) | 0 / 1178 | 14.6 | 905.399 | 9 / 24 | carrier C4, U2 |
| audio | 180 | (86,298) | 209 / 1628 | 0.6 | 1431.922 | 6 / 45 | none |
| audio | 270 | (98,152) | 0 / 1178 | 0.6 | 1240.093 | 11 / 38 | carrier C3, R1 |

Baseline controller (65,30,0°) has 1113.164 mm signal, peak 5 and 33
cells ≥3; audio (65,190,0°) has 990.330 mm, peak 6 and 26 cells. Across
the screened orientations, shortest-signal choices are controller
(64,56,0°): 1014.858 mm, and audio (80,232,180°): 905.728 mm. Their
respective pin-1 carrier ends are 54.6 and 66.6 mm from the outward board
edge. See `results.json` for each orientation's shortest-signal selection.

### Actual existing candidate, not an edge-flush carrier

For `../esp-edge-candidate`, the controller (66,5,0°) carrier bounds are
x=64.73..90.13, y=3.60..66.34, and audio (86,295,180°) bounds are
x=61.87..87.27, y=233.66..296.40. Each carrier's pin-1 end is **3.60 mm
inside** the corresponding board edge, not flush. Both pass the modeled
carrier and hypothetical USB-to-courtyard screens, with no expanded-J
envelope hits; minimum pad-to-edge distance is 4.15 mm. Nearest other-pad
AABB gaps are 3.59 mm (controller J3.6 to H2 hole) and 2.44 mm (audio
J3.16 to JP2.2); carrier-to-hole courtyard gaps are 1.095 mm to H2 and
30.146 mm to H6. Signal proxies are 1395.898 and 1396.920 mm, peak 7 / 7,
and 41 / 42 cells ≥3.

If the *rough secondary raster estimate* happens to describe this
part, its -7.9 mm tip would extend roughly 2.9 mm beyond the board at
these candidate origins; some of the estimated feature would still be over
the substrate. This illustration has no tolerance and is not a measured
RF clearance or fit conclusion.

For geometry comparison only, nominal flush positions are (66,1.4,0°)
and (86,298.6,180°). Their carrier edges touch the board edges, with no
modeled carrier or hypothetical USB box collisions and 0.55 mm pad-edge
distance. They are **not** the existing candidate and are not recommended
without verifying actual component/antenna dimensions, tolerances,
mounting hardware, ports, enclosure, RF clearance, rerouting and DRC.
The estimated antenna feature, if applicable, extends beyond such a flush
carrier; the unchanged board outline is not evidence of enclosure fit.

## Reproduce

From the repository root, with Docker and the pinned image available:

```
bash hardware/pcb-redesign/v5/routing/esp-orientation-comparison/run.sh
```

The script loads the input read-only in KiCad 10.0.2, checks its hash, runs
tests of all four transforms against native pcbnew pads plus carrier
rotation and candidate regressions, and replaces `results.json`. It removes
KiCad/Python caches afterwards and does not save or create a board copy.
