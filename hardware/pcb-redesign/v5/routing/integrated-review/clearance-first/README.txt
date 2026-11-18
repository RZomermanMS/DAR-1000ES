Clearance-first composition — FAILED DRC; NOT FOR FABRICATION OR POWER-UP
=========================================================================

This is the retained, uncorrected conflict reproduction, separate from the
passing power+silk candidate in the parent directory and the locally
corrected candidate in ../clearance-first-corrected/. It is NOT a passing
board. The clearance replay preflight ran on the unzoned decoupling board,
and its output was byte-identical to the saved clearance-rework result.
The original power generator was then run on that output with its zone and
branch preconditions intact, followed by the original silk preflight.

The refilled KiCad 10.0.2 DRC reports two F.Cu clearance errors, both
0.1950 mm against the required 0.2000 mm: the new LOCAL_5V C6 branch
segment from (46.5,72.5) to (47,72) meets two ENABLE_U3 track segments
near (46.4953,71.8047). parity.json also contains the two DRC violations
but zero schematic parity issues; both exit codes are 5. There are zero
unconnected items. See drc.json for exact UUIDs and locations.

result.kicad_pcb SHA-256:
  74674474efe62d6e1b0cb38e13fb2255c36fdc5ee8df994890e329cd232bbae5
verification.json records this same hash before and after read-only DRC.
audit.json contains the netlist, exact UART, domain/envelope, placement,
zone and thermal-sampling checks. Filled GND zones have three F.Cu and
twelve B.Cu polygons, none flagged as islands. Four inherited checks are
ignored as listed in DRC reports. The actual native pad-to-unrelated-track/
via measurement finds 144 pairs below 0.30 mm, minimum 0.201700 mm;
baseline-comparison.json compares against 332 pairs in the decoupling
source and comparison.json against 142 in clearance-rework. The two
extra sub-0.30 mm pairs are newly added power-track pairs. This measurement
does not cover track-to-track DRC, zones, pad-pad, non-PTH holes or physical
assembly; its passing minimum does not negate the DRC failures.

Reproduction from repository root: verify inputs.sha256, remove only this
directory's result.kicad_pcb, then run `bash
hardware/pcb-redesign/v5/routing/integrated-review/clearance-first/build.sh`.
The script records both failing DRC exit codes and all audits before
returning a nonzero status. Generated UUIDs and hashes vary. Re-run
verification and update manifests and recorded hashes after regeneration.
The project is restored before DRC because KiCad can synthesize a default
project when saving intermediate boards. Do not waive failed preconditions.

Capacitor positions remain unchanged; power bypass locality is unresolved.
RF geometry and performance, current return paths, physical fit and safety
remain unverified. No manufacturing or fabrication readiness is claimed.
