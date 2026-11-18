#!/usr/bin/env python3
"""Replay the controller bypass placement experiment on a compatible board."""
import argparse
from pathlib import Path

import pcbnew as pcb

BASE = Path(__file__).resolve().parent.parent / "integrated-review/clearance-first-corrected/result.kicad_pcb"
REMOVED = {
    "0c0d6d26-6216-4b35-83c2-a8d7ac867958", "bf8d22e7-65c7-44d0-a811-c6802c9943ef",
    "12ab39b5-1bd9-4657-a910-ad9c09a1ea7b", "14363d58-133b-4d5a-9b37-239b36181704",
    "bfb8f0d0-930f-4e21-862d-5e3c4bd645a0",
}


def track_signature(track):
    a, b = track.GetStart(), track.GetEnd()
    width = track.GetWidth(pcb.F_Cu) if isinstance(track, pcb.PCB_VIA) else track.GetWidth()
    return (type(track).__name__, track.GetNetname(), track.GetLayer(), width,
            a.x, a.y, b.x, b.y)


def xy(x, y):
    return pcb.VECTOR2I(pcb.FromMM(x), pcb.FromMM(y))


def apply(source, output):
    if source.resolve() == output.resolve() or output.exists():
        raise ValueError("output must be a new file, distinct from input")
    board = pcb.LoadBoard(str(source))
    baseline = pcb.LoadBoard(str(BASE))
    fps = {f.GetReference(): f for f in board.GetFootprints()}
    base_fps = {f.GetReference(): f for f in baseline.GetFootprints()}
    tracks = {t.m_Uuid.AsString(): t for t in board.GetTracks()}
    for ref, old_y in (("C1", 44), ("C2", 69)):
        fp = fps[ref]
        if fp.GetPosition() != xy(25, old_y) or fp.GetOrientationDegrees() != 90:
            raise ValueError(f"{ref} placement does not match input")
        if sorted(p.GetNumber() for p in fp.Pads()) != ["1", "2"]:
            raise ValueError(f"{ref} pad set differs")
        for pad in fp.Pads():
            net = {"1": "GND", "2": "LOCAL_5V"}.get(pad.GetNumber())
            if pad.GetNetname() != net:
                raise ValueError(f"{ref} pad net differs")
            original = next(p for p in base_fps[ref].Pads() if p.GetNumber() == pad.GetNumber())
            if (pad.GetPosition() != original.GetPosition() or
                    pad.GetSize() != original.GetSize() or pad.GetDrillSize() != original.GetDrillSize() or
                    pad.GetShape() != original.GetShape() or
                    pad.GetLayerSet().FmtBin() != original.GetLayerSet().FmtBin()):
                raise ValueError(f"{ref}.{pad.GetNumber()} pad geometry differs")
            def touching(source_board, source_pad):
                return {t.m_Uuid.AsString(): track_signature(t) for t in source_board.GetTracks()
                        if source_pad.HitTest(t.GetStart()) or source_pad.HitTest(t.GetEnd())}
            if touching(board, pad) != touching(baseline, original):
                raise ValueError(f"{ref}.{pad.GetNumber()} incident tracks differ")
    if not REMOVED <= tracks.keys():
        raise ValueError("expected source tracks absent")
    for key in REMOVED:
        board.Remove(tracks[key])
    for ref, y in (("C1", 24), ("C2", 49)):
        fp = fps[ref]
        fp.SetOrientationDegrees(180)
        fp.SetPosition(xy(30, y))
        fp.Reference().SetPosition(xy(30, y - 2.7))
        via = pcb.PCB_VIA(board)
        via.SetPosition(xy(25, y + 15))
        via.SetWidth(pcb.FromMM(1.8))
        via.SetDrill(pcb.FromMM(0.8))
        via.SetViaType(pcb.VIATYPE_THROUGH)
        via.SetLayerPair(pcb.F_Cu, pcb.B_Cu)
        via.SetNetCode(board.FindNet("LOCAL_5V").GetNetCode())
        board.Add(via)
        segment = pcb.PCB_TRACK(board)
        segment.SetStart(xy(25, y))
        segment.SetEnd(xy(25, y + 3.38))
        segment.SetLayer(pcb.F_Cu)
        segment.SetWidth(pcb.FromMM(0.8))
        segment.SetNetCode(board.FindNet("LOCAL_5V").GetNetCode())
        board.Add(segment)
    pcb.SaveBoard(str(output), board)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    apply(args.source, args.output)
