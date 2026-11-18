#!/usr/bin/env python3
"""Verify authorized rigid moves, geometry, nets, domains and bypass paths."""
import hashlib
import importlib.util
import json
import math
import sys
from pathlib import Path

import pcbnew as pcb

HERE = Path(__file__).resolve().parent
R = HERE.parent
sys.path[:0] = [str(R), str(R / "decoupling-trial")]
import board_ops as ops
import measure_paths as paths

spec = importlib.util.spec_from_file_location("detail", R / "placement-controller/audit.py")
detail = importlib.util.module_from_spec(spec)
spec.loader.exec_module(detail)

source = pcb.LoadBoard(str(R / "placement-current/result.kicad_pcb"))
board = pcb.LoadBoard(str(HERE / "result.kicad_pcb"))
normalized = pcb.LoadBoard(str(HERE / "result.kicad_pcb"))
old = {f.GetReference(): f for f in source.GetFootprints()}
new = {f.GetReference(): f for f in normalized.GetFootprints()}
if detail.placements(source) != detail.placements(normalized):
    raise ValueError("Unexpected change to footprint position or pad geometry")
def outline(b):
    return sorted((s.GetShape(), s.GetStart().x, s.GetStart().y, s.GetEnd().x, s.GetEnd().y,
                   s.GetWidth()) for s in b.GetDrawings() if s.GetLayer() == pcb.Edge_Cuts)
if outline(source) != outline(board):
    raise ValueError("Board outline changed")
for prefix in tuple(f"J{i}  " for i in range(2, 12)) + ("JP1  ", "JP2  "):
    baseline = [t.GetText() for t in source.GetDrawings()
                if isinstance(t, pcb.PCB_TEXT) and t.GetText().startswith(prefix)]
    visible = [t.GetText() for t in board.GetDrawings()
               if isinstance(t, pcb.PCB_TEXT) and t.GetLayer() == pcb.F_SilkS
               and t.GetText().startswith(prefix)]
    if len(baseline) != 1 or baseline != visible:
        raise ValueError(f"Missing front silkscreen legend {prefix}")
    text = next(t for t in board.GetDrawings()
                if isinstance(t, pcb.PCB_TEXT) and t.GetText() == visible[0])
    ref = prefix.strip()
    delta = text.GetPosition() - new[ref].GetPosition()
    if math.hypot(pcb.ToMM(delta.x), pcb.ToMM(delta.y)) > 30:
        raise ValueError(f"Connector legend too far from {ref}")
    if ref == "J8" and pcb.ToMM(text.GetBoundingBox().GetBottom()) >= 149.5:
        raise ValueError("J8 legend crosses the section divider")
ops.verify_netlist(board, str(R.parent / "DAR-1000ES-v5.net.xml"))
ops.verify_uart(str(R.parent / "DAR-1000ES-v5.net.xml"))
ops.audit_sections(board, 150, "lower")
ops.audit_component_envelopes(board, 150, "lower")
zones = detail.check_zones(board)
if any(z.GetIsRuleArea() for z in board.Zones()):
    raise ValueError("Obsolete interior antenna areas remain")
fps = {f.GetReference(): f for f in board.GetFootprints()}
for ref in ("R4", "R11"):
    pad = next(p for p in fps[ref].Pads() if p.GetNumber() == "2")
    original = next(p for p in old[ref].Pads() if p.GetNumber() == "2")
    if pad.GetLocalZoneConnection() != original.GetLocalZoneConnection():
        raise ValueError(f"{ref}.2 ground zone override changed")
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
        pairs.append({"capacitor": cap, "capacitor_pad": pad.GetNumber(), "ic": ic,
                      "ic_pin": pin, "net": net,
                      "pad_centers_mm": round(pcb.ToMM(round(math.hypot(a.x - b.x, a.y - b.y))), 3),
                      "track_only_shortest_mm": round(pcb.ToMM(round(result[0])), 3) if result else None})
report = {
    "sha256": hashlib.sha256((HERE / "result.kicad_pcb").read_bytes()).hexdigest(),
    "authorized_positions_and_pad_geometry_verified": True,
    "r4_r11_zone_connections_unchanged": True,
    "zones": [{"layer": board.GetLayerName(z.GetLayer()), "net": z.GetNetname(),
               "filled_polygons": z.GetFilledPolysList(z.GetLayer()).OutlineCount()} for z in zones],
    "pairs": pairs,
}
(HERE / "audit.json").write_text(json.dumps(report, indent=2) + "\n")
print("Authorized placement, geometry, nets, sections and filled planes passed.")
