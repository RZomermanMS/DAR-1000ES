#!/usr/bin/env python3
"""Prepare and import a fresh routing of the experimental edge placement."""
import importlib.util
import json
import math
import re
import sys
from pathlib import Path

import pcbnew as pcb

ROOT = Path(__file__).resolve().parent.parent
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
    fps = {f.GetReference(): f for f in board.GetFootprints()}
    move(fps["U1-CONTROLLER1"], 66, 5, 0)
    move(fps["U6-AUDIO1"], 86, 295, 180)
    # Conservative assumed installed-board and USB envelopes, not verified CAD.
    envelopes = [(64.73, 0, 90.13, 62.74), (71.43, 62.74, 83.43, 77.74),
                 (61.87, 237.26, 87.27, 300), (68.57, 222.26, 80.57, 237.26)]
    moving = {"U1-CONTROLLER1", "U6-AUDIO1", "C10", "C11", "C12", "C13"}
    obstacles = [bbox(fp) for ref, fp in fps.items() if ref not in moving] + envelopes
    results = {}
    for cap, esp, limits in (
        ("C11", "U1-CONTROLLER1", (48, 64, 45, 70)),
        ("C10", "U1-CONTROLLER1", (48, 64, 45, 70)),
        ("C13", "U6-AUDIO1", (87, 99, 230, 260)),
        ("C12", "U6-AUDIO1", (87, 99, 230, 260)),
    ):
        fp = fps[cap]
        supply = pads(fps[esp])["J1.21"].GetPosition()
        ground = pads(fps[esp])["J1.22"].GetPosition()
        xmin, xmax, ymin, ymax = limits
        candidates = []
        for x in range(xmin, xmax + 1):
            for y in range(ymin, ymax + 1):
                for angle in (0, 90, 180, 270):
                    move(fp, x, y, angle)
                    box = bbox(fp)
                    if box[0] < .5 or box[1] < .5 or box[2] > 99.5 or box[3] > 299.5:
                        continue
                    if any(overlap(box, b) for b in obstacles):
                        continue
                    pp = pads(fp)
                    sd = distance(pp["1"].GetPosition(), supply)
                    gd = distance(pp["2"].GetPosition(), ground)
                    candidates.append((sd + gd, sd, gd, x, y, angle))
        if not candidates:
            raise ValueError(f"No physical placement candidate for {cap}")
        _, sd, gd, x, y, angle = min(candidates)
        move(fp, x, y, angle)
        obstacles.append(bbox(fp))
        results[cap] = {"at_mm": [x, y], "angle": angle,
                        "supply_center_mm": round(sd, 3), "ground_center_mm": round(gd, 3)}
    ops.verify_netlist(board, str(NETLIST))
    ops.verify_uart(str(NETLIST))
    ops.audit_sections(board, 150, "lower")
    ops.audit_component_envelopes(board, 150, "lower")
    pcb.SaveBoard(str(OUT / "input.kicad_pcb"), board)
    if not pcb.ExportSpecctraDSN(board, str(OUT / "route.dsn")):
        raise ValueError("DSN export failed")
    (OUT / "placement.json").write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps(results, indent=2))


def finish():
    board = pcb.LoadBoard(str(OUT / "input.kicad_pcb"))
    if not pcb.ImportSpecctraSES(board, str(OUT / "route.ses")):
        raise ValueError("SES import failed")
    ops.verify_netlist(board, str(NETLIST))
    ops.audit_sections(board, 150, "lower")
    ops.audit_component_envelopes(board, 150, "lower")
    tracks = list(board.GetTracks())
    segments = [t for t in tracks if not isinstance(t, pcb.PCB_VIA)]
    if not segments or min(t.GetWidth() for t in segments) < pcb.FromMM(.25):
        raise ValueError("Missing or undersized tracks")
    source = pcb.LoadBoard(str(SOURCE))
    for zone in source.Zones():
        if not zone.GetIsRuleArea():
            board.Add(pcb.ZONE(zone))
    pcb.SaveBoard(str(OUT / "result.kicad_pcb"), board)
    print(f"Imported {len(segments)} segments, {len(tracks) - len(segments)} vias")


def tidy():
    board = pcb.LoadBoard(str(OUT / "result.kicad_pcb"))
    legends = ("J8  ", "J9  ", "J10  ", "J11  ", "JP1  ", "JP2  ")
    to_move = []
    for text in board.GetDrawings():
        if isinstance(text, pcb.PCB_TEXT):
            if text.GetText().startswith(legends):
                to_move.append(text)
            elif text.GetText() in ("1 LOCAL", "2 AUDIO") and text.GetPosition().y > pcb.FromMM(200):
                x = 52 if text.GetText() == "2 AUDIO" else 49
                text.SetPosition(pcb.VECTOR2I(pcb.FromMM(x), text.GetPosition().y))
    fps = {f.GetReference(): f for f in board.GetFootprints()}
    for ref, x, y in (("C11", 55, 52), ("C10", 54, 59), ("C13", 95, 241)):
        fps[ref].Reference().SetPosition(pcb.VECTOR2I(pcb.FromMM(x), pcb.FromMM(y)))
    def item_box(item):
        b = item.GetBoundingBox()
        return tuple(pcb.ToMM(v) for v in (b.GetX(), b.GetY(), b.GetRight(), b.GetBottom()))
    obstacles = [item_box(f) for f in board.GetFootprints()]
    obstacles += [item_box(t) for t in board.GetDrawings()
                  if t.GetLayer() == pcb.F_SilkS and t not in to_move]
    obstacles += [(64.73, 0, 90.13, 62.74), (71.43, 62.74, 83.43, 77.74),
                  (61.87, 237.26, 87.27, 300), (68.57, 222.26, 80.57, 237.26)]
    if len(to_move) != 6:
        raise ValueError("Expected six connector legends")
    for text in to_move:
        original = text.GetPosition()
        candidates = sorted(((x, y) for x in range(20, 81) for y in range(2, 299)),
                            key=lambda p: (p[0] - pcb.ToMM(original.x)) ** 2
                            + (p[1] - pcb.ToMM(original.y)) ** 2)
        for x, y in candidates:
            text.SetPosition(pcb.VECTOR2I(pcb.FromMM(x), pcb.FromMM(y)))
            box = item_box(text)
            if box[0] < .5 or box[1] < .5 or box[2] > 99.5 or box[3] > 299.5:
                continue
            if any(overlap(box, b, .3) for b in obstacles):
                continue
            obstacles.append(box)
            print(f"Relocated silk {text.GetText()} to ({x}, {y})")
            break
        else:
            raise ValueError(f"No silk position for {text.GetText()}")
    pcb.SaveBoard(str(OUT / "result.kicad_pcb"), board)


if __name__ == "__main__":
    try:
        {"prepare": prepare, "finish": finish, "tidy": tidy}[sys.argv[1]]()
    except Exception as exc:
        print(f"{type(exc).__name__}: {exc}", flush=True)
        sys.exit(1)
