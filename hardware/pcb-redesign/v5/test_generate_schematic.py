#!/usr/bin/env python3
import unittest

import generate_schematic as gen


class MarkerGuardTests(unittest.TestCase):
    def test_free_point(self):
        root = ["kicad_sch"]
        gen.add_unused_marker(root, "test", (1.0, 2.0))
        self.assertEqual(len(gen.ch(root, "no_connect")), 1)

    def test_connected_points_rejected(self):
        objects = [
            ["wire", ["pts", ["xy", "0", "2"], ["xy", "2", "2"]]],
            ["wire", ["pts", ["xy", "1", "2"], ["xy", "2", "2"]]],
            ["label", '"net"', ["at", "1", "2", "0"]],
            ["global_label", '"net"', ["at", "1", "2", "0"]],
            ["hierarchical_label", '"net"', ["at", "1", "2", "0"]],
            ["junction", ["at", "1", "2"]],
            ["no_connect", ["at", "1", "2"]],
        ]
        for item in objects:
            with self.subTest(item=item), self.assertRaises(AssertionError):
                gen.add_unused_marker(["kicad_sch", item], "test", (1.0, 2.0))


if __name__ == "__main__":
    unittest.main()
