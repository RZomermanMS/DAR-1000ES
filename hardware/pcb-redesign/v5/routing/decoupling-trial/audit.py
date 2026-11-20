#!/usr/bin/env python3
"""Verify trial-B placement, v5 netlist and section rules on this candidate."""
import importlib.util
import json
import sys
from pathlib import Path

import pcbnew as pcb

ops_path = Path(__file__).resolve().parent.parent / "placement-trial" / "board_ops.py"
spec = importlib.util.spec_from_file_location("board_ops", ops_path)
ops = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ops)


def snapshot(board):
    return sorted((f.GetReference(), f.GetFPIDAsString(), f.GetPosition().x,
                   f.GetPosition().y, f.GetOrientationDegrees(),
                   tuple(sorted((p.GetNumber(), p.GetPosition().x, p.GetPosition().y,
                                 p.GetNetname()) for p in f.Pads())))
                  for f in board.GetFootprints())


baseline = pcb.LoadBoard(sys.argv[1])
board = pcb.LoadBoard(sys.argv[2])
if snapshot(baseline) != snapshot(board):
    raise ValueError("footprint or pad placement changed")
ops.verify_netlist(board, sys.argv[3])
ops.verify_uart(sys.argv[3])
ops.audit_sections(board, 150, "lower")
ops.audit_component_envelopes(board, 150, "lower")
def zones(b):
    return sorted((z.GetIsRuleArea(), z.GetBoundingBox().GetX(), z.GetBoundingBox().GetY(),
                   z.GetBoundingBox().GetWidth(), z.GetBoundingBox().GetHeight(),
                   z.GetDoNotAllowTracks(), z.GetDoNotAllowVias(), z.GetDoNotAllowPads(),
                   z.GetDoNotAllowZoneFills(), z.GetDoNotAllowFootprints())
                  for z in b.Zones())


if len(zones(board)) != 2 or zones(board) != zones(baseline):
    raise ValueError("antenna rule area bounding boxes or restrictions changed")
tracks = list(board.GetTracks())
segments = [t for t in tracks if not isinstance(t, pcb.PCB_VIA)]
if not segments or min(t.GetWidth() for t in segments) < pcb.FromMM(0.25):
    raise ValueError("undersize or missing tracks")
print("Footprint/pad placement unchanged from B; v5 netlist and UART nodes match.")
print(json.dumps({"segments": len(segments), "vias": len(tracks) - len(segments),
                  "minimum_track_width_mm": pcb.ToMM(min(t.GetWidth() for t in segments))}))
