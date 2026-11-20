#!/usr/bin/env python3
"""Move one junction in the newly added C6 branch; reject topology changes."""
import argparse
from pathlib import Path

import pcbnew as pcb

HERE = Path(__file__).resolve().parent
BASE = HERE.parent.parent / "decoupling-trial/result.kicad_pcb"


def point(x, y):
    return pcb.VECTOR2I(pcb.FromMM(x), pcb.FromMM(y))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.output.exists() or args.source.resolve() == args.output.resolve():
        raise ValueError("Output must be new and distinct from input")
    board = pcb.LoadBoard(str(args.source))
    base = pcb.LoadBoard(str(BASE))
    ids = {x.m_Uuid.AsString() for x in base.GetTracks()}
    old, new = point(46.5, 72.5), point(46.5, 72.6)
    expected = {(46.5, 73.5, 46.5, 72.5), (46.5, 72.5, 47.0, 72.0)}
    attached = [t for t in board.GetTracks() if t.IsOnLayer(pcb.F_Cu)
                and (t.GetStart() == old or t.GetEnd() == old)]
    def geom(t):
        a, b = t.GetStart(), t.GetEnd()
        return tuple(round(pcb.ToMM(v), 4) for v in (a.x, a.y, b.x, b.y))
    if len(attached) != 2 or {geom(t) for t in attached} != expected:
        raise ValueError("Unexpected C6 branch junction topology")
    if any(t.m_Uuid.AsString() in ids or t.GetNetname() != "LOCAL_5V"
           or t.GetLayer() != pcb.F_Cu or t.GetWidth() != pcb.FromMM(0.3)
           or isinstance(t, (pcb.PCB_ARC, pcb.PCB_VIA)) for t in attached):
        raise ValueError("Junction is not exactly the new power branch")
    if any(p.IsOnLayer(pcb.F_Cu) and (p.HitTest(old) or p.HitTest(new))
           for f in board.GetFootprints() for p in f.Pads()):
        raise ValueError("Junction touches a pad")
    if any(t not in attached and t.IsOnLayer(pcb.F_Cu)
           and (t.GetStart() == new or t.GetEnd() == new) for t in board.GetTracks()):
        raise ValueError("Destination is another track junction")
    for t in attached:
        if t.GetStart() == old:
            t.SetStart(new)
        else:
            t.SetEnd(new)
    if not pcb.SaveBoard(str(args.output), board):
        raise OSError("KiCad failed to save repaired board")
    print("Moved C6 branch junction from (46.5,72.5) to (46.5,72.6) mm.")


if __name__ == "__main__":
    main()
