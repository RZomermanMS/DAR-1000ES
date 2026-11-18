#!/usr/bin/env python3
"""Report straight-line pad distances, not routed loop lengths or electrical approval."""
import math
import sys

import pcbnew as pcb

PAIRS = {
    "C1": "U3", "C2": "U4", "C3": "U2", "C4": "U6", "C5": "U7",
    "C6": "U8", "C7": "U9", "C8": "U10", "C14": "U11",
    "C10": "U1-CONTROLLER1", "C11": "U1-CONTROLLER1",
    "C12": "U6-AUDIO1", "C13": "U6-AUDIO1",
}

board = pcb.LoadBoard(sys.argv[1])
fps = {f.GetReference(): f for f in board.GetFootprints()}
for cap, target in PAIRS.items():
    parts = []
    for pad in fps[cap].Pads():
        net = pad.GetNetname()
        targets = [p for p in fps[target].Pads() if p.GetNetname() == net]
        if not targets:
            parts.append(f"{net}: no same-net target pad")
            continue
        point = pad.GetPosition()
        nearest = min(math.hypot(p.GetPosition().x - point.x, p.GetPosition().y - point.y)
                      for p in targets)
        parts.append(f"{net}: {pcb.ToMM(round(nearest)):.2f} mm")
    print(f"{cap} -> {target}: " + "; ".join(parts))
