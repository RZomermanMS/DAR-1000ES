#!/usr/bin/env python3
"""Relocate C6 and shorten C8's supply branch on the guarded source."""
import argparse
import hashlib
from pathlib import Path

import pcbnew as pcb

SOURCE_HASH = "06f73f9b662897d0822611513cf09feb3f9ccb1c8e08e6cac4ecad31c147810c"


def point(x, y):
    return pcb.VECTOR2I(pcb.FromMM(x), pcb.FromMM(y))


def apply(board):
    fps = {f.GetReference(): f for f in board.GetFootprints()}
    c6, u8 = fps["C6"], fps["U8"]
    c6pads = {p.GetNumber(): p for p in c6.Pads()}
    u8pins = {p.GetNumber(): p for p in u8.Pads()}
    if (c6.GetPosition() != point(55.5, 41.5) or c6.GetOrientationDegrees() % 360 != 0
            or c6pads["1"].GetNetname() != "LOCAL_5V"
            or c6pads["2"].GetNetname() != "GND"
            or u8pins["14"].GetPosition() != point(52.62, 45)
            or u8pins["14"].GetNetname() != "LOCAL_5V"
            or u8pins["7"].GetPosition() != point(45, 60.24)
            or u8pins["7"].GetNetname() != "GND"):
        raise ValueError("unexpected C6/U8 geometry or nets")
    incident = [t for t in board.GetTracks()
                if t.GetStart() in (point(55.5, 41.5), point(60.5, 41.5))
                or t.GetEnd() in (point(55.5, 41.5), point(60.5, 41.5))]
    if (len(incident) != 1 or type(incident[0]) != pcb.PCB_TRACK
            or incident[0].GetNetname() != "LOCAL_5V"
            or incident[0].GetLayer() != pcb.F_Cu
            or incident[0].GetWidth() != pcb.FromMM(.3)
            or incident[0].GetStart() != point(52.62, 45)
            or incident[0].GetEnd() != point(55.5, 41.5)):
        raise ValueError("unexpected copper incident to C6")
    board.Remove(incident[0])
    c6.SetOrientationDegrees(270)
    c6.SetPosition(point(58, 44))
    c6track = pcb.PCB_TRACK(board)
    c6track.SetStart(c6pads["1"].GetPosition())
    c6track.SetEnd(u8pins["14"].GetPosition())
    c6track.SetWidth(pcb.FromMM(.3))
    c6track.SetLayer(pcb.F_Cu)
    c6track.SetNetCode(c6pads["1"].GetNetCode())
    board.Add(c6track)

    cap, chip = fps["C8"], fps["U10"]
    cpads = {p.GetNumber(): p for p in cap.Pads()}
    pins = {p.GetNumber(): p for p in chip.Pads()}
    if (cap.GetPosition() != point(45, 96) or cap.GetOrientationDegrees() % 360 != 270
            or cpads["1"].GetPosition() != point(45, 96)
            or cpads["1"].GetNetname() != "SONY_5V_SENSE"
            or pins["2"].GetPosition() != point(49.27, 102)
            or pins["2"].GetNetname() != "SONY_5V_SENSE"):
        raise ValueError("unexpected C8/U10 geometry or nets")
    def find(a, b):
        return [t for t in board.GetTracks()
                if type(t) == pcb.PCB_TRACK and t.GetNetname() == "SONY_5V_SENSE"
                and t.GetLayer() == pcb.F_Cu and t.GetWidth() == pcb.FromMM(.3)
                and t.GetStart() == point(*a) and t.GetEnd() == point(*b)]
    branch = find((45, 96), (49.164739, 96))
    trunk = find((49.27, 102), (49.164739, 96))
    if len(branch) != 1 or len(trunk) != 1:
        raise ValueError("unexpected C8 supply copper")
    board.Remove(branch[0])
    start = pcb.VECTOR2I(trunk[0].GetStart().x, trunk[0].GetStart().y)
    end = pcb.VECTOR2I(trunk[0].GetEnd().x, trunk[0].GetEnd().y)
    y = pcb.FromMM(98.5)
    x = round(start.x + (end.x - start.x) * (y - start.y) / (end.y - start.y))
    junction = pcb.VECTOR2I(x, y)
    trunk[0].SetEnd(junction)

    def add(a, b):
        t = pcb.PCB_TRACK(board)
        t.SetStart(a)
        t.SetEnd(b)
        t.SetWidth(pcb.FromMM(.3))
        t.SetLayer(pcb.F_Cu)
        t.SetNetCode(cpads["1"].GetNetCode())
        board.Add(t)

    add(junction, end)
    add(cpads["1"].GetPosition(), junction)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.output.exists() or args.source.resolve() == args.output.resolve():
        raise ValueError("output must be new and distinct from source")
    if hashlib.sha256(args.source.read_bytes()).hexdigest() != SOURCE_HASH:
        raise ValueError("source board hash mismatch")
    board = pcb.LoadBoard(str(args.source))
    apply(board)
    if not pcb.SaveBoard(str(args.output), board):
        raise OSError("failed to save board")


if __name__ == "__main__":
    main()
