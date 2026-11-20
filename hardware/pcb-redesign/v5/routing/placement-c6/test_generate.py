#!/usr/bin/env python3
"""Check replay guards and C6 pad positions."""
from pathlib import Path
import pcbnew as pcb
import generate

source = Path(__file__).resolve().parent.parent / "integrated-review/clearance-first-corrected/result.kicad_pcb"
board = pcb.LoadBoard(str(source))
generate.apply(board)
cap = next(f for f in board.GetFootprints() if f.GetReference() == "C6")
assert {p.GetNumber(): (pcb.ToMM(p.GetPosition().x), pcb.ToMM(p.GetPosition().y), p.GetNetname())
        for p in cap.Pads()} == {
            "1": (55.5, 41.5, "LOCAL_5V"), "2": (60.5, 41.5, "GND")}
try:
    generate.apply(board)
except ValueError:
    pass
else:
    raise AssertionError("Reapplying to a modified board must fail")
print("C6 replay and duplicate-application guard passed.")
