#!/usr/bin/env python3
import unittest

import pcbnew as pcb
import audit


class PlaneAuditTest(unittest.TestCase):
    def setUp(self):
        self.board = pcb.LoadBoard(str(audit.BOARD))
        self.zone = next(z for z in self.board.Zones() if not z.GetIsRuleArea())

    def test_candidate(self):
        self.assertEqual(len(audit.check_zones(self.board)), 2)

    def test_allowed_track_net_is_not_allowed_as_a_zone(self):
        self.zone.SetNetCode(self.board.FindNet("LOCAL_5V").GetNetCode())
        with self.assertRaisesRegex(ValueError, "only GND"):
            audit.check_zones(self.board)

    def test_unfilled_and_island_retention_rejected(self):
        self.zone.SetIsFilled(False)
        with self.assertRaises(ValueError):
            audit.check_zones(self.board)
        self.zone.SetIsFilled(True)
        self.zone.SetIslandRemovalMode(pcb.ISLAND_REMOVAL_MODE_NEVER)
        with self.assertRaises(ValueError):
            audit.check_zones(self.board)

    def test_extra_zone_rejected(self):
        zone = pcb.ZONE(self.board)
        zone.SetNetCode(self.board.FindNet("GND").GetNetCode())
        zone.SetLayer(pcb.F_Cu)
        self.board.Add(zone)
        with self.assertRaises(ValueError):
            audit.check_zones(self.board)


if __name__ == "__main__":
    unittest.main()
