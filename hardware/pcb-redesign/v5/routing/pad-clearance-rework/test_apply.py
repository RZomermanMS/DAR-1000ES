#!/usr/bin/env python3
"""Replay, compatibility, and conflict tests; scratch stays in this directory."""
import json
import shutil
import unittest
from pathlib import Path

import pcbnew as pcb
from apply import HERE, REFERENCE, transform


class ReplayTests(unittest.TestCase):
    def setUp(self):
        self.work = HERE / "test-work"
        self.work.mkdir(exist_ok=False)

    def tearDown(self):
        shutil.rmtree(self.work)

    def test_exact_replay(self):
        output = self.work / "replay.kicad_pcb"
        transform(REFERENCE, output)
        self.assertEqual(output.read_bytes(), (HERE / "result.kicad_pcb").read_bytes())

    def test_preserves_unrelated_integrated_change(self):
        source = self.work / "input.kicad_pcb"
        output = self.work / "output.kicad_pcb"
        text = REFERENCE.read_text()
        text = text.replace('(title "', '(title "integrated-', 1)
        self.assertNotEqual(text, REFERENCE.read_text())
        source.write_text(text)
        transform(source, output)
        self.assertIn('(title "integrated-', output.read_text())

    def test_changed_track_rejected_without_output(self):
        source = self.work / "input.kicad_pcb"
        output = self.work / "output.kicad_pcb"
        moves = json.loads((HERE / "moves.json").read_text())
        uuid = moves[0]["changes"][0]["uuid"]
        board = pcb.LoadBoard(str(REFERENCE))
        track = next(t for t in board.GetTracks() if t.m_Uuid.AsString() == uuid)
        track.SetWidth(track.GetWidth() + pcb.FromMM(.01))
        pcb.SaveBoard(str(source), board)
        with self.assertRaisesRegex(ValueError, "changed or missing source track"):
            transform(source, output)
        self.assertFalse(output.exists())

    def test_extra_junction_branch_rejected(self):
        source = self.work / "input.kicad_pcb"
        output = self.work / "output.kicad_pcb"
        moves = json.loads((HERE / "moves.json").read_text())
        change = moves[0]["changes"][0]
        board = pcb.LoadBoard(str(REFERENCE))
        original = next(t for t in board.GetTracks() if t.m_Uuid.AsString() == change["uuid"])
        track = pcb.PCB_TRACK(board)
        x, y = change["old"]
        track.SetStart(pcb.VECTOR2I(x, y))
        track.SetEnd(pcb.VECTOR2I(x + pcb.FromMM(1), y))
        track.SetLayer(original.GetLayer())
        track.SetNetCode(original.GetNetCode())
        track.SetWidth(original.GetWidth())
        board.Add(track)
        pcb.SaveBoard(str(source), board)
        with self.assertRaisesRegex(ValueError, "unexpected junction topology"):
            transform(source, output)
        self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
