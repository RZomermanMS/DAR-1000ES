#!/usr/bin/env python3
"""Add the independently found C7-to-U9.7 ground route if DRC passes."""
import subprocess
import sys
from pathlib import Path

import pcbnew as pcb

POINTS = ((32, 264), (30, 272.75), (28.75, 274.75),
          (28, 275.5), (20, 274.24))


def main(board_path, report):
    path = Path(board_path)
    original = path.read_bytes()
    board = pcb.LoadBoard(board_path)
    fps = {f.GetReference(): f for f in board.GetFootprints()}
    for ref, number, xy in (("C7", "2", POINTS[0]), ("U9", "7", POINTS[-1])):
        pads = [p for p in fps[ref].Pads() if p.GetNumber() == number]
        if len(pads) != 1 or pads[0].GetNetname() != "GND" or (
                pads[0].GetPosition().x, pads[0].GetPosition().y) != tuple(
                    pcb.FromMM(x) for x in xy):
            raise ValueError(f"{ref}.{number} differs from trial B")
    ground = board.FindNet("GND")
    for a, b in zip(POINTS, POINTS[1:]):
        t = pcb.PCB_TRACK(board)
        t.SetStart(pcb.VECTOR2I(*(pcb.FromMM(x) for x in a)))
        t.SetEnd(pcb.VECTOR2I(*(pcb.FromMM(x) for x in b)))
        t.SetWidth(pcb.FromMM(0.30))
        t.SetLayer(pcb.F_Cu)
        t.SetNetCode(ground.GetNetCode())
        board.Add(t)
    if not pcb.SaveBoard(board_path, board):
        raise OSError("KiCad failed to save candidate")
    try:
        Path(report).unlink(missing_ok=True)
        subprocess.run(["kicad-cli", "pcb", "drc", "--format", "json", "--severity-all",
                        "--exit-code-violations", "--output", report, board_path], check=True)
    except Exception:
        path.write_bytes(original)
        raise


if __name__ == "__main__":
    main(*sys.argv[1:])
