#!/usr/bin/env python3
"""Replay a C8 relocation on the exact corrected integrated source board."""
import argparse
import hashlib
from pathlib import Path

import pcbnew as pcb

SOURCE_SHA256 = "c63fa89924e244bbf6bfd92f2c72e6c9d34117106b4bd87cf46f7971078920c5"


def point(x, y):
    return pcb.VECTOR2I(pcb.FromMM(x), pcb.FromMM(y))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.output.exists() or args.source.resolve() == args.output.resolve():
        raise ValueError("output must be new and distinct from source")
    if hashlib.sha256(args.source.read_bytes()).hexdigest() != SOURCE_SHA256:
        raise ValueError("source board hash mismatch")
    board = pcb.LoadBoard(str(args.source))
    footprints = {f.GetReference(): f for f in board.GetFootprints()}
    cap, chip = footprints["C8"], footprints["U10"]
    pads = {p.GetNumber(): p for p in cap.Pads()}
    pins = {p.GetNumber(): p for p in chip.Pads()}
    if (cap.GetPosition() != point(48, 124) or cap.GetOrientationDegrees() != 0
            or pads["1"].GetNetname() != "SONY_5V_SENSE"
            or pads["2"].GetNetname() != "GND"
            or pins["2"].GetPosition() != point(49.27, 102)
            or pins["2"].GetNetname() != "SONY_5V_SENSE"
            or pins["3"].GetPosition() != point(50.54, 102)
            or pins["3"].GetNetname() != "GND"):
        raise ValueError("unexpected source placement or power nets")
    incident = [t for t in board.GetTracks()
                if t.GetStart() in (point(48, 124), point(53, 124))
                or t.GetEnd() in (point(48, 124), point(53, 124))]
    if len(incident) != 3:
        raise ValueError("unexpected copper at original C8")
    candidates = [t for t in board.GetTracks()
                  if t.GetNetname() == "SONY_5V_SENSE" and t.GetLayer() == pcb.F_Cu
                  and t.GetStart() == point(49.27, 102)
                  and t.GetEnd() == point(48.97, 84.8996)
                  and t.GetWidth() == pcb.FromMM(0.3)]
    if len(candidates) != 1:
        raise ValueError("unexpected U10 supply route")
    old = candidates[0]
    junction = point(49.164739, 96)
    old_end = point(48.97, 84.8996)
    old.SetEnd(junction)
    extension = pcb.PCB_TRACK(board)
    extension.SetStart(junction)
    extension.SetEnd(old_end)
    extension.SetWidth(old.GetWidth())
    extension.SetLayer(old.GetLayer())
    extension.SetNetCode(old.GetNetCode())
    board.Add(extension)
    cap.SetOrientationDegrees(270)
    cap.SetPosition(point(45, 96))
    track = pcb.PCB_TRACK(board)
    track.SetStart(pads["1"].GetPosition())
    track.SetEnd(junction)
    track.SetWidth(pcb.FromMM(0.3))
    track.SetLayer(pcb.F_Cu)
    track.SetNetCode(pads["1"].GetNetCode())
    board.Add(track)
    if not pcb.SaveBoard(str(args.output), board):
        raise OSError("failed to save board")


if __name__ == "__main__":
    main()
