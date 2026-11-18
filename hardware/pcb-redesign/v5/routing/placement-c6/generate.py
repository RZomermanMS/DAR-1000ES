#!/usr/bin/env python3
"""Relocate C6 and rebuild its affected copper from the corrected source."""
import argparse
import hashlib
from pathlib import Path

import pcbnew as pcb

SOURCE_SHA256 = "c63fa89924e244bbf6bfd92f2c72e6c9d34117106b4bd87cf46f7971078920c5"


def point(x, y):
    return pcb.VECTOR2I(pcb.FromMM(x), pcb.FromMM(y))


def apply(board):
    fps = {f.GetReference(): f for f in board.GetFootprints()}
    cap, chip = fps["C6"], fps["U8"]
    pads = {p.GetNumber(): p for p in cap.Pads()}
    vcc = next(p for p in chip.Pads() if p.GetNumber() == "14")
    if (cap.GetPosition() != point(45, 68) or cap.GetOrientationDegrees() != 0
            or pads["1"].GetNetname() != "LOCAL_5V"
            or pads["2"].GetNetname() != "GND"
            or vcc.GetPosition() != point(52.62, 45)
            or vcc.GetNetname() != "LOCAL_5V"):
        raise ValueError("Unexpected source placement or power nets")
    expected = {
        ("LOCAL_5V", pcb.F_Cu, (45, 68), (45, 69.5), 0.3),
        ("LOCAL_5V", pcb.B_Cu, (45, 68), (41, 64), 0.8),
        ("LOCAL_5V", pcb.B_Cu, (49.68, 72.68), (45, 68), 0.8),
        ("GND", pcb.F_Cu, (50, 52.7), (50, 68), 0.8),
        ("GND", pcb.B_Cu, (50, 70.38), (50, 68), 0.8),
    }

    def signature(track):
        a, b = track.GetStart(), track.GetEnd()
        return (track.GetNetname(), track.GetLayer(),
                (pcb.ToMM(a.x), pcb.ToMM(a.y)), (pcb.ToMM(b.x), pcb.ToMM(b.y)),
                pcb.ToMM(track.GetWidth()))

    incident = [t for t in board.GetTracks()
                if t.GetStart() in (point(45, 68), point(50, 68))
                or t.GetEnd() in (point(45, 68), point(50, 68))]
    if len(incident) != len(expected) or {signature(t) for t in incident} != expected:
        raise ValueError("Unexpected copper incident to C6")
    for t in incident:
        if t.GetNetname() == "GND":
            board.Remove(t)
    cap.SetPosition(point(55.5, 41.5))
    via = pcb.PCB_VIA(board)
    via.SetPosition(point(45, 68))
    via.SetWidth(pcb.FromMM(0.8))
    via.SetDrill(pcb.FromMM(0.4))
    via.SetViaType(pcb.VIATYPE_THROUGH)
    via.SetLayerPair(pcb.F_Cu, pcb.B_Cu)
    via.SetNetCode(pads["1"].GetNetCode())
    board.Add(via)

    def segment(net, layer, width, a, b):
        track = pcb.PCB_TRACK(board)
        track.SetStart(point(*a))
        track.SetEnd(point(*b))
        track.SetWidth(pcb.FromMM(width))
        track.SetLayer(layer)
        track.SetNetCode(net)
        board.Add(track)

    segment(pads["1"].GetNetCode(), pcb.F_Cu, 0.3, (52.62, 45), (55.5, 41.5))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.output.exists() or args.source.resolve() == args.output.resolve():
        raise ValueError("Output must be new and distinct from source")
    if hashlib.sha256(args.source.read_bytes()).hexdigest() != SOURCE_SHA256:
        raise ValueError("Source board hash mismatch")
    board = pcb.LoadBoard(str(args.source))
    apply(board)
    if not pcb.SaveBoard(str(args.output), board):
        raise OSError("Unable to save board")


if __name__ == "__main__":
    main()
