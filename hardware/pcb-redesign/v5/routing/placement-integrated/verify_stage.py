#!/usr/bin/env python3
"""Compare each composition step with the independently verified edit."""
import sys
from collections import Counter

import pcbnew as pcb


def tracks(board):
    def sig(t):
        via = isinstance(t, pcb.PCB_VIA)
        a, b = t.GetStart(), t.GetEnd()
        return (type(t).__name__, t.GetNetname(), t.GetLayer(),
                t.GetWidth(pcb.F_Cu) if via else t.GetWidth(),
                t.GetDrillValue() if via else 0, a.x, a.y, b.x, b.y)
    return Counter(sig(t) for t in board.GetTracks())


def footprints(board):
    return {f.GetReference(): (f.GetPosition().x, f.GetPosition().y,
                              f.GetOrientationDegrees(),
                              f.Reference().GetPosition().x, f.Reference().GetPosition().y)
            for f in board.GetFootprints()}


def delta(a, b):
    old, new = tracks(a), tracks(b)
    af, bf = footprints(a), footprints(b)
    if af.keys() != bf.keys():
        raise ValueError("footprint set changed")
    return old - new, new - old, {k: (af[k], bf[k]) for k in af if af[k] != bf[k]}


if __name__ == "__main__":
    if len(sys.argv) != 5:
        raise SystemExit("usage: verify_stage.py SOURCE RESULT REFERENCE_SOURCE REFERENCE_RESULT")
    boards = [pcb.LoadBoard(path) for path in sys.argv[1:]]
    if delta(boards[0], boards[1]) != delta(boards[2], boards[3]):
        raise ValueError("composition step differs from verified independent edit")
    print("Composition step matches verified placement and copper delta.")
