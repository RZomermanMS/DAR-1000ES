#!/usr/bin/env python3
"""Annotate the installed carrier envelope without changing copper or placement."""
import json
import math
import shutil
from pathlib import Path

import pcbnew as pcb

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "esp-edge-candidate/result.kicad_pcb"
board = pcb.LoadBoard(str(SOURCE))
fps = {f.GetReference(): f for f in board.GetFootprints()}
body = (-1.27, -1.40, 24.13, 61.34)
library = HERE / "DAR1000ES.pretty"
shutil.copytree(HERE.parent.parent / "DAR1000ES.pretty", library)
name = "Bottom_DAR1000ES__ESP32-S3-DevKitC-1_2xSocket_1x22_P2.54mm_W22.86mm.kicad_mod"
footprint = library / name
text = footprint.read_text()
lines = [
    (-1.27, -1.40, 24.13, -1.40, .15),
    (24.13, -1.40, 24.13, 61.34, .15),
    (24.13, 61.34, -1.27, 61.34, .15),
    (-1.27, 61.34, -1.27, -1.40, .15),
    (8, 0, 14.86, 0, .3),
]
art = "".join(f'\t(fp_line (start {x1} {y1}) (end {x2} {y2}) '
              f'(stroke (width {width}) (type solid)) (layer "F.Fab"))\n'
              for x1, y1, x2, y2, width in lines)
assert text.count("\t(attr through_hole)") == 1
footprint.write_text(text.replace("\t(attr through_hole)", "\t(attr through_hole)\n" + art.rstrip()))
table = HERE / "fp-lib-table"
table.write_text(table.read_text().replace("${KIPRJMOD}/../../DAR1000ES.pretty",
                                           "${KIPRJMOD}/DAR1000ES.pretty"))


def point(fp, x, y):
    a = math.radians(fp.GetOrientationDegrees())
    p = fp.GetPosition()
    return pcb.VECTOR2I(p.x + round((x * math.cos(a) + y * math.sin(a)) * 1_000_000),
                        p.y + round((-x * math.sin(a) + y * math.cos(a)) * 1_000_000))


def box(item):
    b = item.GetBoundingBox()
    return [pcb.ToMM(v) for v in (b.GetLeft(), b.GetTop(), b.GetRight(), b.GetBottom())]


def courtyard(fp):
    shapes = [box(i) for i in fp.GraphicalItems()
              if i.GetLayer() in (pcb.F_CrtYd, pcb.B_CrtYd)]
    shapes = shapes or [box(p) for p in fp.Pads()]
    return [min(b[0] for b in shapes), min(b[1] for b in shapes),
            max(b[2] for b in shapes), max(b[3] for b in shapes)]


def gap(a, b):
    return math.hypot(max(a[0] - b[2], b[0] - a[2], 0),
                      max(a[1] - b[3], b[1] - a[3], 0))


def area(a, b):
    return max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))


report = {}
for ref in ("U1-CONTROLLER1", "U6-AUDIO1"):
    fp = fps[ref]
    points = [point(fp, x, y) for x, y in ((body[0], body[1]), (body[2], body[1]),
                                             (body[2], body[3]), (body[0], body[3]))]
    for start, end in zip(points, points[1:] + points[:1]):
        line = pcb.PCB_SHAPE(fp)
        line.SetShape(pcb.SHAPE_T_SEGMENT)
        line.SetStart(start)
        line.SetEnd(end)
        line.SetLayer(pcb.F_Fab)
        line.SetWidth(pcb.FromMM(.15))
        fp.Add(line)
    # Pin-1-end crossbar distinguishes the antenna end without inventing a
    # radiator outline. Socket fabrication outlines remain intact.
    line = pcb.PCB_SHAPE(fp)
    line.SetShape(pcb.SHAPE_T_SEGMENT)
    line.SetStart(point(fp, 8, 0))
    line.SetEnd(point(fp, 14.86, 0))
    line.SetLayer(pcb.F_Fab)
    line.SetWidth(pcb.FromMM(.3))
    fp.Add(line)
    bounds = [pcb.ToMM(min(p.x for p in points)), pcb.ToMM(min(p.y for p in points)),
              pcb.ToMM(max(p.x for p in points)), pcb.ToMM(max(p.y for p in points))]
    distances = sorted((round(gap(bounds, courtyard(other)), 3), other_ref)
                       for other_ref, other in fps.items() if other_ref != ref)
    # Non-authoritative, approximate raster estimate: diagnostic only.
    approx = (2.4, -7.9, 20.5, -1.5)
    ap = [point(fp, x, y) for x in (approx[0], approx[2]) for y in (approx[1], approx[3])]
    antenna = [pcb.ToMM(min(p.x for p in ap)), pcb.ToMM(min(p.y for p in ap)),
               pcb.ToMM(max(p.x for p in ap)), pcb.ToMM(max(p.y for p in ap))]
    report[ref] = {
        "carrier_bbox_mm": bounds,
        "nearest_courtyard_bbox_gap_mm": distances[0][0],
        "nearest_courtyard_reference": distances[0][1],
        "zero_gap_courtyard_bboxes": [r for d, r in distances if d == 0],
        "edge_inset_mm": round(min(bounds[0], bounds[1], 100 - bounds[2], 300 - bounds[3]), 3),
        "unverified_raster_feature_bbox_mm": antenna,
        "unverified_feature_substrate_intersection_mm2": round(area(antenna, (0, 0, 100, 300)), 3),
        "unverified_feature_other_courtyard_bbox_hits": [
            r for r, f in fps.items() if r != ref and area(antenna, courtyard(f)) > 0],
        "unverified_feature_track_via_bbox_hits": sum(area(antenna, box(t)) > 0 for t in board.GetTracks()),
    }

pcb.SaveBoard(str(HERE / "result.kicad_pcb"), board)
(HERE / "geometry.json").write_text(json.dumps(report, indent=2) + "\n")
