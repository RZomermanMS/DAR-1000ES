#!/usr/bin/env python3
"""Fresh two-layer routing from the external-whip review placement."""
import importlib.util
import json
import math
import os
import re
import sys
from pathlib import Path

import pcbnew as pcb

ROOT = Path(os.environ.get("ROUTING_ROOT", Path(__file__).resolve().parent.parent))
V5 = ROOT.parent
SOURCE = ROOT / "placement-current/result.kicad_pcb"
OUT = Path(__file__).resolve().parent
NETLIST = V5 / "DAR-1000ES-v5.net.xml"
spec = importlib.util.spec_from_file_location("board_ops", ROOT / "board_ops.py")
ops = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ops)


def bbox(fp):
    b = fp.GetBoundingBox(False, False)
    return tuple(pcb.ToMM(v) for v in (b.GetX(), b.GetY(), b.GetRight(), b.GetBottom()))


def overlap(a, b, margin=0.5):
    return not (a[2] + margin <= b[0] or b[2] + margin <= a[0]
                or a[3] + margin <= b[1] or b[3] + margin <= a[1])


def move(fp, x, y, angle):
    fp.SetOrientationDegrees(angle)
    fp.SetPosition(pcb.VECTOR2I(pcb.FromMM(x), pcb.FromMM(y)))


def pads(fp):
    return {p.GetNumber(): p for p in fp.Pads()}


def distance(a, b):
    return math.hypot(pcb.ToMM(a.x - b.x), pcb.ToMM(a.y - b.y))


def prepare():
    text = SOURCE.read_text()
    pattern = re.compile(r"(?m)^\t\((?:segment|via|zone)\s")
    while match := pattern.search(text):
        i, depth, quoted, escaped = match.start() + 1, 0, False, False
        start = i
        while i < len(text):
            c = text[i]
            if quoted:
                if escaped:
                    escaped = False
                elif c == "\\":
                    escaped = True
                elif c == '"':
                    quoted = False
            elif c == '"':
                quoted = True
            elif c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        if depth != 0:
            raise ValueError("Unbalanced board expression")
        text = text[:start - 1] + text[i + 1:]
    stripped = OUT / ".work/stripped.kicad_pcb"
    stripped.write_text(text)
    project = json.loads((ROOT / "placement-current/result.kicad_pro").read_text())
    for netclass in project["net_settings"]["classes"]:
        netclass["clearance"] = max(netclass["clearance"], 0.30)
    stripped.with_suffix(".kicad_pro").write_text(json.dumps(project, indent=2) + "\n")
    board = pcb.LoadBoard(str(stripped))
    if list(board.GetTracks()) or list(board.Zones()):
        raise ValueError("Could not remove all old tracks and zones")
    ops.verify_netlist(board, str(NETLIST))
    ops.verify_uart(str(NETLIST))
    ops.audit_sections(board, 150, "lower")
    ops.audit_component_envelopes(board, 150, "lower")
    pcb.SaveBoard(str(OUT / "input.kicad_pcb"), board)
    if not pcb.ExportSpecctraDSN(board, str(OUT / "route.dsn")):
        raise ValueError("DSN export failed")
    print("Retained all placement-current footprint positions and pad geometry.")


def finish():
    board = pcb.LoadBoard(str(OUT / "input.kicad_pcb"))
    if not pcb.ImportSpecctraSES(board, str(OUT / "route.ses")):
        raise ValueError("SES import failed")
    ops.verify_netlist(board, str(NETLIST))
    ops.audit_sections(board, 150, "lower")
    ops.audit_component_envelopes(board, 150, "lower")
    tracks = list(board.GetTracks())
    segments = [t for t in tracks if not isinstance(t, pcb.PCB_VIA)]
    if not segments or min(t.GetWidth() for t in segments) < pcb.FromMM(.30):
        raise ValueError("Missing or undersized tracks")
    held_tracks = improve_c8(board)
    source = pcb.LoadBoard(str(SOURCE))
    for zone in source.Zones():
        if not zone.GetIsRuleArea():
            board.Add(pcb.ZONE(zone))
    pcb.SaveBoard(str(OUT / "result.kicad_pcb"), board)
    assert held_tracks
    print(f"Imported {len(segments)} segments, {len(tracks) - len(segments)} vias")


def improve_c8(board):
    def point(xy):
        return pcb.VECTOR2I(pcb.FromMM(xy[0]), pcb.FromMM(xy[1]))

    def coordinates(vector):
        return (vector.x, vector.y)

    old_points = [(45, 96), (47.2464, 96), (51.5613, 100.3149),
                  (51.5613, 102.5989), (50.9585, 103.2017),
                  (49.27, 103.2017), (49.27, 102)]
    new_points = [(45, 96), (49.27, 100.27), (49.27, 102)]
    fps = {f.GetReference(): f for f in board.GetFootprints()}
    for ref, number, expected in (("C8", "1", new_points[0]),
                                  ("U10", "2", new_points[-1])):
        matches = [p for p in fps[ref].Pads() if p.GetNumber() == number]
        if (len(matches) != 1 or matches[0].GetPosition() != point(expected)
                or matches[0].GetNetname() != "SONY_5V_SENSE"):
            raise ValueError(f"{ref}.{number} placement or net changed")
    tracks = list(board.GetTracks())
    removed = []
    for a, b in zip(old_points, old_points[1:]):
        endpoints = {coordinates(point(a)), coordinates(point(b))}
        found = [t for t in tracks if type(t) == pcb.PCB_TRACK
                 and t.GetNetname() == "SONY_5V_SENSE" and t.GetLayer() == pcb.B_Cu
                 and t.GetWidth() == pcb.FromMM(.30)
                 and {coordinates(t.GetStart()), coordinates(t.GetEnd())} == endpoints]
        if len(found) != 1:
            raise ValueError("C8 original detour differs from expected topology")
        removed.append(found[0])
    for track in removed:
        board.Remove(track)
    net = board.FindNet("SONY_5V_SENSE")
    for a, b in zip(new_points, new_points[1:]):
        track = pcb.PCB_TRACK(board)
        track.SetStart(point(a))
        track.SetEnd(point(b))
        track.SetLayer(pcb.F_Cu)
        track.SetWidth(pcb.FromMM(.30))
        track.SetNet(net)
        board.Add(track)
    print("Replaced C8/U10 B.Cu detour with guarded 0.30 mm F.Cu path.")
    return tracks


def tidy():
    board = pcb.LoadBoard(str(OUT / "result.kicad_pcb"))
    legends = tuple(f"J{i}  " for i in range(2, 12)) + ("JP1  ", "JP2  ")
    to_move = []
    for text in board.GetDrawings():
        if isinstance(text, pcb.PCB_TEXT):
            if text.GetText().startswith(legends):
                to_move.append(text)
    fps = {f.GetReference(): f for f in board.GetFootprints()}
    def item_box(item):
        b = item.GetBoundingBox()
        return tuple(pcb.ToMM(v) for v in (b.GetX(), b.GetY(), b.GetRight(), b.GetBottom()))
    obstacles = [item_box(f) for f in board.GetFootprints()]
    obstacles += [item_box(t) for t in board.GetDrawings()
                  if t.GetLayer() == pcb.F_SilkS and t not in to_move]
    if len(to_move) != 12:
        raise ValueError("Expected twelve connector legends")
    for text in to_move:
        connector = fps[text.GetText().split()[0]].GetPosition()
        candidates = sorted(((x, y) for x in range(2, 99) for y in range(2, 299)),
                            key=lambda p: (p[0] - pcb.ToMM(connector.x)) ** 2
                            + (p[1] - pcb.ToMM(connector.y)) ** 2)
        for x, y in candidates:
            text.SetPosition(pcb.VECTOR2I(pcb.FromMM(x), pcb.FromMM(y)))
            box = item_box(text)
            if box[0] < .5 or box[1] < .5 or box[2] > 99.5 or box[3] > 299.5:
                continue
            if text.GetText().startswith("J8  ") and box[3] >= 149.5:
                continue
            if any(overlap(box, b, .3) for b in obstacles):
                continue
            obstacles.append(box)
            print(f"Relocated silk {text.GetText()} to ({x}, {y})")
            break
        else:
            raise ValueError(f"No silk position for {text.GetText()}")
    # Non-copper drawing is a conditional review model, not an actual envelope.
    for y in (30, 190):
        for x1, y1, x2, y2 in ((63.73, y - 1.4, 89.13, y + 61.34),
                               (70.43, y + 61.34, 82.43, y + 76.34)):
            shape = pcb.PCB_SHAPE(board)
            shape.SetShape(pcb.SHAPE_T_RECT)
            shape.SetStart(pcb.VECTOR2I(pcb.FromMM(x1), pcb.FromMM(y1)))
            shape.SetEnd(pcb.VECTOR2I(pcb.FromMM(x2), pcb.FromMM(y2)))
            shape.SetLayer(pcb.Dwgs_User)
            shape.SetWidth(pcb.FromMM(.15))
            board.Add(shape)
        for text_value, x, yy in (("PROVISIONAL BODY", 76.43, y + 20),
                                  ("USB ACCESS?", 76.43, y + 68)):
            label = pcb.PCB_TEXT(board)
            label.SetText(text_value)
            label.SetPosition(pcb.VECTOR2I(pcb.FromMM(x), pcb.FromMM(yy)))
            label.SetTextSize(pcb.VECTOR2I(pcb.FromMM(.8), pcb.FromMM(.8)))
            label.SetTextThickness(pcb.FromMM(.12))
            label.SetLayer(pcb.Dwgs_User)
            board.Add(label)
    pcb.SaveBoard(str(OUT / "result.kicad_pcb"), board)


if __name__ == "__main__":
    try:
        {"prepare": prepare, "finish": finish, "tidy": tidy}[sys.argv[1]]()
    except Exception as exc:
        print(f"{type(exc).__name__}: {exc}", flush=True)
        sys.exit(1)
