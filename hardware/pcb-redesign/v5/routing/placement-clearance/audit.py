#!/usr/bin/env python3
"""Run placement, netlist, section, fill and bypass checks on the derivative."""
import importlib.util
import os
from pathlib import Path

import pcbnew as pcb

HERE = Path(os.environ.get("OUTPUT_DIR", Path(__file__).resolve().parent))
R = HERE.parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    source = R / "placement-integrated/result.kicad_pcb"
    board = HERE / "result.kicad_pcb"
    detail = load("detail_audit", R / "placement-controller/audit.py")
    if detail.placements(pcb.LoadBoard(str(source))) != detail.placements(pcb.LoadBoard(str(board))):
        raise ValueError("Footprint or pad geometry changed")
    power = load("power_audit", R / "power-rework/audit.py")
    power.SOURCE, power.BOARD, power.HERE = source, board, HERE
    power.main()


if __name__ == "__main__":
    main()
