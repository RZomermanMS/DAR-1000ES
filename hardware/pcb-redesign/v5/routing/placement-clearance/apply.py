#!/usr/bin/env python3
"""Replay reviewed junction moves on the exact placement-integrated board."""
import argparse
import hashlib
import json
from pathlib import Path

import pcbnew as pcb

HERE = Path(__file__).resolve().parent
SHA256 = "06f73f9b662897d0822611513cf09feb3f9ccb1c8e08e6cac4ecad31c147810c"


def xy(p):
    return (p.x, p.y)


def apply(source, output):
    if source.resolve() == output.resolve() or output.exists():
        raise ValueError("Output must be a new file distinct from the source")
    if hashlib.sha256(source.read_bytes()).hexdigest() != SHA256:
        raise ValueError("Unexpected source board hash")
    board = pcb.LoadBoard(str(source))
    if board.GetCopperLayerCount() != 2:
        raise ValueError("Expected two copper layers")
    tracks = list(board.GetTracks())
    by_id = {t.m_Uuid.AsString(): t for t in tracks}
    if len(by_id) != len(tracks):
        raise ValueError("Duplicate track UUID")
    pads = [p for f in board.GetFootprints() for p in f.Pads()]
    moves = json.loads((HERE / "moves.json").read_text())
    if not moves:
        raise ValueError("No recorded moves")
    for step in moves:
        groups = {}
        for change in step["changes"]:
            groups.setdefault(tuple(change["old"]), []).append(change)
        for old, changes in groups.items():
            first = by_id[changes[0]["uuid"]]
            layer = first.GetLayer()
            wanted = {(c["uuid"], c["endpoint"]) for c in changes}
            attached = {(t.m_Uuid.AsString(), ep) for t in tracks if t.IsOnLayer(layer)
                        for ep in ("Start", "End") if xy(getattr(t, "Get" + ep)()) == old}
            if attached != wanted or any(p.IsOnLayer(layer) and
                                         p.HitTest(pcb.VECTOR2I(*old)) for p in pads):
                raise ValueError(f"Unexpected junction topology at {old}")
            for c in changes:
                t = by_id[c["uuid"]]
                if (c["endpoint"] not in ("Start", "End") or
                        isinstance(t, (pcb.PCB_ARC, pcb.PCB_VIA)) or
                        t.GetLayer() != layer or t.GetNetCode() != first.GetNetCode() or
                        xy(getattr(t, "Get" + c["endpoint"])()) != old):
                    raise ValueError(f"Unexpected track at {old}")
        for c in step["changes"]:
            getattr(by_id[c["uuid"]], "Set" + c["endpoint"])(pcb.VECTOR2I(*c["new"]))
        if any(t.GetStart() == t.GetEnd() for t in tracks if not isinstance(t, pcb.PCB_VIA)):
            raise ValueError("Zero-length track")
    if not pcb.SaveBoard(str(output), board) or not output.exists():
        raise OSError("KiCad failed to save output")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    apply(args.source, args.output)
