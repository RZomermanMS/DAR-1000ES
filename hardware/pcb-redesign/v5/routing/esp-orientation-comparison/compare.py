#!/usr/bin/env python3
"""Coarse rigid-assembly placement comparison; requires KiCad 10 pcbnew."""
import hashlib
import json
import math
from collections import Counter
from pathlib import Path

import pcbnew as pcb

HERE = Path(__file__).resolve().parent
BOARD = HERE.parent / "placement-current/result.kicad_pcb"
EXPECTED = "1639ae39478dff811224cf6ff1e299ec685bb6e8568631e4d861dfafcb36eafa"
ESPS = ("U1-CONTROLLER1", "U6-AUDIO1")
POWER = {"GND", "LOCAL_5V", "SONY_5V_SENSE"}
STEP = 2
GRID = 5
CARRIER = (-1.27, -1.40, 24.13, 61.34)
# Sensitivity envelope only, not a measured connector, plug or cable.
USB_ACCESS = (5.43, 61.34, 17.43, 76.34)
BOARD_BOUNDS = (0, 0, 100, 300)


def mm(v):
    return pcb.ToMM(v)


def xy(v):
    return (mm(v.x), mm(v.y))


def bbox(b):
    return tuple(mm(v) for v in (b.GetLeft(), b.GetTop(), b.GetRight(), b.GetBottom()))


def union(boxes):
    return (min(b[0] for b in boxes), min(b[1] for b in boxes),
            max(b[2] for b in boxes), max(b[3] for b in boxes))


def overlap(a, b):
    return max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))


def rotate(x, y, angle):
    # KiCad angles are counterclockwise in a y-down coordinate system.
    return ((x, y), (y, -x), (-x, -y), (-y, x))[angle // 90]


def transformed(rect, x, y, angle):
    a, b, c, d = rect
    corners = [rotate(i, j, angle) for i in (a, c) for j in (b, d)]
    return (x + min(p[0] for p in corners), y + min(p[1] for p in corners),
            x + max(p[0] for p in corners), y + max(p[1] for p in corners))


def inside(a, b):
    return a[0] >= b[0] and a[1] >= b[1] and a[2] <= b[2] and a[3] <= b[3]


def boundary_clearance(box):
    return min(box[0], box[1], 100 - box[2], 300 - box[3])


def radio_end_edge_distance(box, angle):
    """Distance from the carrier's pin-1 end to the edge in its outward direction."""
    return (box[1], box[0], 300 - box[3], 100 - box[2])[angle // 90]


def box_gap(a, b):
    return math.hypot(max(a[0]-b[2], b[0]-a[2], 0),
                      max(a[1]-b[3], b[1]-a[3], 0))


def expand(box, amount):
    return (box[0]-amount, box[1]-amount, box[2]+amount, box[3]+amount)


def footprint_box(fp):
    shapes = [bbox(g.GetBoundingBox()) for g in fp.GraphicalItems()
              if g.GetLayer() in (pcb.F_CrtYd, pcb.B_CrtYd)]
    # Missing courtyards fall back to pads; avoid text/silk inflation.
    return union(shapes or [bbox(p.GetBoundingBox()) for p in fp.Pads()])


def links(pads, external, x, y, angle):
    lines = []
    for px, py, net, number in pads:
        if not net or net not in external:
            continue
        dx, dy = rotate(px, py, angle)
        p = (x + dx, y + dy)
        q = min(external[net], key=lambda q: (math.dist(p, q), q))
        lines.append((p, q, net, number))
    return lines


def metrics(lines):
    signal = [v for v in lines if v[2] not in POWER]
    cells = Counter()
    for (x1, y1), (x2, y2), _, _ in signal:
        # Deterministic horizontal-then-vertical Manhattan L. Per-link cells
        # are counted once, including shared cells at the bend.
        c1, r1, c2, r2 = (math.floor(x1 / GRID), math.floor(y1 / GRID),
                          math.floor(x2 / GRID), math.floor(y2 / GRID))
        touched = {(c, r1) for c in range(min(c1, c2), max(c1, c2) + 1)}
        touched |= {(c2, r) for r in range(min(r1, r2), max(r1, r2) + 1)}
        cells.update(touched)
    return {
        "links": len(lines), "signal_links": len(signal),
        "all_link_euclidean_mm": round(sum(math.dist(p, q) for p, q, _, _ in lines), 3),
        "signal_link_euclidean_mm": round(sum(math.dist(p, q) for p, q, _, _ in signal), 3),
        "signal_link_manhattan_mm": round(sum(abs(p[0]-q[0]) + abs(p[1]-q[1]) for p, q, _, _ in signal), 3),
        "signal_grid_peak": max(cells.values(), default=0),
        "signal_grid_cells_ge_3": sum(v >= 3 for v in cells.values()),
    }


def main():
    actual = hashlib.sha256(BOARD.read_bytes()).hexdigest()
    if actual != EXPECTED:
        raise ValueError(f"Unexpected board SHA-256: {actual}")
    board = pcb.LoadBoard(str(BOARD))
    fps = {f.GetReference(): f for f in board.GetFootprints()}
    result = {"board_sha256": actual, "grid_step_mm": STEP,
              "carrier_local_mm": CARRIER, "usb_access_hypothesis_local_mm": USB_ACCESS,
              "radio_geometry": "unknown", "orientations": {}}
    for ref, ymin, ymax in ((ESPS[0], 0, 150), (ESPS[1], 150, 300)):
        fp = fps[ref]
        assert fp.GetOrientationDegrees() % 360 == 0
        ox, oy = xy(fp.GetPosition())
        pads = [(xy(p.GetPosition())[0] - ox, xy(p.GetPosition())[1] - oy,
                 p.GetNetname(), p.GetNumber()) for p in fp.Pads()]
        assert len(pads) == 44
        padboxes = [tuple(v - (ox if i % 2 == 0 else oy)
                          for i, v in enumerate(bbox(p.GetBoundingBox()))) for p in fp.Pads()]
        external = {}
        obstacles = {}
        other_pads = []
        for other, f in fps.items():
            if other == ref:
                continue
            obstacles[other] = footprint_box(f)
            for p in f.Pads():
                other_pads.append((other, p.GetNumber(), bbox(p.GetBoundingBox())))
                if p.GetNetname():
                    external.setdefault(p.GetNetname(), []).append(xy(p.GetPosition()))
        # The other ESP is an installed assembly, not merely two courtyards.
        other = ESPS[1] if ref == ESPS[0] else ESPS[0]
        f = fps[other]
        obstacles[other] = transformed(CARRIER, *xy(f.GetPosition()), int(f.GetOrientationDegrees()) % 360)
        connector_boxes = {k: expand(v, 5) for k, v in obstacles.items()
                           if k.startswith("J") and k[1:].isdigit()}
        domain = (0, ymin, 100, ymax)

        def summarize(x, y, angle):
            b, u = (transformed(rect, x, y, angle) for rect in (CARRIER, USB_ACCESS))
            bh = sorted(k for k, ob in obstacles.items() if overlap(b, ob) > 1e-8)
            uh = sorted(k for k, ob in obstacles.items() if overlap(u, ob) > 1e-8)
            connector_hits = sorted(k for k, ob in connector_boxes.items()
                                    if overlap(b, ob) > 1e-8 or overlap(u, ob) > 1e-8)
            edges = [boundary_clearance(transformed(p, x, y, angle)) for p in padboxes]
            nearest = min((box_gap(transformed(pbox, x, y, angle), ob), pads[i][3], ref2, n)
                          for i, pbox in enumerate(padboxes) for ref2, n, ob in other_pads)
            nearest_hole = min((box_gap(b, ob), ref2) for ref2, ob in obstacles.items()
                               if ref2.startswith("H"))
            return {
                "origin_mm": [x, y], "angle": angle, "carrier_mm": b,
                "carrier_inside_domain": inside(b, domain),
                "usb_access_hypothesis_mm": u,
                "carrier_courtyard_overlaps": bh,
                "usb_access_hypothesis_courtyard_overlaps": uh,
                "assumed_connector_envelope_overlaps": connector_hits,
                "usb_access_hypothesis_outside_board_area_mm2": round((u[2]-u[0])*(u[3]-u[1])-overlap(u, BOARD_BOUNDS), 3),
                "pad_edge_min_mm": round(min(edges), 3),
                "pad_to_other_pad_bbox_lower_bound_mm": round(nearest[0], 3),
                "nearest_pad_pair": [nearest[1], nearest[2], nearest[3]],
                "carrier_to_hole_courtyard_bbox_gap_mm": round(nearest_hole[0], 3),
                "nearest_hole_courtyard": nearest_hole[1],
                "radio_end_edge_distance_mm": round(radio_end_edge_distance(b, angle), 3),
                **metrics(links(pads, external, x, y, angle)),
            }

        per_angle = {}
        offgrid = (66, 5, 0) if ref == ESPS[0] else (86, 295, 180)
        flush = (66, 1.4, 0) if ref == ESPS[0] else (86, 298.6, 180)
        result["orientations"][ref] = {
            "baseline": summarize(ox, oy, 0),
            "existing_edge_candidate": summarize(*offgrid),
            "exact_carrier_edge_flush_illustration": summarize(*flush),
        }
        for angle in (0, 90, 180, 270):
            candidates = []
            considered = 0
            collision_free = 0
            for x in range(0, 101, STEP):
                for y in range(ymin, ymax + 1, STEP):
                    b = transformed(CARRIER, x, y, angle)
                    if not inside(b, domain):
                        continue
                    considered += 1
                    u = transformed(USB_ACCESS, x, y, angle)
                    body_hits = sorted(k for k, ob in obstacles.items() if overlap(b, ob) > 1e-8)
                    usb_hits = sorted(k for k, ob in obstacles.items() if overlap(u, ob) > 1e-8)
                    edge = min(boundary_clearance(transformed(p, x, y, angle)) for p in padboxes)
                    if not body_hits and not usb_hits and edge >= 0.25:
                        collision_free += 1
                    # This edge preference does not model RF geometry or clearance.
                    rank_prefix = (len(body_hits) + len(usb_hits),
                                   edge < 0.25, round(radio_end_edge_distance(b, angle), 6))
                    candidates.append((rank_prefix, x, y))
            if not candidates:
                per_angle[str(angle)] = {"considered": 0}
                continue
            best_prefix = min(c[0] for c in candidates)
            finalists = [c for c in candidates if c[0] == best_prefix]
            ranked = []
            for prefix, x, y in finalists:
                m = metrics(links(pads, external, x, y, angle))
                ranked.append((m["signal_link_euclidean_mm"], m["signal_grid_peak"],
                               m["signal_grid_cells_ge_3"], x, y))
            _, _, _, x, y = min(ranked)
            feasible = [c for c in candidates if c[0][0] == 0 and not c[0][1]]
            signal_choice = None
            if feasible:
                options = [(metrics(links(pads, external, x, y, angle))["signal_link_euclidean_mm"], x, y)
                           for _, x, y in feasible]
                _, sx, sy = min(options)
                signal_choice = summarize(sx, sy, angle)
            per_angle[str(angle)] = {
                "considered": considered, "collision_free_and_pad_edge_ge_0_25": collision_free,
                "edge_first": summarize(x, y, angle),
                "signal_first_feasible": signal_choice,
            }
        result["orientations"][ref].update(per_angle)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
