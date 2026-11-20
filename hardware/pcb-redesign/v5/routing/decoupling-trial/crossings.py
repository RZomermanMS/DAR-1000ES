#!/usr/bin/env python3
"""List track-centerline crossings at the section boundary, not a corridor audit."""
import json
import sys

import pcbnew as pcb

board = pcb.LoadBoard(sys.argv[1])
y = pcb.FromMM(150)
crossings = []
for track in board.GetTracks():
    if isinstance(track, pcb.PCB_VIA):
        continue
    a, b = track.GetStart(), track.GetEnd()
    if a.y == b.y == y:
        crossings.append({"net": track.GetNetname(), "layer": board.GetLayerName(track.GetLayer()),
                          "x_mm": [pcb.ToMM(min(a.x, b.x)), pcb.ToMM(max(a.x, b.x))]})
    elif a.y != b.y and min(a.y, b.y) <= y <= max(a.y, b.y):
        x = a.x + (b.x - a.x) * (y - a.y) / (b.y - a.y)
        crossings.append({"net": track.GetNetname(), "layer": board.GetLayerName(track.GetLayer()),
                          "x_mm": round(pcb.ToMM(round(x)), 6)})
print(json.dumps(sorted(crossings, key=lambda x: (x["net"], str(x["x_mm"]))), indent=2))
