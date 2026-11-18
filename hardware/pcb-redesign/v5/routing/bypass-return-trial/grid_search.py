#!/usr/bin/env python3
"""Time-limited, additive 0.5 mm-grid return search using native copper shapes."""
import heapq
import json
import math
import subprocess
import sys
import time
from pathlib import Path

import pcbnew as pcb

sys.path.insert(0, "/work/hardware/pcb-redesign/v5/routing/decoupling-trial")
from measure_paths import build, shortest

BOARD = Path("/out/result.kicad_pcb")
REPORT = "/out/grid-drc.json"
STEP = pcb.FromMM(0.5)
BUCKET = pcb.FromMM(4)
MARGIN = pcb.FromMM(0.6)
MAX_PER_LAYER = 25
PAIRS = (("C1", "U3"), ("C2", "U4"), ("C3", "U2"), ("C4", "U6"))
DIRS = [(i, j) for i in (-1, 0, 1) for j in (-1, 0, 1) if i or j]


def pt(p):
    p = p.GetPosition()
    return p.x, p.y


def in_buckets(a, b):
    for x in range((min(a[0], b[0]) - MARGIN) // BUCKET,
                   (max(a[0], b[0]) + MARGIN) // BUCKET + 1):
        for y in range((min(a[1], b[1]) - MARGIN) // BUCKET,
                       (max(a[1], b[1]) + MARGIN) // BUCKET + 1):
            yield x, y


def main():
    board = pcb.LoadBoard(str(BOARD))
    fps = {f.GetReference(): f for f in board.GetFootprints()}
    tables = {}
    for layer in (pcb.F_Cu, pcb.B_Cu):
        buckets = {}
        objs = []
        for fp in board.GetFootprints():
            for p in fp.Pads():
                if p.IsOnLayer(layer) and p.FlashLayer(layer) and p.GetNetname() != "GND":
                    objs.append((p, pcb.FromMM(0.301 if p.GetAttribute() == pcb.PAD_ATTRIB_PTH else 0.201)))
        objs.extend((t, pcb.FromMM(0.201)) for t in board.GetTracks()
                    if t.IsOnLayer(layer) and t.GetNetname() != "GND")
        for obj, clearance in objs:
            shape = obj.GetEffectiveShape(layer)
            if shape.IsNull():
                continue
            box = obj.GetBoundingBox()
            a, b = (box.GetLeft(), box.GetTop()), (box.GetRight(), box.GetBottom())
            for key in in_buckets(a, b):
                buckets.setdefault(key, []).append((shape, clearance))
        tables[layer] = buckets

    records = []
    for cap, ic in PAIRS:
        start = next(p for p in fps[cap].Pads() if p.GetNetname() == "GND")
        target = next(p for p in fps[ic].Pads() if p.GetNumber() == "7")
        if target.GetNetname() != "GND":
            raise ValueError(f"{ic}.7 not GND")
        a, b = pt(start), pt(target)
        graph, _ = build(board, "GND")
        previous = shortest(graph, ("pad", cap, start.GetNumber()), {("pad", ic, "7")})
        if previous is None:
            raise ValueError("baseline open")
        results = []
        accepted = None
        for layer in (pcb.F_Cu, pcb.B_Cu):
            begin = time.monotonic()
            cache = {}
            checks = 0

            def clear(x, y):
                nonlocal checks
                key = tuple(sorted((x, y)))
                if key in cache:
                    return cache[key]
                track = pcb.PCB_TRACK(board)
                track.SetStart(pcb.VECTOR2I(*x))
                track.SetEnd(pcb.VECTOR2I(*y))
                track.SetLayer(layer)
                track.SetWidth(pcb.FromMM(0.3))
                track.SetNetCode(start.GetNetCode())
                shape = track.GetEffectiveShape(layer)
                checks += 1
                valid = all(shape.GetClearance(obstacle) >= distance
                            for bucket in in_buckets(x, y)
                            for obstacle, distance in tables[layer].get(bucket, ()))
                cache[key] = valid
                return valid

            xmin, xmax = (min(a[0], b[0]) - 8 * pcb.FromMM(1)) // STEP, (max(a[0], b[0]) + 8 * pcb.FromMM(1)) // STEP
            ymin, ymax = (min(a[1], b[1]) - 8 * pcb.FromMM(1)) // STEP, (max(a[1], b[1]) + 8 * pcb.FromMM(1)) // STEP
            queue, costs, prev = [], {}, {}
            for ix in range(round(a[0] / STEP) - 2, round(a[0] / STEP) + 3):
                for iy in range(round(a[1] / STEP) - 2, round(a[1] / STEP) + 3):
                    q = (ix * STEP, iy * STEP)
                    d = math.dist(a, q)
                    if d <= 1.5 * pcb.FromMM(1) and (d == 0 or clear(a, q)):
                        costs[q] = d
                        prev[q] = None
                        heapq.heappush(queue, (d + math.dist(q, b), d, q))
            found = None
            while queue and time.monotonic() - begin < MAX_PER_LAYER:
                _, cost, q = heapq.heappop(queue)
                if costs[q] != cost:
                    continue
                if math.dist(q, b) <= 1.5 * pcb.FromMM(1) and (q == b or clear(q, b)):
                    found = q
                    break
                for dx, dy in DIRS:
                    nxt = (q[0] + dx * STEP, q[1] + dy * STEP)
                    if not (xmin <= nxt[0] // STEP <= xmax and ymin <= nxt[1] // STEP <= ymax):
                        continue
                    newcost = cost + math.dist(q, nxt)
                    if newcost + math.dist(nxt, b) >= previous[0] - pcb.FromMM(0.5):
                        continue
                    if newcost < costs.get(nxt, math.inf) and clear(q, nxt):
                        costs[nxt] = newcost
                        prev[nxt] = q
                        heapq.heappush(queue, (newcost + math.dist(nxt, b), newcost, nxt))
            result = {"layer": board.GetLayerName(layer), "elapsed_seconds": round(time.monotonic() - begin, 2),
                      "tested_edges": checks, "explored_nodes": len(costs), "found": found is not None}
            if found is not None:
                coords = [found]
                while prev[coords[-1]] is not None:
                    coords.append(prev[coords[-1]])
                coords.reverse()
                coords = [a] + coords + [b]
                coords = [p for i, p in enumerate(coords) if not i or p != coords[i - 1]]
                reduced = [coords[0]]
                for p in coords[1:]:
                    if len(reduced) >= 2:
                        x, y = reduced[-2], reduced[-1]
                        if (y[0] - x[0]) * (p[1] - y[1]) == (y[1] - x[1]) * (p[0] - y[0]):
                            reduced.pop()
                    reduced.append(p)
                tracks = []
                for x, y in zip(reduced, reduced[1:]):
                    t = pcb.PCB_TRACK(board)
                    t.SetStart(pcb.VECTOR2I(*x))
                    t.SetEnd(pcb.VECTOR2I(*y))
                    t.SetWidth(pcb.FromMM(0.3))
                    t.SetLayer(layer)
                    t.SetNetCode(start.GetNetCode())
                    board.Add(t)
                    tracks.append(t)
                pcb.SaveBoard(str(BOARD), board)
                drc = subprocess.run(["kicad-cli", "pcb", "drc", "--format", "json",
                    "--severity-all", "--exit-code-violations", "--output", REPORT, str(BOARD)],
                    stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
                result["drc_exit"] = drc.returncode
                if drc.returncode == 0:
                    accepted = {"layer": board.GetLayerName(layer),
                                "points_mm": [[pcb.ToMM(x), pcb.ToMM(y)] for x, y in reduced]}
                else:
                    for t in tracks:
                        board.Remove(t)
                    if drc.returncode != 5:
                        raise RuntimeError(f"DRC failed {drc.returncode}: {drc.stderr}")
            results.append(result)
            if accepted:
                break
        pcb.SaveBoard(str(BOARD), board)
        record = {"capacitor": cap, "capacitor_pad": start.GetNumber(), "ic": ic,
                  "target_pad": "7", "old_path_mm": round(pcb.ToMM(round(previous[0])), 3),
                  "layers": results, "accepted": accepted}
        records.append(record)
        print(json.dumps(record), flush=True)
    Path("/out/grid-search.json").write_text(json.dumps({"step_mm": 0.5,
        "time_limit_seconds_per_layer": MAX_PER_LAYER, "results": records}, indent=2) + "\n")


if __name__ == "__main__":
    main()
