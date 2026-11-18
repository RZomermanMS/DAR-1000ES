ESP rigid-assembly orientation experiment

**Exploratory placement evidence, not a routed board or fabrication/RF approval.**
The exact input is `../placement-current/result.kicad_pcb`, SHA-256
`1639ae39478dff811224cf6ff1e299ec685bb6e8568631e4d861dfafcb36eafa`.
Each ESP is analyzed independently with the other one and all other
footprints fixed at their input locations. Pads stay attached to their own
22-pin rows: the rows and assumed installed device are one rigid body.
No board is written. Existing tracks/zones are **not** moved or rerouted;
these placements cannot be applied to the routed board without rerouting and
native DRC. The metrics do not establish that routing is possible.

## Assumptions and method

Coordinates are mm; origin is footprint J1.1, with KiCad y down and KiCad
orientation (90° maps local +y to global +x). The board is the input's
0..100 × 0..300 rectangle. Controller body must fit x=0..100, y=0..150;
audio body must fit x=0..100, y=150..300. Touching an edge/domain line is
allowed, with **no** manufacturing tolerance. These are comparison domains,
not a validated electrical partition or enclosure.

The board actually supplies the two 22-pad rows, their 2.54 mm pitch and
22.86 mm row spacing, not a complete daughterboard model. Following the
unverified dimensional lead in `../../MECHANICAL-REVIEW.txt`, assume a
25.4 × 62.74 body, centered between rows, local x=-1.27..24.13,
y=-5..57.74. **The longitudinal alignment is assumed**, not sourced from a
verified drawing. Assume a full-width 5 mm antenna projection at local
x=-1.27..24.13, y=-10..-5, and a 12 × 15 mm USB plug/cable-access rectangle
at x=5.43..17.43, y=57.74..72.74. These are deliberately simple hypotheses,
not measured module/antenna/plug geometry. The antenna side is inferred from
the footprint description, not verified on the installed part. It can extend
off the PCB; body cannot. Model USB as allowed off the PCB and report its
outside area. No chassis, socket height, module component height, cable bend,
USB port location or orientation is established.
All antenna/substrate overlap values, including zero, are **provisional**
pending verification of the actual antenna y-offset and PCB-body dimensions
and alignment for the installed board. They do not establish RF clearance.

KiCad native footprint courtyard primitive bounding boxes are unioned per
footprint; pad boxes are the fallback if no courtyard exists. The other ESP
uses the assumed body instead. The rectangular AABBs are conservative but
not exact courtyard polygons or fitted parts; H1–H6 use their assumed
7.5 mm courtyard, not verified mounting hardware. Body, antenna and USB
positive-area overlaps with these boxes are counted; boundary contact is
not a collision. Additionally report intersections of body/USB with each
numbered J connector's courtyard AABB expanded by 5 mm in all directions.
This expanded envelope is a sensitivity flag, not a real plug model or a
search rejection. Calculate the minimum ESP pad bounding-box distance to the
rectangular board edge and to any other pad/hole box. The latter is a
conservative AABB lower bound, not an exact copper clearance or DRC. Pad
edge >=0.25 mm is a **screening assumption**, not a manufacturing rule.

For each orientation sample footprint origins on a 2 mm global grid, and
consider all positions whose body fits its domain. Rank first by count of
body/antenna/USB courtyard-box overlaps, then pad-edge failure, then antenna
projection area over substrate, then signal distance and grid congestion.
Also record the shortest-signal candidate among zero-overlap/edge-screen
grid positions, even if its antenna is over substrate. `results.json` has
counts, bounds, collisions, distances and both selections. Infeasible angles
retain their least-overlap examples, not pretend feasible placements.

The ratsnest proxy joins **each connected ESP pad** to its nearest external
pad on the same net using Euclidean distance. It is not KiCad's dynamic
ratsnest or an MST, and can double-count fanout; other ESP remains at its
original location. "Signal" excludes only GND, LOCAL_5V and SONY_5V_SENSE.
The congestion proxy draws each signal link as a horizontal-then-vertical
Manhattan L and counts touched 5 mm cells once per link, reporting maximum
occupancy and cells with at least three links. It ignores obstacles, track
widths, layers, existing copper, via costs, and net topology; it is a
repeatable comparison, not a router or capacity estimate.

## Results

Table: edge-first representative per orientation; lengths are signal-link
Euclidean mm, peak/cells are the L-grid metrics. "Free" is the number of
grid points satisfying the assumed no-overlap and pad-edge screen. A collision
in the last column means the angle had no such point on this grid.

| ESP | ° | origin | free / tested | antenna on substrate mm² | signal mm | peak / cells ≥3 | conflicts |
|---|---:|---|---:|---:|---:|---:|---|
| controller | 0 | (66,6) | 123 / 1628 | 25.4 | 1382.659 | 7 / 41 | none |
| controller | 90 | (24,144) | 0 / 1178 | 127 | 1271.563 | 9 / 27 | body U5 |
| controller | 180 | (86,108) | 120 / 1628 | 127 | 1334.161 | 9 / 35 | none |
| controller | 270 | (94,120) | 0 / 1178 | 25.4 | 1276.956 | 11 / 38 | body and USB U5 |
| audio | 0 | (66,180) | 197 / 1628 | 127 | 986.858 | 6 / 26 | none |
| audio | 90 | (24,200) | 0 / 1178 | 127 | 915.422 | 9 / 20 | body C4, U2 |
| audio | 180 | (86,294) | 197 / 1628 | 25.4 | 1385.498 | 7 / 42 | none |
| audio | 270 | (94,152) | 0 / 1178 | 25.4 | 1212.778 | 11 / 37 | body C3, R1 |

Baseline controller (65,30,0°) is 127 mm² substrate, 1113.164 mm signal,
peak 5, 33 cells ≥3; audio (65,190,0°) is 127 mm², 990.330 mm, peak 6,
26 cells. Shortest feasible signal choices are controller (64,56,0°):
1014.858 mm, peak 6, 26 cells, and audio (58,176,0°): 897.718 mm,
peak 6, 15 cells; both leave all 127 mm² of assumed antenna over substrate.
The edge preference therefore carries a substantial wiring/congestion penalty.
Grid sampling cannot prove no other placements exist.

The two edge-first grid cases leave a 1 mm substrate strip. Hypothetically
removing the controller strip x=64.73..90.13, y=0..1 and audio strip
x=61.87..87.27, y=299..300 creates edge notches, changing the rectangular
outline. In the **original** board, no track/via or other-pad AABB overlaps
these strips. This does not test zone copper, edge clearances, relocated
copper, structural strength, enclosure, or actual antenna geometry, and
does not establish that either cut is feasible.

As a separate non-grid, non-cutout alternative, shifting those origins one
mm outward produces controller **(66,5,0°)** and audio **(86,295,180°)**.
Each assumed antenna projection then lies completely outside the unchanged
rectangle; each body is exactly flush with the corresponding board edge.
Both have 4.15 mm minimum pad-to-board-edge distance, no modeled
body/antenna/USB-to-courtyard overlaps and no expanded-J envelope overlaps.
The nearest other pad AABB gaps are 3.59 mm (controller J3.6 to H2 hole)
and 2.44 mm (audio J3.16 to JP2.2). The controller body is only 1.095 mm
from H2's assumed courtyard AABB; audio body is 33.718 mm from H6's. Their
respective signal proxies are 1395.898 and 1396.920 mm, peak 7 / 7, and
41 / 42 cells ≥3. The two candidate body/antenna/USB envelopes lie in
opposite ends of the board and do not intersect, but the stated net and
collision comparisons were independent, not a jointly rerouted analysis.
These are nominal candidates for further design, **not** a fit verdict:
confirm antenna extension and alignment, actual module and PCB tolerances,
connector access, mounting head/driver and enclosure/RF clearances first.

## Reproduce

From the repository root, with Docker and the pinned image available:

```
bash hardware/pcb-redesign/v5/routing/esp-orientation-comparison/run.sh
```

The script loads the input read-only in KiCad 10.0.2, checks its hash, runs
tests comparing all four transforms against native pcbnew pad positions,
and replaces `results.json`; it removes KiCad/Python caches afterwards.
It neither saves nor creates a board copy. If the image is not present,
Docker may need to pull the pinned digest first.
