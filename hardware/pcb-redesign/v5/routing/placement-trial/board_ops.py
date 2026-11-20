#!/usr/bin/env python3
"""KiCad 10 pcbnew operations; invoked inside the KiCad container."""
import argparse
import json
import math
import sys
import xml.etree.ElementTree as ET

import pcbnew as pcb

UART_NODES = {
    "Net-(U1-CONTROLLER1-IO21)": {("U1-CONTROLLER1", "J3.18"), ("U6-AUDIO1", "J1.19")},
    "Net-(U1-CONTROLLER1-IO47)": {("U1-CONTROLLER1", "J3.17"), ("U6-AUDIO1", "J1.20")},
}
CONTROLLER_REFS = {
    "J2", "J3", "J4", "J5", "J6", "J7", "J8", "J12", "JP1",
    "U1-CONTROLLER1", "U3", "U4", "U5", "U8", "U10",
    "C1", "C2", "C6", "C8", "C9", "C10", "C11",
    "R2", "R3", "R4", "R8", "R9", "R12", "R13",
}
AUDIO_REFS = {
    "J9", "J10", "J11", "JP2", "U2", "U6", "U7", "U9", "U11", "U6-AUDIO1",
    "C3", "C4", "C5", "C7", "C12", "C13", "C14",
    "R1", "R5", "R6", "R7", "R10", "R11", "R14", "R15",
}
MECHANICAL_REFS = {"H1", "H2", "H3", "H4", "H5", "H6"}


def fail(message):
    raise ValueError(message)


def label_experiment(board):
    title = board.GetTitleBlock()
    title.SetTitle("DAR-1000ES v5 - experimental, not for fabrication")
    title.SetRevision("v5 experimental")
    for index in range(9):
        title.SetComment(index, "")
    title.SetComment(0, "100 x 300 mm outline; mechanical fit unverified")
    title.SetComment(1, "Experimental routing; electrical and RF review required")


def load(path):
    board = pcb.LoadBoard(path)
    if board is None:
        fail(f"cannot load {path}")
    return board


def verify_netlist(board, filename):
    root = ET.parse(filename).getroot()
    components = [c.get("ref") for c in root.findall("./components/comp")]
    if not components or len(components) != len(set(components)):
        fail("netlist has no components or duplicate references")
    footprints = {}
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        if ref in footprints:
            fail(f"duplicate footprint reference: {ref}")
        footprints[ref] = fp
    missing = set(components) - footprints.keys()
    extra = {r for r in footprints.keys() - set(components)
             if any(p.GetNetname() for p in footprints[r].Pads())}
    if missing or extra:
        fail(f"netlist/board references differ: missing={sorted(missing)}, extra connected={sorted(extra)}")
    expected = {}
    for net in root.findall("./nets/net"):
        name = net.get("name")
        for node in net.findall("node"):
            key = (node.get("ref"), node.get("pin"))
            if key in expected:
                fail(f"duplicate netlist node {key}")
            expected[key] = name
    actual = {}
    for ref, fp in footprints.items():
        for pad in fp.Pads():
            if pad.GetNetname():
                key = (ref, pad.GetNumber())
                if key in actual and actual[key] != pad.GetNetname():
                    fail(f"conflicting duplicate pads {key}")
                actual[key] = pad.GetNetname()
    if actual != expected:
        only_expected = sorted((k, v, actual.get(k)) for k, v in expected.items() if actual.get(k) != v)
        only_actual = sorted((k, v) for k, v in actual.items() if k not in expected)
        fail(f"netlist differs: expected/actual={only_expected[:20]}, extra={only_actual[:20]}")


def clean(board):
    if list(board.GetTracks()) or list(board.Zones()):
        fail("input must be unrouted and have no zones or rule areas")
    if board.GetCopperLayerCount() != 2:
        fail("input must have exactly two copper layers")


def verify_uart(filename):
    root = ET.parse(filename).getroot()
    nets = {n.get("name"): {(p.get("ref"), p.get("pin")) for p in n.findall("node")}
            for n in root.findall("./nets/net")}
    for name, nodes in UART_NODES.items():
        if nets.get(name) != nodes:
            fail(f"UART net {name} has unexpected endpoints: {nets.get(name)}")


def rect_zone(board, rect):
    x1, y1, x2, y2 = rect
    if not (0 <= x1 < x2 <= 100 and 0 <= y1 < y2 <= 300):
        fail(f"invalid antenna rectangle: {rect}")
    zone = pcb.ZONE(board)
    layers = pcb.LSET()
    layers.AddLayer(pcb.F_Cu)
    layers.AddLayer(pcb.B_Cu)
    zone.SetLayerSet(layers)
    zone.SetIsRuleArea(True)
    zone.SetDoNotAllowTracks(True)
    zone.SetDoNotAllowVias(True)
    zone.SetDoNotAllowPads(True)
    zone.SetDoNotAllowZoneFills(True)
    zone.SetDoNotAllowFootprints(True)
    outline = zone.Outline()
    outline.NewOutline()
    for x, y in ((x1, y1), (x2, y1), (x2, y2), (x1, y2)):
        outline.Append(int(pcb.FromMM(x)), int(pcb.FromMM(y)))
    board.Add(zone)


def audit_sections(board, boundary_mm, audio_side):
    if not math.isfinite(boundary_mm) or not 0 < boundary_mm < 300:
        fail("section boundary must lie inside the board")
    boundary = pcb.FromMM(boundary_mm)
    allowed = {"GND", "LOCAL_5V", "SONY_5V_SENSE"} | UART_NODES.keys()
    fps = {f.GetReference(): f for f in board.GetFootprints()}
    for refs, side in ((("U2", "J9", "U6-AUDIO1", "U9", "U11"), audio_side),
                       (("U1-CONTROLLER1", "U8", "U10"),
                        "lower" if audio_side == "upper" else "upper")):
        for ref in refs:
            if ref not in fps:
                fail(f"missing section anchor {ref}")
            y = fps[ref].GetPosition().y
            if (side == "upper" and y >= boundary) or (side == "lower" and y <= boundary):
                fail(f"{ref} is not in the {side} section")
    occupied = {}
    for fp in fps.values():
        for pad in fp.Pads():
            net = pad.GetNetname()
            if not net:
                continue
            box = pad.GetBoundingBox()
            lo, hi = box.GetY(), box.GetY() + box.GetHeight()
            if lo <= boundary:
                occupied.setdefault(net, set()).add("upper")
            if hi >= boundary:
                occupied.setdefault(net, set()).add("lower")
    crossed = [net for net, sides in occupied.items() if len(sides) > 1 and net not in allowed]
    for track in board.GetTracks():
        box = track.GetBoundingBox()
        if box.GetY() <= boundary <= box.GetY() + box.GetHeight() and track.GetNetname() not in allowed:
            crossed.append(track.GetNetname())
    if crossed:
        fail(f"unauthorized cross-boundary nets: {sorted(set(crossed))}")
    print(f"Section audit passed at y={boundary_mm} mm.")


def audit_component_envelopes(board, boundary_mm, audio_side):
    fps = {f.GetReference(): f for f in board.GetFootprints()}
    if set(fps) != CONTROLLER_REFS | AUDIO_REFS | MECHANICAL_REFS:
        fail("component classification does not match the v5 footprint set")
    boundary = pcb.FromMM(boundary_mm)
    for refs, side in ((AUDIO_REFS, audio_side),
                       (CONTROLLER_REFS, "lower" if audio_side == "upper" else "upper")):
        for ref in sorted(refs):
            box = fps[ref].GetBoundingBox(False, False)
            lo, hi = box.GetY(), box.GetY() + box.GetHeight()
            if (side == "upper" and hi >= boundary) or (side == "lower" and lo <= boundary):
                fail(f"{ref} footprint envelope crosses the section boundary")
    print("All classified component footprint envelopes remain in their sections.")


def place(args):
    board = load(args.board)
    clean(board)
    verify_netlist(board, args.netlist)
    verify_uart(args.netlist)
    plan = json.load(open(args.plan, encoding="utf-8"))
    fps = {f.GetReference(): f for f in board.GetFootprints()}
    if set(plan["placements"]) != set(fps):
        fail("plan must specify every board footprint exactly once")
    if len(plan["antenna_keepouts_mm"]) != 2:
        fail("exactly two independently designed antenna keepouts required")
    for ref, fp in fps.items():
        x, y, angle = plan["placements"][ref]
        if not all(math.isfinite(v) for v in (x, y, angle)) or not (0 <= x <= 100 and 0 <= y <= 300):
            fail(f"invalid placement for {ref}")
        fp.SetOrientationDegrees(angle)
        fp.SetPosition(pcb.VECTOR2I(pcb.FromMM(x), pcb.FromMM(y)))
    edges = [s for s in board.GetDrawings() if s.GetLayer() == pcb.Edge_Cuts]
    if len(edges) != 1 or edges[0].GetShape() != pcb.SHAPE_T_RECT:
        fail("expected one rectangular Edge.Cuts graphic")
    edges[0].SetStart(pcb.VECTOR2I(0, 0))
    edges[0].SetEnd(pcb.VECTOR2I(pcb.FromMM(100), pcb.FromMM(300)))
    for rect in plan["antenna_keepouts_mm"]:
        rect_zone(board, rect)
    label_experiment(board)
    pcb.SaveBoard(args.output, board)
    print("Placement generated; DRC and independent physical review are mandatory.")


def prepare(args):
    board = load(args.board)
    if list(board.GetTracks()) or board.GetCopperLayerCount() != 2:
        fail("expected unrouted two-layer board")
    verify_netlist(board, args.netlist)
    verify_uart(args.netlist)
    zones = list(board.Zones())
    if len(zones) != 2 or any(
        not z.GetIsRuleArea()
        or not z.GetLayerSet().Contains(pcb.F_Cu)
        or not z.GetLayerSet().Contains(pcb.B_Cu)
        or not all((z.GetDoNotAllowTracks(), z.GetDoNotAllowVias(),
                    z.GetDoNotAllowPads(), z.GetDoNotAllowZoneFills(),
                    z.GetDoNotAllowFootprints()))
        for z in zones
    ):
        fail("expected exactly two antenna rule areas")
    edges = [s for s in board.GetDrawings() if s.GetLayer() == pcb.Edge_Cuts]
    if len(edges) != 1 or edges[0].GetShape() != pcb.SHAPE_T_RECT:
        fail("expected a single rectangular outline")
    a, b = edges[0].GetStart(), edges[0].GetEnd()
    if sorted((a.x, b.x)) != [0, pcb.FromMM(100)] or sorted((a.y, b.y)) != [0, pcb.FromMM(300)]:
        fail("expected 100 x 300 mm outline at (0,0)")
    audit_sections(board, args.boundary, args.audio_side)
    audit_component_envelopes(board, args.boundary, args.audio_side)
    if not pcb.ExportSpecctraDSN(board, args.output):
        fail("DSN export failed")


def finish(args):
    board = load(args.board)
    if list(board.GetTracks()):
        fail("SES must be imported into a fresh untracked board")
    verify_netlist(board, args.netlist)
    verify_uart(args.netlist)
    def placement_snapshot(b):
        return sorted(
            (f.GetReference(), f.GetFPIDAsString(), f.GetPosition().x,
             f.GetPosition().y, f.GetOrientationDegrees(),
             tuple(sorted((p.GetNumber(), p.GetPosition().x, p.GetPosition().y, p.GetNetname())
                          for p in f.Pads())))
            for f in b.GetFootprints()
        )
    before = placement_snapshot(board)
    if not pcb.ImportSpecctraSES(board, args.ses):
        fail("SES import failed")
    if placement_snapshot(board) != before:
        fail("SES import changed footprint or pad placement")
    verify_netlist(board, args.netlist)
    segments = [t for t in board.GetTracks() if not isinstance(t, pcb.PCB_VIA)]
    vias = [t for t in board.GetTracks() if isinstance(t, pcb.PCB_VIA)]
    if not segments:
        fail("SES contains no tracks")
    undersize = [pcb.ToMM(t.GetWidth()) for t in segments if t.GetWidth() < pcb.FromMM(0.25)]
    if undersize:
        fail(f"{len(undersize)} tracks below 0.25 mm: min={min(undersize):.6f} mm")
    if args.mode == "single" and (vias or any(t.GetLayer() != pcb.B_Cu for t in segments)):
        fail("single-layer output has vias or non-B.Cu traces")
    audit_sections(board, args.boundary, args.audio_side)
    audit_component_envelopes(board, args.boundary, args.audio_side)
    pcb.SaveBoard(args.output, board)
    print(json.dumps({"tracks": len(segments), "vias": len(vias),
                      "minimum_track_width_mm": min(pcb.ToMM(t.GetWidth()) for t in segments)}))


def add_ground(args):
    board = load(args.board)
    verify_netlist(board, args.netlist)
    verify_uart(args.netlist)
    audit_sections(board, args.boundary, args.audio_side)
    audit_component_envelopes(board, args.boundary, args.audio_side)
    if len(list(board.Zones())) != 2 or any(not z.GetIsRuleArea() for z in board.Zones()):
        fail("expected only the two existing antenna keepouts")
    ground = board.FindNet("GND")
    if not ground:
        fail("GND net missing")
    for layer in (pcb.F_Cu, pcb.B_Cu):
        zone = pcb.ZONE(board)
        zone.SetLayer(layer)
        zone.SetNetCode(ground.GetNetCode())
        zone.SetLocalClearance(pcb.FromMM(0.25))
        outline = zone.Outline()
        outline.NewOutline()
        for x, y in ((0.5, 0.5), (99.5, 0.5), (99.5, 299.5), (0.5, 299.5)):
            outline.Append(pcb.FromMM(x), pcb.FromMM(y))
        board.Add(zone)
    pcb.SaveBoard(args.output, board)
    print("GND zones added but not yet filled; KiCad refill and DRC required.")


def tidy_silk(args):
    board = load(args.board)
    verify_netlist(board, args.netlist)
    verify_uart(args.netlist)
    audit_sections(board, args.boundary, args.audio_side)
    audit_component_envelopes(board, args.boundary, args.audio_side)
    fps = {f.GetReference(): f for f in board.GetFootprints()}
    for ref in ("C9", "C10", "C12"):
        fp = fps[ref]
        fields = {f.GetName(): f for f in fp.GetFields()}
        for name in ("MPN", "Manufacturer"):
            if name not in fields:
                fail(f"{ref} is missing {name}")
            fields[name].SetLayer(pcb.F_Fab)
    for ref in sorted(MECHANICAL_REFS):
        fp = fps[ref]
        if any(g.GetLayer() == pcb.F_CrtYd for g in fp.GraphicalItems()):
            fail(f"{ref} already has a front courtyard")
        center = fp.GetPosition()
        circle = pcb.PCB_SHAPE(fp)
        circle.SetShape(pcb.SHAPE_T_CIRCLE)
        circle.SetLayer(pcb.F_CrtYd)
        circle.SetWidth(pcb.FromMM(0.05))
        circle.SetStart(center)
        circle.SetEnd(pcb.VECTOR2I(center.x + pcb.FromMM(3.75), center.y))
        circle.SetFilled(False)
        fp.Add(circle)
    label_experiment(board)
    pcb.SaveBoard(args.output, board)
    print("Moved capacitor metadata to F.Fab and added provisional 7.5 mm mounting courtyards.")


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="action", required=True)
    p = sub.add_parser("place")
    for key in ("board", "netlist", "plan", "output"):
        p.add_argument("--" + key, required=True)
    p.set_defaults(func=place)
    p = sub.add_parser("export")
    for key in ("board", "netlist", "output"):
        p.add_argument("--" + key, required=True)
    p.add_argument("--boundary", type=float, required=True)
    p.add_argument("--audio-side", choices=("upper", "lower"), required=True)
    p.set_defaults(func=prepare)
    p = sub.add_parser("import")
    for key in ("board", "netlist", "ses", "mode", "output"):
        p.add_argument("--" + key, required=True)
    p.add_argument("--boundary", type=float, required=True)
    p.add_argument("--audio-side", choices=("upper", "lower"), required=True)
    p.set_defaults(func=finish)
    p = sub.add_parser("pour")
    for key in ("board", "netlist", "output"):
        p.add_argument("--" + key, required=True)
    p.add_argument("--boundary", type=float, required=True)
    p.add_argument("--audio-side", choices=("upper", "lower"), required=True)
    p.set_defaults(func=add_ground)
    p = sub.add_parser("silk")
    for key in ("board", "netlist", "output"):
        p.add_argument("--" + key, required=True)
    p.add_argument("--boundary", type=float, required=True)
    p.add_argument("--audio-side", choices=("upper", "lower"), required=True)
    p.set_defaults(func=tidy_silk)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, OSError, ET.ParseError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
