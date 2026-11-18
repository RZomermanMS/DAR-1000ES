#!/usr/bin/env python3
"""Verify the stored overlay preserves the source and reject unsafe inputs."""
import hashlib
import collections
import subprocess
from pathlib import Path

import pcbnew as pcb

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "decoupling-trial" / "result.kicad_pcb"
RESULT = HERE / "result.kicad_pcb"
NETLIST = HERE.parent.parent / "DAR-1000ES-v5.net.xml"
SCRATCH = [HERE / "test-source.kicad_pcb", HERE / "test-stripped.kicad_pcb",
           HERE / "test-moved.kicad_pcb", HERE / "test-output.kicad_pcb"]
SIDECARS = [p.with_suffix(suffix) for p in SCRATCH for suffix in (".kicad_pro", ".kicad_prl")]


def main():
    if any(p.exists() for p in SCRATCH + SIDECARS):
        raise ValueError("Test scratch paths must not exist")
    original_hash = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    try:
        source = pcb.LoadBoard(str(SOURCE))
        result = pcb.LoadBoard(str(RESULT))
        uuids = {g.m_Uuid.AsString() for g in source.GetDrawings()}
        extras = [g for g in result.GetDrawings() if g.m_Uuid.AsString() not in uuids]
        assert len(extras) == 61
        assert all(g.GetLayer() == pcb.F_SilkS for g in extras)
        assert sum(isinstance(g, pcb.PCB_TEXT) for g in extras) == 60
        for g in extras:
            result.Remove(g)
        pcb.SaveBoard(str(SCRATCH[0]), source)
        pcb.SaveBoard(str(SCRATCH[1]), result)
        assert SCRATCH[0].read_bytes() == SCRATCH[1].read_bytes(), "non-overlay board data changed"

        j4 = next(f for f in source.GetFootprints() if f.GetReference() == "J4")
        j4.SetPosition(j4.GetPosition() + pcb.VECTOR2I(pcb.FromMM(1), 0))
        pcb.SaveBoard(str(SCRATCH[2]), source)
        command = ["python3", str(HERE / "apply_silk.py"), str(SCRATCH[2]),
                   str(SCRATCH[3]), str(NETLIST)]
        failed = subprocess.run(command, capture_output=True, text=True)
        assert failed.returncode != 0 and not SCRATCH[3].exists(), "moved connector accepted"
        command[2] = str(RESULT)
        failed = subprocess.run(command, capture_output=True, text=True)
        assert failed.returncode != 0 and not SCRATCH[3].exists(), "duplicate overlay accepted"
        command[2] = str(SOURCE)
        subprocess.run(command, check=True, capture_output=True, text=True)
        generated = pcb.LoadBoard(str(SCRATCH[3]))
        def overlay(board):
            return collections.Counter(
                (g.GetText(), g.GetPosition().x, g.GetPosition().y,
                 g.GetTextAngle().AsDegrees(), g.GetTextWidth(), g.GetTextHeight(),
                 g.GetTextThickness())
                for g in board.GetDrawings() if isinstance(g, pcb.PCB_TEXT))
        assert overlay(generated) == overlay(pcb.LoadBoard(str(RESULT))), "regenerated text differs"
        assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == original_hash
        print("PASS: overlay-only diff, reproducible text, moved connector/duplicate rejection, source unchanged")
    finally:
        for path in SCRATCH + SIDECARS:
            path.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
