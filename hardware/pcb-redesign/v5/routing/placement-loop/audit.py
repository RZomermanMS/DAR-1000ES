#!/usr/bin/env python3
"""Check saved board against source and audit domains, planes and bypasses."""
import importlib.util
import json
import os
from pathlib import Path

import pcbnew as pcb

HERE = Path(__file__).resolve().parent
R = HERE.parent
OUT = Path(os.environ["OUTPUT_DIR"])
SOURCE = R / "placement-integrated/result.kicad_pcb"
BOARD = OUT / "result.kicad_pcb"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


power = load("power_audit", R / "power-rework/audit.py")
detail = load("detail_audit", R / "placement-controller/audit.py")
source, board = pcb.LoadBoard(str(SOURCE)), pcb.LoadBoard(str(BOARD))
normalized = pcb.LoadBoard(str(BOARD))
original = next(f for f in source.GetFootprints() if f.GetReference() == "C6")
cap = next(f for f in normalized.GetFootprints() if f.GetReference() == "C6")
if (cap.GetPosition() != pcb.VECTOR2I(pcb.FromMM(58), pcb.FromMM(44))
        or cap.GetOrientationDegrees() % 360 != 270):
    raise ValueError("C6 placement was not saved")
cap.SetOrientationDegrees(original.GetOrientationDegrees())
cap.SetPosition(original.GetPosition())
if detail.placements(source) != detail.placements(normalized):
    raise ValueError("unexpected footprint or pad geometry/net change")
power.SOURCE, power.BOARD, power.HERE = SOURCE, BOARD, OUT
power.placements = lambda b: None
power.main()
report = json.loads((OUT / "audit.json").read_text())
report.pop("unchanged_footprint_positions_and_pad_nets")
report["only_c6_moved_and_pad_geometry_unchanged"] = True
report["c6_position_mm"] = [58, 44]
report["c6_orientation_degrees"] = 270
ground = next(p for p in report["pairs"] if p["capacitor"] == "C6" and p["net"] == "GND")
if ground["pad_centers_mm"] >= 24.319:
    raise ValueError("C6 ground pad separation did not improve")
pair = next(p for p in report["pairs"] if p["capacitor"] == "C8" and p["net"] == "SONY_5V_SENSE")
if pair["track_only_shortest_mm"] is None or pair["track_only_shortest_mm"] >= 10.166:
    raise ValueError("C8 supply path did not improve")
(OUT / "audit.json").write_text(json.dumps(report, indent=2) + "\n")
