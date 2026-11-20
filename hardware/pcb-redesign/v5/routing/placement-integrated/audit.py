#!/usr/bin/env python3
"""Audit the saved composed board and record exact bypass geometry."""
import importlib.util
import json
import os
from pathlib import Path

import pcbnew as pcb

HERE = Path(os.environ.get("OUTPUT_DIR", Path(__file__).resolve().parent))
R = HERE.parent
SOURCE = R / "placement-c6/result.kicad_pcb"
BOARD = HERE / "result.kicad_pcb"
PLAN = {"C1": (30, 24, 180), "C2": (30, 49, 180),
        "C3": (35, 173.5, 0), "C4": (35.3, 199.38, 0),
        "C5": (40, 223, 180), "C8": (45, 96, 270)}


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    power = load("power_audit", R / "power-rework/audit.py")
    detail = load("controller_audit", R / "placement-controller/audit.py")
    old = pcb.LoadBoard(str(SOURCE))
    board = pcb.LoadBoard(str(BOARD))
    normalized = pcb.LoadBoard(str(BOARD))
    original = {f.GetReference(): f for f in old.GetFootprints()}
    actual = {f.GetReference(): f for f in board.GetFootprints()}
    for f in normalized.GetFootprints():
        ref = f.GetReference()
        if ref not in PLAN:
            continue
        x, y, angle = PLAN[ref]
        if (f.GetPosition() != pcb.VECTOR2I(pcb.FromMM(x), pcb.FromMM(y))
                or f.GetOrientationDegrees() % 360 != angle):
            raise ValueError(f"{ref} placement was not saved")
        f.SetOrientationDegrees(original[ref].GetOrientationDegrees())
        f.SetPosition(original[ref].GetPosition())
    if detail.placements(old) != detail.placements(normalized):
        raise ValueError("unexpected footprint or pad geometry/net change")
    power.SOURCE, power.BOARD, power.HERE = SOURCE, BOARD, HERE
    power.placements = lambda b: None
    power.main()
    report = json.loads((HERE / "audit.json").read_text())
    report.pop("unchanged_footprint_positions_and_pad_nets")
    report["only_authorized_additional_placements_and_pad_geometry_unchanged"] = True
    report["moved_capacitors"] = {}
    for ref in ("C1", "C2", "C3", "C4", "C5", "C6", "C8"):
        f = actual[ref]
        report["moved_capacitors"][ref] = {
            "position_mm": [pcb.ToMM(f.GetPosition().x), pcb.ToMM(f.GetPosition().y)],
            "orientation_degrees": f.GetOrientationDegrees() % 360,
            "pads_mm": {p.GetNumber(): [pcb.ToMM(p.GetPosition().x), pcb.ToMM(p.GetPosition().y)]
                        for p in f.Pads()}}
    (HERE / "audit.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
