#!/usr/bin/env python3
"""Verify the saved supervisor relocation, domains, fill and local geometry."""
import hashlib
import importlib.util
import json
import math
import sys
from pathlib import Path

import pcbnew as pcb

HERE = Path(__file__).resolve().parent
ROUTING = HERE.parent
SOURCE = ROUTING / "integrated-review/clearance-first-corrected/result.kicad_pcb"
BOARD = HERE / "result.kicad_pcb"
sys.path.insert(0, str(ROUTING))
sys.path.insert(0, str(ROUTING / "decoupling-trial"))
import board_ops as ops
import measure_paths as paths

spec = importlib.util.spec_from_file_location("power_audit", ROUTING / "power-rework/audit.py")
power = importlib.util.module_from_spec(spec)
spec.loader.exec_module(power)


def main():
    source, board = pcb.LoadBoard(str(SOURCE)), pcb.LoadBoard(str(BOARD))
    before = {p[0]: p for p in power.placements(source)}
    after = {p[0]: p for p in power.placements(board)}
    if before.keys() != after.keys() or any(before[k] != after[k] for k in before if k != "C8"):
        raise ValueError("unexpected other footprint or pad change")
    if power.rule_areas(source) != power.rule_areas(board):
        raise ValueError("provisional antenna rule areas changed")
    ops.verify_netlist(board, str(ROUTING.parent / "DAR-1000ES-v5.net.xml"))
    ops.verify_uart(str(ROUTING.parent / "DAR-1000ES-v5.net.xml"))
    ops.audit_sections(board, 150, "lower")
    ops.audit_component_envelopes(board, 150, "lower")
    zones = power.check_zones(board)
    fps = {f.GetReference(): f for f in board.GetFootprints()}
    cap, chip = fps["C8"], fps["U10"]
    if cap.GetPosition() != pcb.VECTOR2I(pcb.FromMM(45), pcb.FromMM(96)) or cap.GetOrientationDegrees() % 360 != 270:
        raise ValueError("C8 placement was not saved")
    samples, measurements = {}, {}
    for cp, ip, net in (("1", "2", "SONY_5V_SENSE"), ("2", "3", "GND")):
        a = next(p for p in cap.Pads() if p.GetNumber() == cp and p.GetNetname() == net)
        b = next(p for p in chip.Pads() if p.GetNumber() == ip and p.GetNetname() == net)
        graph, _ = paths.build(board, net)
        route = paths.shortest(graph, ("pad", "C8", cp), {("pad", "U10", ip)})
        if net != "GND" and route is None:
            raise ValueError("no track-only supply path from C8 to U10")
        distance = math.hypot(a.GetPosition().x - b.GetPosition().x, a.GetPosition().y - b.GetPosition().y)
        measurements[net] = {"c8_pad": cp, "u10_pin": ip,
                             "pad_centers_mm": round(pcb.ToMM(round(distance)), 3),
                             "track_only_mm": round(pcb.ToMM(round(route[0])), 3) if route else None}
        if net == "GND":
            for ref, pad in (("C8", a), ("U10", b)):
                for z in zones:
                    hits = 0
                    center = pad.GetPosition()
                    for i in range(360):
                        dx, dy = math.cos(i * math.pi / 180), math.sin(i * math.pi / 180)
                        lo, hi = 0, pcb.FromMM(10)
                        while hi - lo > pcb.FromMM(0.001):
                            mid = (lo + hi) // 2
                            q = pcb.VECTOR2I(round(center.x + mid * dx), round(center.y + mid * dy))
                            if pad.HitTest(q):
                                lo = mid
                            else:
                                hi = mid
                        radius = hi + pcb.FromMM(0.125)
                        q = pcb.VECTOR2I(round(center.x + radius * dx), round(center.y + radius * dy))
                        hits += z.HitTestFilledArea(z.GetLayer(), q)
                    if not hits:
                        raise ValueError(f"no sampled thermal fill at {ref}")
                    samples[f"{ref}.{pad.GetNumber()} {board.GetLayerName(z.GetLayer())}"] = hits
    result = {"board_sha256": hashlib.sha256(BOARD.read_bytes()).hexdigest(),
              "unchanged_other_placements_and_pad_nets": True,
              "netlist_uart_section_and_envelopes_passed": True,
              "antenna_rule_areas_unchanged": True, "c8_u10": measurements,
              "thermal_gap_sample_hits": samples,
              "zones": [{"layer": board.GetLayerName(z.GetLayer()),
                         "net": z.GetNetname(),
                         "filled_polygons": z.GetFilledPolysList(z.GetLayer()).OutlineCount()}
                        for z in zones]}
    (HERE / "audit.json").write_text(json.dumps(result, indent=2) + "\n")
    print("Netlist, UART, domains, plane, and saved placement checks passed.")


if __name__ == "__main__":
    main()
