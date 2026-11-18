#!/usr/bin/env python3
"""Replay reviewed endpoint moves on a compatible integrated KiCad board."""
import argparse
import json
from pathlib import Path

import pcbnew as pcb

HERE = Path(__file__).resolve().parent
REFERENCE = HERE.parent / "decoupling-trial/result.kicad_pcb"


def xy(p):
    return (p.x, p.y)


def signature(t):
    return (type(t).__name__, t.GetLayer(), t.GetNetname(), t.GetWidth(),
            xy(t.GetStart()), xy(t.GetEnd()))


def on_segment(point, t):
    a, b = xy(t.GetStart()), xy(t.GetEnd())
    return ((point[0] - a[0]) * (b[1] - a[1]) == (point[1] - a[1]) * (b[0] - a[0])
            and min(a[0], b[0]) <= point[0] <= max(a[0], b[0])
            and min(a[1], b[1]) <= point[1] <= max(a[1], b[1]))


def transform(source, output):
    if source.resolve() == output.resolve():
        raise ValueError("input and output must be different files")
    moves = json.loads((HERE / "moves.json").read_text())
    reference = pcb.LoadBoard(str(REFERENCE))
    board = pcb.LoadBoard(str(source))
    if board.GetCopperLayerCount() != 2 or any(not z.GetIsRuleArea() for z in board.Zones()):
        raise ValueError("expected two copper layers and no copper zones")
    tracks = list(board.GetTracks())
    by_id = {t.m_Uuid.AsString(): t for t in tracks}
    original = {t.m_Uuid.AsString(): t for t in reference.GetTracks()}
    changed_ids = {c["uuid"] for step in moves for c in step["changes"]}
    for uuid in changed_ids:
        if uuid not in by_id or signature(by_id[uuid]) != signature(original[uuid]):
            raise ValueError(f"changed or missing source track {uuid}")
    pads = [p for f in board.GetFootprints() for p in f.Pads()]
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
            if attached != wanted:
                raise ValueError(f"unexpected junction topology at {old}: {attached ^ wanted}")
            if any(p.IsOnLayer(layer) and p.HitTest(pcb.VECTOR2I(*old)) for p in pads):
                raise ValueError(f"junction touches pad at {old}")
            for t in tracks:
                if (t.IsOnLayer(layer) and t.GetNetCode() == first.GetNetCode()
                    and t.m_Uuid.AsString() not in {c["uuid"] for c in changes}
                    and not isinstance(t, (pcb.PCB_ARC, pcb.PCB_VIA))
                    and on_segment(old, t)):
                    raise ValueError(f"junction crosses another track at {old}")
            for c in changes:
                t = by_id[c["uuid"]]
                if (isinstance(t, (pcb.PCB_ARC, pcb.PCB_VIA))
                    or t.GetLayer() != layer or t.GetNetCode() != first.GetNetCode()
                    or xy(getattr(t, "Get" + c["endpoint"])()) != old):
                    raise ValueError(f"unexpected track at junction {old}")
        for c in step["changes"]:
            getattr(by_id[c["uuid"]], "Set" + c["endpoint"])(pcb.VECTOR2I(*c["new"]))
    if not pcb.SaveBoard(str(output), board):
        raise OSError("KiCad failed to save output")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    transform(args.source, args.output)


if __name__ == "__main__":
    main()
