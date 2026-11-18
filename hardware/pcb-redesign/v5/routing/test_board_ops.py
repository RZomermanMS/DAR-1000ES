import unittest
from types import SimpleNamespace

import pcbnew as pcb
import board_ops as ops


def box(y, height=0):
    return SimpleNamespace(GetY=lambda: pcb.FromMM(y), GetHeight=lambda: pcb.FromMM(height))


def pad(net, y, height=0):
    return SimpleNamespace(GetNetname=lambda: net, GetBoundingBox=lambda: box(y, height))


def footprint(ref, y, pads=()):
    return SimpleNamespace(GetReference=lambda: ref,
                           GetPosition=lambda: SimpleNamespace(y=pcb.FromMM(y)),
                           GetBoundingBox=lambda *args: box(y - 1, 2),
                           Pads=lambda: pads)


def design(extra=(), tracks=()):
    audio = ("U2", "J9", "U6-AUDIO1", "U9", "U11")
    ctrl = ("U1-CONTROLLER1", "U8", "U10")
    fps = [footprint(r, 200) for r in audio] + [footprint(r, 40) for r in ctrl] + list(extra)
    return SimpleNamespace(GetFootprints=lambda: fps, GetTracks=lambda: tracks)


class SectionTests(unittest.TestCase):
    def test_allowed_rails(self):
        board = design([footprint("A", 40, [pad("GND", 40), pad("LOCAL_5V", 40)]),
                        footprint("B", 200, [pad("GND", 200), pad("LOCAL_5V", 200)])])
        ops.audit_sections(board, 150, "lower")

    def test_wrong_ownership(self):
        board = design([footprint("A", 40, [pad("/DATA", 40)]),
                        footprint("B", 200, [pad("/DATA", 200)])])
        with self.assertRaisesRegex(ValueError, "cross-boundary"):
            ops.audit_sections(board, 150, "lower")

    def test_allowed_uart(self):
        board = design([footprint("A", 40, [pad("Net-(U1-CONTROLLER1-IO21)", 40)]),
                        footprint("B", 200, [pad("Net-(U1-CONTROLLER1-IO21)", 200)])])
        ops.audit_sections(board, 150, "lower")

    def test_straddling_track(self):
        track = SimpleNamespace(GetBoundingBox=lambda: box(140, 20),
                                GetNetname=lambda: "/DATA")
        with self.assertRaisesRegex(ValueError, "cross-boundary"):
            ops.audit_sections(design(tracks=[track]), 150, "lower")

    def test_touching_pad(self):
        board = design([footprint("A", 149, [pad("/DATA", 149, 2)])])
        with self.assertRaisesRegex(ValueError, "cross-boundary"):
            ops.audit_sections(board, 150, "lower")

    def test_anchor_wrong_side(self):
        with self.assertRaisesRegex(ValueError, "not in"):
            ops.audit_sections(design(), 150, "upper")

    def test_all_component_envelopes(self):
        fps = ([footprint(r, 40) for r in ops.CONTROLLER_REFS]
               + [footprint(r, 200) for r in ops.AUDIO_REFS]
               + [footprint(r, 150) for r in ops.MECHANICAL_REFS])
        board = SimpleNamespace(GetFootprints=lambda: fps)
        ops.audit_component_envelopes(board, 150, "lower")
        fps.append(footprint("unexpected", 40))
        with self.assertRaisesRegex(ValueError, "classification"):
            ops.audit_component_envelopes(board, 150, "lower")

    def test_component_body_crosses_boundary(self):
        fps = ([footprint(r, 40) for r in ops.CONTROLLER_REFS]
               + [footprint(r, 200 if r != "U2" else 150.5) for r in ops.AUDIO_REFS]
               + [footprint(r, 150) for r in ops.MECHANICAL_REFS])
        with self.assertRaisesRegex(ValueError, "footprint envelope"):
            ops.audit_component_envelopes(SimpleNamespace(GetFootprints=lambda: fps), 150, "lower")

    def test_keepout_layers_and_flags(self):
        board = pcb.BOARD()
        ops.rect_zone(board, [10, 20, 30, 40])
        zone = list(board.Zones())[0]
        self.assertTrue(zone.GetIsRuleArea())
        self.assertTrue(zone.GetLayerSet().Contains(pcb.F_Cu))
        self.assertTrue(zone.GetLayerSet().Contains(pcb.B_Cu))
        self.assertTrue(all((zone.GetDoNotAllowTracks(), zone.GetDoNotAllowVias(),
                             zone.GetDoNotAllowPads(), zone.GetDoNotAllowZoneFills(),
                             zone.GetDoNotAllowFootprints())))

    def test_invalid_keepout(self):
        with self.assertRaises(ValueError):
            ops.rect_zone(pcb.BOARD(), [10, 10, 101, 20])


if __name__ == "__main__":
    unittest.main()
