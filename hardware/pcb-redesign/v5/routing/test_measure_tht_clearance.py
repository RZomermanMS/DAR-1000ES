import hashlib
import json
import unittest
from pathlib import Path

import pcbnew as pcb
import measure_tht_clearance as clearance


def point(x, y):
    return pcb.VECTOR2I(pcb.FromMM(x), pcb.FromMM(y))


def fixture(shape=pcb.PAD_SHAPE_CIRCLE, size=(2, 2), angle=0):
    board = pcb.BOARD()
    board.SetCopperLayerCount(2)
    fp = pcb.FOOTPRINT(board)
    fp.SetReference("U1")
    board.Add(fp)
    pad = pcb.PAD(fp)
    pad.SetNumber("1")
    pad.SetAttribute(pcb.PAD_ATTRIB_PTH)
    pad.SetLayerSet(pcb.LSET.AllCuMask())
    pad.SetShape(shape)
    pad.SetSize(point(*size))
    pad.SetOrientationDegrees(angle)
    pad.SetPosition(point(0, 0))
    fp.Add(pad)
    return board, pad


def track(board, x, layer=pcb.B_Cu):
    item = pcb.PCB_TRACK(board)
    item.SetStart(point(x, -1))
    item.SetEnd(point(x, 1))
    item.SetWidth(pcb.FromMM(0.4))
    item.SetLayer(layer)
    board.Add(item)
    return item


class ClearanceTests(unittest.TestCase):
    def test_circle_track_and_endpoint(self):
        board, _ = fixture()
        item = track(board, 1.7)
        result = clearance.measure(board, 0.4)
        self.assertAlmostEqual(result["minimum"]["clearance_mm"], 0.5, places=5)
        self.assertEqual(result["within_threshold"], [])
        item.SetStart(point(2, 0))
        item.SetEnd(point(3, 0))
        self.assertAlmostEqual(clearance.measure(board, 1)["minimum"]["clearance_mm"],
                               0.8, places=5)

    def test_rotated_oval_and_rectangle(self):
        for shape, expected in ((pcb.PAD_SHAPE_OVAL, 0.5),
                                (pcb.PAD_SHAPE_RECT, 0.0)):
            with self.subTest(shape=shape):
                board, _ = fixture(shape, (4, 2) if shape == pcb.PAD_SHAPE_OVAL else (2, 4), 90)
                track(board, 1.7)
                result = clearance.measure(board, 1)
                self.assertAlmostEqual(result["minimum"]["clearance_mm"], expected, places=5)

    def test_roundrect_and_arc(self):
        board, pad = fixture(pcb.PAD_SHAPE_ROUNDRECT)
        pad.SetRoundRectRadiusRatio(0.25)
        track(board, 1.7)
        self.assertAlmostEqual(clearance.measure(board, 1)["minimum"]["clearance_mm"],
                               0.5, places=5)
        board, _ = fixture()
        arc = pcb.PCB_ARC(board)
        arc.SetStart(point(2, 0))
        arc.SetMid(point(0, 2))
        arc.SetEnd(point(-2, 0))
        arc.SetWidth(pcb.FromMM(0.4))
        arc.SetLayer(pcb.F_Cu)
        board.Add(arc)
        result = clearance.measure(board, 1)
        self.assertEqual(result["minimum"]["item"]["type"], "arc")
        self.assertAlmostEqual(result["minimum"]["clearance_mm"], 0.8, places=5)

    def test_via_both_layers_and_unconnected_net_zero(self):
        board, _ = fixture()
        via = pcb.PCB_VIA(board)
        via.SetPosition(point(1.7, 0))
        via.SetWidth(pcb.FromMM(0.4))
        via.SetLayerPair(pcb.F_Cu, pcb.B_Cu)
        board.Add(via)
        result = clearance.measure(board, 1)
        self.assertEqual(result["unrelated_layer_pairs_examined"], 2)
        self.assertEqual({r["layer"] for r in result["within_threshold"]}, {"F.Cu", "B.Cu"})
        self.assertTrue(all(r["item"]["type"] == "via" for r in result["within_threshold"]))
        self.assertAlmostEqual(result["minimum"]["clearance_mm"], 0.5, places=5)

    def test_same_net_excluded_and_smd_excluded(self):
        board, pad = fixture()
        net = pcb.NETINFO_ITEM(board, "shared")
        board.Add(net)
        pad.SetNetCode(net.GetNetCode())
        same = track(board, 1.2)
        same.SetNetCode(net.GetNetCode())
        track(board, 2.2, pcb.F_Cu)
        result = clearance.measure(board, 1)
        self.assertEqual(result["unrelated_layer_pairs_examined"], 1)
        self.assertAlmostEqual(result["minimum"]["clearance_mm"], 1.0, places=5)
        pad.SetAttribute(pcb.PAD_ATTRIB_SMD)
        self.assertIsNone(clearance.measure(board, 1)["minimum"])

    def test_invalid_inputs(self):
        board, _ = fixture()
        for threshold in (-1, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                clearance.measure(board, threshold)
        board.SetCopperLayerCount(4)
        with self.assertRaisesRegex(ValueError, "two copper"):
            clearance.measure(board, 1)

    def test_retained_board_and_report(self):
        directory = Path(__file__).resolve().parent / "experiment-silk-7"
        path = directory / "result.kicad_pcb"
        result = clearance.measure(pcb.LoadBoard(str(path)), 0.5)
        result["board_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        self.assertEqual(result, json.loads((directory / "tht-clearance.json").read_text()))
        self.assertEqual(result["tht_pad_count"], 319)
        self.assertEqual(result["unrelated_layer_pairs_examined"], 233002)
        self.assertEqual(result["minimum"]["clearance_mm"], 0.201657)
        self.assertEqual(len(result["within_threshold"]), 505)


if __name__ == "__main__":
    unittest.main()
