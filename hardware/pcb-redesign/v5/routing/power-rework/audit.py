#!/usr/bin/env python3
"""Fail-closed section/plane checks and bypass geometry measurements."""
import hashlib
import json
import math
import sys
from pathlib import Path

import pcbnew as pcb

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "decoupling-trial"))
import board_ops as ops
import measure_paths as paths

SOURCE = HERE.parent / "decoupling-trial" / "result.kicad_pcb"
NETLIST = HERE.parents[1] / "DAR-1000ES-v5.net.xml"
BOARD = HERE / "result.kicad_pcb"


def placements(board):
    return sorted((f.GetReference(), f.GetFPIDAsString(), f.GetPosition().x,
                   f.GetPosition().y, f.GetOrientationDegrees(),
                   tuple(sorted((p.GetNumber(), p.GetPosition().x, p.GetPosition().y,
                                 p.GetNetname()) for p in f.Pads())))
                  for f in board.GetFootprints())


def rule_areas(board):
    return sorted((z.GetBoundingBox().GetX(), z.GetBoundingBox().GetY(),
                   z.GetBoundingBox().GetWidth(), z.GetBoundingBox().GetHeight(),
                   z.GetLayerSet().Contains(pcb.F_Cu), z.GetLayerSet().Contains(pcb.B_Cu),
                   z.GetDoNotAllowTracks(), z.GetDoNotAllowVias(), z.GetDoNotAllowPads(),
                   z.GetDoNotAllowZoneFills(), z.GetDoNotAllowFootprints())
                  for z in board.Zones() if z.GetIsRuleArea())


def check_zones(board):
    zones = [z for z in board.Zones() if not z.GetIsRuleArea()]
    if len(zones) != 2 or {z.GetLayer() for z in zones} != {pcb.F_Cu, pcb.B_Cu}:
        raise ValueError("expected exactly one fill per copper layer")
    for z in zones:
        if z.GetNetname() != "GND":
            raise ValueError("only GND copper zones are permitted")
        if (z.GetIslandRemovalMode() != pcb.ISLAND_REMOVAL_MODE_ALWAYS or
                z.GetPadConnection() != pcb.ZONE_CONNECTION_THERMAL or not z.IsFilled()):
            raise ValueError("zone requires a filled thermal connection with island removal")
        poly = z.GetFilledPolysList(z.GetLayer())
        if not poly.OutlineCount() or any(z.IsIsland(z.GetLayer(), i) for i in range(poly.OutlineCount())):
            raise ValueError("empty or flagged isolated fill")
    return zones


def main():
    source, board = pcb.LoadBoard(str(SOURCE)), pcb.LoadBoard(str(BOARD))
    if placements(source) != placements(board):
        raise ValueError("unexpected footprint or pad relocation")
    if rule_areas(source) != rule_areas(board) or len(rule_areas(board)) != 2:
        raise ValueError("provisional antenna rules changed")
    ops.verify_netlist(board, str(NETLIST))
    ops.verify_uart(str(NETLIST))
    ops.audit_sections(board, 150, "lower")
    ops.audit_component_envelopes(board, 150, "lower")
    zones = check_zones(board)
    fps = {f.GetReference(): f for f in board.GetFootprints()}
    nets = {p.GetNetname() for cap in paths.PAIRS for p in fps[cap].Pads()}
    graphs = {net: paths.build(board, net)[0] for net in nets}
    pairs = []
    for cap, ic in paths.PAIRS.items():
        for pad in fps[cap].Pads():
            net = pad.GetNetname()
            pin = paths.SUPPLY_PINS[ic][1 if net == "GND" else 0]
            target = next(p for p in fps[ic].Pads() if p.GetNumber() == pin and p.GetNetname() == net)
            a, b = pad.GetPosition(), target.GetPosition()
            result = paths.shortest(graphs[net], ("pad", cap, pad.GetNumber()), {("pad", ic, pin)})
            samples = {}
            if net == "GND" and cap in ("C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8", "C14"):
                for name, item in ((cap, pad), (ic, target)):
                    center = item.GetPosition()
                    points = []
                    for i in range(360):
                        dx, dy = math.cos(i * math.pi / 180), math.sin(i * math.pi / 180)
                        lo, hi = 0, pcb.FromMM(10)
                        while hi - lo > pcb.FromMM(0.001):
                            mid = (lo + hi) // 2
                            q = pcb.VECTOR2I(round(center.x + mid * dx), round(center.y + mid * dy))
                            if item.HitTest(q):
                                lo = mid
                            else:
                                hi = mid
                        radius = hi + pcb.FromMM(0.125)
                        points.append(pcb.VECTOR2I(round(center.x + radius * dx),
                                                   round(center.y + radius * dy)))
                    for z in zones:
                        layer = z.GetLayer()
                        hits = sum(z.HitTestFilledArea(layer, point) for point in points)
                        if not hits:
                            raise ValueError(f"no sampled fill in thermal gap at {name} on {board.GetLayerName(layer)}")
                        samples[f"{name}.{item.GetNumber()} {board.GetLayerName(layer)}"] = hits
            pairs.append({"capacitor": cap, "capacitor_pad": pad.GetNumber(), "ic": ic,
                          "ic_pin": pin, "net": net,
                          "pad_centers_mm": round(pcb.ToMM(round(math.hypot(a.x - b.x, a.y - b.y))), 3),
                          "track_only_shortest_mm": round(pcb.ToMM(round(result[0])), 3) if result else None,
                          "thermal_gap_sample_hits": samples})
    result = {"sha256": hashlib.sha256(BOARD.read_bytes()).hexdigest(),
              "unchanged_footprint_positions_and_pad_nets": True,
              "zones": [{"layer": board.GetLayerName(z.GetLayer()),
                         "net": z.GetNetname(),
                         "filled_polygons": z.GetFilledPolysList(z.GetLayer()).OutlineCount(),
                         "flagged_islands": sum(z.IsIsland(z.GetLayer(), i) for i in
                                                range(z.GetFilledPolysList(z.GetLayer()).OutlineCount()))}
                        for z in zones],
              "pairs": pairs}
    (HERE / "audit.json").write_text(json.dumps(result, indent=2) + "\n")
    print("Netlist, UART, section, placement and common-GND fill checks passed.")


if __name__ == "__main__":
    main()
