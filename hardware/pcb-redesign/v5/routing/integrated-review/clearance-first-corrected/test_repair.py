#!/usr/bin/env python3
"""Exercise the guarded junction repair on actual candidate boards."""
import hashlib
import subprocess
import sys
from pathlib import Path

import pcbnew as pcb

HERE = Path(__file__).resolve().parent
source, result = map(Path, sys.argv[1:3])
scratch = HERE / "test-repair.kicad_pcb"
sidecars = [scratch.with_suffix(s) for s in (".kicad_pro", ".kicad_prl")]
if any(p.exists() for p in [scratch] + sidecars):
    raise ValueError("Test scratch path already exists")
digest = hashlib.sha256(source.read_bytes()).hexdigest()


def tracks(path):
    board = pcb.LoadBoard(str(path))
    return {t.m_Uuid.AsString(): (t.GetStart().x, t.GetStart().y,
                                 t.GetEnd().x, t.GetEnd().y, t.GetNetname(),
                                 t.GetLayer(), t.GetWidth()) for t in board.GetTracks()}


def run(inp, out):
    return subprocess.run([sys.executable, str(HERE / "repair.py"), str(inp), str(out)],
                          capture_output=True, text=True)


try:
    before, after = tracks(source), tracks(result)
    assert before.keys() == after.keys()
    changed = [key for key in before if before[key] != after[key]]
    assert len(changed) == 2, f"Unexpected changed tracks: {changed}"
    for key in changed:
        old, new = before[key], after[key]
        assert old[4:] == new[4:]
        assert sorted((old[0:2], old[2:4])) != sorted((new[0:2], new[2:4]))
    assert run(result, scratch).returncode != 0 and not scratch.exists()
    assert run(source, source).returncode != 0
    replay = run(source, scratch)
    assert replay.returncode == 0, replay.stderr
    assert tracks(scratch) == after
    assert run(source, scratch).returncode != 0
    assert hashlib.sha256(source.read_bytes()).hexdigest() == digest
    print("PASS: exactly two branch segments changed; replay and preflight rejection.")
finally:
    for path in [scratch] + sidecars:
        path.unlink(missing_ok=True)
