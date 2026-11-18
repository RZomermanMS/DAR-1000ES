#!/usr/bin/env python3
"""Replay the three audio bypass placement and supply-branch edits."""
import hashlib
import sys
from pathlib import Path

import pcbnew as pcb

PLAN = {
    # ref: original position, original angle, new position, new angle, IC, layer
    "C3": ((25, 197), 90, (35, 173.5), 0, "U2", pcb.F_Cu),
    "C4": ((25, 222), 90, (35.3, 199.38), 0, "U6", pcb.B_Cu),
    "C5": ((25, 247), 90, (40, 223), 180, "U7", pcb.B_Cu),
}


def xy(x, y):
    return pcb.VECTOR2I(pcb.FromMM(x), pcb.FromMM(y))


def main(source, output, expected_hash):
    source, output = Path(source), Path(output)
    if source.resolve() == output.resolve() or output.exists():
        raise ValueError("output must be a new file, distinct from source")
    if hashlib.sha256(source.read_bytes()).hexdigest() != expected_hash:
        raise ValueError("unexpected source board hash")
    board = pcb.LoadBoard(str(source))
    fps = {f.GetReference(): f for f in board.GetFootprints()}
    if len(fps) != len(list(board.GetFootprints())):
        raise ValueError("duplicate footprint references")
    for ref, (old, angle, new, new_angle, ic, layer) in PLAN.items():
        f = fps[ref]
        if f.GetPosition() != xy(*old) or f.GetOrientationDegrees() != angle:
            raise ValueError(f"{ref} source placement changed")
        pads = list(f.Pads())
        supply = [p for p in pads if p.GetNetname() == "LOCAL_5V"]
        ground = [p for p in pads if p.GetNetname() == "GND"]
        target = [p for p in fps[ic].Pads() if p.GetNumber() == "14"]
        if len(pads) != 2 or len(supply) != 1 or len(ground) != 1 or len(target) != 1 or target[0].GetNetname() != "LOCAL_5V":
            raise ValueError(f"{ref}/{ic} has unexpected pin/net assignment")
        f.SetOrientationDegrees(new_angle)
        f.SetPosition(xy(*new))
        track = pcb.PCB_TRACK(board)
        track.SetStart(supply[0].GetPosition())
        track.SetEnd(target[0].GetPosition())
        track.SetWidth(pcb.FromMM(0.3))
        track.SetLayer(layer)
        track.SetNetCode(supply[0].GetNetCode())
        board.Add(track)
        if ref == "C4":
            # The removed through-hole pad joined pre-existing F/B supply routes.
            incident = [t for t in board.GetTracks()
                        if type(t) == pcb.PCB_TRACK and t.GetNetname() == "LOCAL_5V"
                        and (t.GetStart() == xy(*old) or t.GetEnd() == xy(*old))]
            if {t.GetLayer() for t in incident} != {pcb.F_Cu, pcb.B_Cu}:
                raise ValueError("C4's former supply junction changed")
            via = pcb.PCB_VIA(board)
            via.SetPosition(xy(*old))
            via.SetWidth(pcb.FromMM(0.8))
            via.SetDrill(pcb.FromMM(0.4))
            via.SetViaType(pcb.VIATYPE_THROUGH)
            via.SetLayerPair(pcb.F_Cu, pcb.B_Cu)
            via.SetNetCode(supply[0].GetNetCode())
            board.Add(via)
    if not pcb.SaveBoard(str(output), board):
        raise OSError("failed to save board")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        raise SystemExit("usage: audio.py SOURCE OUTPUT EXPECTED_SHA256")
    main(*sys.argv[1:])
