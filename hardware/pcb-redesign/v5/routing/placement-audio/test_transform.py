#!/usr/bin/env python3
"""Exercise source/output guards and the replayed component pin assignments."""
import hashlib
import sys
from pathlib import Path

import pcbnew as pcb
import transform


def must_fail(source, output):
    try:
        transform.main(source, output)
    except ValueError:
        return
    raise AssertionError("invalid input unexpectedly accepted")


def main(source, saved):
    source, saved = Path(source), Path(saved)
    scratch = saved.with_name("test-replay.kicad_pcb")
    if scratch.exists():
        raise ValueError("scratch output already exists")
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    must_fail(source, source)
    must_fail(source, saved)
    must_fail(saved, scratch)
    try:
        transform.main(source, scratch)
        board = pcb.LoadBoard(str(scratch))
        fps = {f.GetReference(): f for f in board.GetFootprints()}
        for ref, (_, _, position, angle, ic, _) in transform.PLAN.items():
            assert fps[ref].GetPosition() == transform.xy(*position)
            assert fps[ref].GetOrientationDegrees() == angle
            assert next(p for p in fps[ic].Pads() if p.GetNumber() == "14").GetNetname() == "LOCAL_5V"
        assert hashlib.sha256(source.read_bytes()).hexdigest() == source_hash
    finally:
        scratch.unlink(missing_ok=True)
        scratch.with_suffix(".kicad_pro").unlink(missing_ok=True)
        scratch.with_suffix(".kicad_prl").unlink(missing_ok=True)
    print("Replay and fail-closed guards passed.")


if __name__ == "__main__":
    main(*sys.argv[1:])
