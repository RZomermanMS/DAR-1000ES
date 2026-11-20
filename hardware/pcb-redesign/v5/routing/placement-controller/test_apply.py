#!/usr/bin/env python3
"""Replay preconditions; run inside the KiCad container."""
import unittest
import subprocess
import sys
from pathlib import Path

import pcbnew as pcb
import apply

HERE = Path(__file__).resolve().parent
SOURCE = apply.BASE


class ReplayTests(unittest.TestCase):
    def replay(self, source, output):
        return subprocess.run([sys.executable, str(HERE / "apply.py"), str(source), str(output)],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    def setUp(self):
        self.files = [HERE / "test-input.kicad_pcb", HERE / "test-output.kicad_pcb"]
        if any(p.exists() or p.with_suffix(".kicad_pro").exists() for p in self.files):
            raise RuntimeError("test files already exist")

    def tearDown(self):
        for path in self.files:
            for suffix in (".kicad_pcb", ".kicad_pro", ".kicad_prl"):
                path.with_suffix(suffix).unlink(missing_ok=True)

    def test_replay_and_refuse_reapplication(self):
        self.replay(SOURCE, self.files[1])
        board = pcb.LoadBoard(str(self.files[1]))
        for ref, y in (("C1", 24), ("C2", 49)):
            fp = next(f for f in board.GetFootprints() if f.GetReference() == ref)
            self.assertEqual(fp.GetPosition(), apply.xy(30, y))
        with self.assertRaises(subprocess.CalledProcessError):
            self.replay(self.files[1], self.files[0])
        with self.assertRaises(subprocess.CalledProcessError):
            self.replay(SOURCE, self.files[1])
        with self.assertRaises(subprocess.CalledProcessError):
            self.replay(SOURCE, SOURCE)

    def test_incident_trace_mutation_rejected(self):
        board = pcb.LoadBoard(str(SOURCE))
        track = next(t for t in board.GetTracks() if t.m_Uuid.AsString() in apply.REMOVED)
        track.SetWidth(track.GetWidth() + pcb.FromMM(0.01))
        pcb.SaveBoard(str(self.files[0]), board)
        with self.assertRaises(subprocess.CalledProcessError):
            self.replay(self.files[0], self.files[1])

    def test_pad_geometry_mutation_rejected(self):
        board = pcb.LoadBoard(str(SOURCE))
        fp = next(f for f in board.GetFootprints() if f.GetReference() == "C1")
        pad = next(p for p in fp.Pads() if p.GetNumber() == "1")
        pad.SetSize(apply.xy(1.7, 1.7))
        pcb.SaveBoard(str(self.files[0]), board)
        with self.assertRaises(subprocess.CalledProcessError):
            self.replay(self.files[0], self.files[1])


if __name__ == "__main__":
    unittest.main()
