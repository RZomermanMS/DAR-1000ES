#!/usr/bin/env python3
"""Search bounded same-layer supply shortcuts with native geometry and DRC."""
import heapq
import json
import math
import subprocess
from pathlib import Path

import pcbnew as pcb

HERE = Path(__file__).resolve().parent
PATH = HERE / "result.kicad_pcb"
STEP = pcb.FromMM(0.5)
MARGIN = pcb.FromMM(8)
PAIRS = (("C1", "U3", "14", 12.804), ("C2", "U4", "14", 12.784),
         ("C3", "U2", "14", 26.468), ("C4", "U6", "14", 38.401),
         ("C5", "U7", "14", 32.228), ("C6", "U8", "14", 105.586),
         ("C8", "U10", "2", 22.526))


def main():
    board = pcb.LoadBoard(str(PATH))
    fps = {f.GetReference(): f for f in board.GetFootprints()}
    results = []
    for cap, ic, pin, old in PAIRS:
        src = next(p for p in fps[cap].Pads() if p.GetNetname() != "GND")
        dst = next(p for p in fps[ic].Pads() if p.GetNumber() == pin)
        if src.GetNetname() != dst.GetNetname():
            raise ValueError(f"net mismatch {cap}/{ic}")
        a = (src.GetPosition().x, src.GetPosition().y)
        b = (dst.GetPosition().x, dst.GetPosition().y)
        lo = (min(a[0], b[0]) - MARGIN, min(a[1], b[1]) - MARGIN)
        hi = (max(a[0], b[0]) + MARGIN, max(a[1], b[1]) + MARGIN)
        accepted = None
        for layer in (pcb.B_Cu, pcb.F_Cu):
            obs = []
            for f in board.GetFootprints():
                for p in f.Pads():
                    if p.IsOnLayer(layer) and p.FlashLayer(layer) and p.GetNetname() != src.GetNetname():
                        obs.append(p)
            obs.extend(t for t in board.GetTracks()
                       if t.IsOnLayer(layer) and t.GetNetname() != src.GetNetname())
            obstacles = []
            for item in obs:
                box = item.GetBoundingBox()
                if (box.GetX() > hi[0] + STEP or box.GetRight() < lo[0] - STEP or
                        box.GetY() > hi[1] + STEP or box.GetBottom() < lo[1] - STEP):
                    continue
                shape = item.GetEffectiveShape(layer)
                if not shape.IsNull():
                    obstacles.append((shape, box.GetX(), box.GetY(), box.GetRight(), box.GetBottom()))

            def clear(x, y):
                t = pcb.PCB_TRACK(board)
                t.SetStart(pcb.VECTOR2I(*x))
                t.SetEnd(pcb.VECTOR2I(*y))
                t.SetWidth(pcb.FromMM(0.3))
                t.SetLayer(layer)
                sh = t.GetEffectiveShape(layer)
                gap = pcb.FromMM(0.201)
                radius = pcb.FromMM(0.36)
                xmin, xmax = min(x[0], y[0]) - radius, max(x[0], y[0]) + radius
                ymin, ymax = min(x[1], y[1]) - radius, max(x[1], y[1]) + radius
                return all(sh.GetClearance(s) >= gap for s, x1, y1, x2, y2 in obstacles
                           if x1 <= xmax and x2 >= xmin and y1 <= ymax and y2 >= ymin)

            start = (round(a[0] / STEP), round(a[1] / STEP))
            goal = (round(b[0] / STEP), round(b[1] / STEP))
            pt = lambda n: (n[0] * STEP, n[1] * STEP)
            if not clear(a, pt(start)) or not clear(pt(goal), b):
                continue
            queue = [(math.dist(start, goal), 0, start)]
            cost, previous = {start: 0}, {}
            while queue:
                _, d, current = heapq.heappop(queue)
                if d != cost[current]:
                    continue
                if current == goal:
                    break
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        if dx == dy == 0:
                            continue
                        nxt = (current[0] + dx, current[1] + dy)
                        q = pt(nxt)
                        if not lo[0] <= q[0] <= hi[0] or not lo[1] <= q[1] <= hi[1]:
                            continue
                        nd = d + math.hypot(dx, dy)
                        if nd >= cost.get(nxt, math.inf) or not clear(pt(current), q):
                            continue
                        cost[nxt] = nd
                        previous[nxt] = current
                        heapq.heappush(queue, (nd + math.dist(nxt, goal), nd, nxt))
            if goal not in cost or cost[goal] * 0.5 >= old - 1:
                continue
            nodes = [goal]
            while nodes[-1] != start:
                nodes.append(previous[nodes[-1]])
            points = [a] + [pt(n) for n in reversed(nodes)] + [b]
            points = [v for i, v in enumerate(points) if not i or v != points[i - 1]]
            added = []
            for x, y in zip(points, points[1:]):
                t = pcb.PCB_TRACK(board)
                t.SetStart(pcb.VECTOR2I(*x))
                t.SetEnd(pcb.VECTOR2I(*y))
                t.SetWidth(pcb.FromMM(0.3))
                t.SetLayer(layer)
                t.SetNetCode(src.GetNetCode())
                board.Add(t)
                added.append(t)
            pcb.SaveBoard(str(PATH), board)
            report = HERE / "grid-drc.json"
            run = subprocess.run(["kicad-cli", "pcb", "drc", "--refill-zones", "--format", "json",
                                  "--severity-all", "-o", str(report), str(PATH)],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if run.returncode:
                raise RuntimeError("KiCad DRC failed")
            drc = json.loads(report.read_text())
            if not drc["violations"] and not drc["unconnected_items"]:
                accepted = {"cap": cap, "target": f"{ic}.{pin}", "layer": board.GetLayerName(layer),
                            "points_mm": [[pcb.ToMM(x), pcb.ToMM(y)] for x, y in points]}
                break
            for t in added:
                board.Remove(t)
        results.append({"capacitor": cap, "route": accepted})
        print(json.dumps(results[-1]), flush=True)
    pcb.SaveBoard(str(PATH), board)


if __name__ == "__main__":
    main()
