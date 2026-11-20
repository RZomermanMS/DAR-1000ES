#!/usr/bin/env python3
"""Replay the locally guarded loop edit after the exact clearance edit."""
import hashlib
import importlib.util
import sys
from pathlib import Path

import pcbnew as pcb

R = Path(__file__).resolve().parent.parent


def main(source, output, expected_hash):
    source, output = Path(source), Path(output)
    if source.resolve() == output.resolve() or output.exists():
        raise ValueError("Output must be new and distinct from source")
    if hashlib.sha256(source.read_bytes()).hexdigest() != expected_hash:
        raise ValueError("Clearance-stage hash mismatch")
    spec = importlib.util.spec_from_file_location("loop_transform", R / "placement-loop/transform.py")
    loop = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loop)
    board = pcb.LoadBoard(str(source))
    loop.apply(board)
    if not pcb.SaveBoard(str(output), board) or not output.exists():
        raise OSError("KiCad failed to save output")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        raise SystemExit("usage: compose.py CLEARANCE_STAGE OUTPUT EXPECTED_SHA256")
    main(*sys.argv[1:])
