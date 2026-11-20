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

    def assert_box_almost_equal(self, actual, expected):
        for a, b in zip(actual, expected):
            self.assertAlmostEqual(a, b, places=6)

    def test_carrier_rotations(self):
        expected = ((64.73, 3.6, 90.13, 66.34),
                    (64.6, -19.13, 127.34, 6.27),
                    (41.87, -56.34, 67.27, 6.4),
                    (4.66, 3.73, 67.4, 29.13))
        for angle, box in zip((0, 90, 180, 270), expected):
            self.assert_box_almost_equal(compare.transformed(compare.CARRIER, 66, 5, angle), box)

    def test_existing_candidates_and_exact_flush(self):
        for x, y, angle, domain, box in (
                (66, 5, 0, (0, 0, 100, 150), (64.73, 3.6, 90.13, 66.34)),
                (86, 295, 180, (0, 150, 100, 300), (61.87, 233.66, 87.27, 296.4))):
            actual = compare.transformed(compare.CARRIER, x, y, angle)
            self.assert_box_almost_equal(actual, box)
            self.assertTrue(compare.inside(actual, domain))
            self.assertAlmostEqual(compare.radio_end_edge_distance(actual, angle), 3.6)
        for x, y, angle in ((66, 1.4, 0), (86, 298.6, 180)):
            self.assertAlmostEqual(compare.radio_end_edge_distance(
                compare.transformed(compare.CARRIER, x, y, angle), angle), 0)

    def test_usb_access_is_opposite_pin_one_end(self):
        for angle in (0, 90, 180, 270):
            body = compare.transformed(compare.CARRIER, 66, 170, angle)
            usb = compare.transformed(compare.USB_ACCESS, 66, 170, angle)
            self.assertAlmostEqual(compare.overlap(body, usb), 0)
        self.assert_box_almost_equal(compare.transformed(compare.USB_ACCESS, 66, 5, 0),
                                     (71.43, 66.34, 83.43, 81.34))

    def test_radio_end_edge_distance_all_rotations(self):
        body = (10, 20, 70, 90)
        for angle, expected in ((0, 20), (90, 10), (180, 210), (270, 30)):
            self.assertEqual(compare.radio_end_edge_distance(body, angle), expected)

    def test_box_gap(self):
        self.assertEqual(compare.box_gap((0, 0, 1, 1), (2, 1, 3, 2)), 1)
        self.assertEqual(compare.box_gap((0, 0, 1, 1), (0.5, 0.5, 2, 2)), 0)


if __name__ == "__main__":
    unittest.main()
