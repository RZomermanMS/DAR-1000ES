#!/usr/bin/env python3
"""Verify guards, changed copper, and the intended saved pad geometry."""
import importlib.util
from pathlib import Path
import unittest

import pcbnew as pcb

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "placement-integrated/result.kicad_pcb"
spec = importlib.util.spec_from_file_location("transform", HERE / "transform.py")
transform = importlib.util.module_from_spec(spec)
spec.loader.exec_module(transform)


class TransformTest(unittest.TestCase):
    def test_exact_local_changes_and_reapplication_guard(self):
        board = pcb.LoadBoard(str(SOURCE))
        def tracks():
            return {t.m_Uuid.AsString(): (t.GetNetname(), t.GetLayer(),
                    t.GetStart().x, t.GetStart().y, t.GetEnd().x, t.GetEnd().y,
                    t.GetWidth(pcb.F_Cu) if isinstance(t, pcb.PCB_VIA) else t.GetWidth())
                    for t in board.GetTracks()}
        before = tracks()
        transform.apply(board)
        after = tracks()
        removed = before.keys() - after.keys()
        changed = {k for k in before.keys() & after.keys() if before[k] != after[k]}
        added = after.keys() - before.keys()
        self.assertEqual((len(removed), len(changed), len(added)), (2, 1, 3))
        self.assertEqual({before[k][0] for k in removed}, {"LOCAL_5V", "SONY_5V_SENSE"})
        self.assertEqual({before[k][0] for k in changed}, {"SONY_5V_SENSE"})
        self.assertEqual({after[k][0] for k in added}, {"LOCAL_5V", "SONY_5V_SENSE"})
        cap = next(f for f in board.GetFootprints() if f.GetReference() == "C6")
        pads = {p.GetNumber(): p for p in cap.Pads()}
        self.assertEqual(pads["1"].GetPosition(), transform.point(58, 44))
        self.assertEqual(pads["2"].GetPosition(), transform.point(58, 49))
        with self.assertRaises(ValueError):
            transform.apply(board)


if __name__ == "__main__":
    unittest.main()
