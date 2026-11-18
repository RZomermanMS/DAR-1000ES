#!/usr/bin/env python3
import unittest

import pcbnew as pcb
import compare


class GeometryTest(unittest.TestCase):
    def test_transform_matches_native_pads(self):
        board = pcb.LoadBoard(str(compare.BOARD))
        for ref in compare.ESPS:
            fp = next(f for f in board.GetFootprints() if f.GetReference() == ref)
            origin = compare.xy(fp.GetPosition())
            pads = list(fp.Pads())
            self.assertEqual(len(pads), 44)
            local = [(compare.xy(p.GetPosition())[0] - origin[0],
                      compare.xy(p.GetPosition())[1] - origin[1]) for p in pads]
            for angle in (0, 90, 180, 270):
                fp.SetOrientationDegrees(angle)
                fp.SetPosition(pcb.VECTOR2I(pcb.FromMM(66), pcb.FromMM(170)))
                for p, (x, y) in zip(pads, local):
                    dx, dy = compare.rotate(x, y, angle)
                    actual = compare.xy(p.GetPosition())
                    self.assertAlmostEqual(actual[0], 66 + dx, places=5)
                    self.assertAlmostEqual(actual[1], 170 + dy, places=5)

    def test_projection_and_boundaries(self):
        body = (-1.27, -5, 24.13, 57.74)
        antenna = (-1.27, -10, 24.13, -5)
        for x, y, angle, domain in ((66, 5, 0, (0, 0, 100, 150)),
                                     (86, 295, 180, (0, 150, 100, 300))):
            self.assertTrue(compare.inside(compare.transformed(body, x, y, angle), domain))
            self.assertEqual(compare.overlap(compare.transformed(antenna, x, y, angle),
                                             (0, 0, 100, 300)), 0)
        self.assertAlmostEqual(compare.overlap(compare.transformed(antenna, 66, 6, 0),
                                               (0, 0, 100, 300)), 25.4)

    def test_box_gap(self):
        self.assertEqual(compare.box_gap((0, 0, 1, 1), (2, 1, 3, 2)), 1)
        self.assertEqual(compare.box_gap((0, 0, 1, 1), (0.5, 0.5, 2, 2)), 0)


if __name__ == "__main__":
    unittest.main()
