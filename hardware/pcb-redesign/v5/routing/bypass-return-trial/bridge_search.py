#!/usr/bin/env python3
"""Try short same-layer GND pad bridges that improve true capacitor-to-pin-7 paths."""
import heapq
import json
import math
import subprocess
import sys
import time
from pathlib import Path

import pcbnew as pcb

sys.path.insert(0, "/work/hardware/pcb-redesign/v5/routing/decoupling-trial")
from measure_paths import build

BOARD = Path("/out/result.kicad_pcb")
PAIRS = (("C1", "U3"), ("C2", "U4"), ("C3", "U2"), ("C4", "U6"))
LIMIT = 20
MAX_BRIDGES = 600


def distances(graph, source):
    queue, best = [(0, 0, source)], {source: 0}
    serial = 0
    while queue:
        d, _, node = heapq.heappop(queue)
        if d != best[node]:
            continue
        for nxt, length, _ in graph[node]:
            nd = d + length
            if nd < best.get(nxt, math.inf):
                best[nxt] = nd
                serial += 1
                heapq.heappush(queue, (nd, serial, nxt))
    return best


def position(p):
    p = p.GetPosition()
    return p.x, p.y


def main():
    board = pcb.LoadBoard(str(BOARD))
    fps = {f.GetReference(): f for f in board.GetFootprints()}
    obstacles = {}
    for layer in (pcb.F_Cu, pcb.B_Cu):
        items = []
        for fp in board.GetFootprints():
            for p in fp.Pads():
                if p.IsOnLayer(layer) and p.FlashLayer(layer) and p.GetNetname() != "GND":
                    shape = p.GetEffectiveShape(layer)
                    if not shape.IsNull():
                        items.append((shape, pcb.FromMM(0.301 if p.GetAttribute() == pcb.PAD_ATTRIB_PTH else 0.201)))
        for t in board.GetTracks():
            if t.IsOnLayer(layer) and t.GetNetname() != "GND":
                shape = t.GetEffectiveShape(layer)
                if not shape.IsNull():
                    items.append((shape, pcb.FromMM(0.201)))
        obstacles[layer] = items

    records = []
    for cap, ic in PAIRS:
        start = next(p for p in fps[cap].Pads() if p.GetNetname() == "GND")
        target = next(p for p in fps[ic].Pads() if p.GetNumber() == "7")
        if target.GetNetname() != "GND":
            raise ValueError(f"{ic}.7 not GND")
        graph, pads = build(board, "GND")
        ds = distances(graph, ("pad", cap, start.GetNumber()))
        dt = distances(graph, ("pad", ic, "7"))
        old = ds[("pad", ic, "7")]
        candidates = []
        for i, (refa, pa) in enumerate(pads):
            na = ("pad", refa, pa.GetNumber())
            if na not in ds:
                continue
            for refb, pb in pads[i + 1:]:
                nb = ("pad", refb, pb.GetNumber())
                if nb not in ds:
                    continue
                a, b = position(pa), position(pb)
                length = math.dist(a, b)
                if length > pcb.FromMM(30) or not length:
                    continue
                score = min(ds[na] + length + dt[nb], ds[nb] + length + dt[na])
                if score < old - pcb.FromMM(2):
                    candidates.append((score, refa, pa.GetNumber(), refb, pb.GetNumber(), pa, pb))
        candidates.sort(key=lambda c: c[:5])
        begin = time.monotonic()
        tested, geometric, no_improvement, drc_count = 0, 0, 0, 0
        accepted = None
        for _, refa, numa, refb, numb, pa, pb in candidates[:MAX_BRIDGES]:
            if time.monotonic() - begin > LIMIT:
                break
            a, b = position(pa), position(pb)
            for coords in ((a, b), (a, (a[0], b[1]), b), (a, (b[0], a[1]), b)):
                coords = [p for i, p in enumerate(coords) if not i or p != coords[i - 1]]
                for layer in (pcb.F_Cu, pcb.B_Cu):
                    if not pa.IsOnLayer(layer) or not pb.IsOnLayer(layer):
                        continue
                    tested += 1
                    tracks = []
                    for x, y in zip(coords, coords[1:]):
                        track = pcb.PCB_TRACK(board)
                        track.SetStart(pcb.VECTOR2I(*x))
                        track.SetEnd(pcb.VECTOR2I(*y))
                        track.SetWidth(pcb.FromMM(0.3))
                        track.SetLayer(layer)
                        track.SetNetCode(start.GetNetCode())
                        shape = track.GetEffectiveShape(layer)
                        if any(shape.GetClearance(o) < c for o, c in obstacles[layer]):
                            geometric += 1
                            break
                        tracks.append(track)
                    else:
                        for t in tracks:
                            board.Add(t)
                        new_graph, _ = build(board, "GND")
                        actual = distances(new_graph, ("pad", cap, start.GetNumber())).get(("pad", ic, "7"), math.inf)
                        if actual > old - pcb.FromMM(0.5):
                            no_improvement += 1
                            for t in tracks:
                                board.Remove(t)
                            continue
                        pcb.SaveBoard(str(BOARD), board)
                        drc = subprocess.run(["kicad-cli", "pcb", "drc", "--format", "json",
                            "--severity-all", "--exit-code-violations", "--output", "/out/bridge-drc.json",
                            str(BOARD)], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
                        drc_count += 1
                        if drc.returncode == 0:
                            accepted = {"from": f"{refa}.{numa}", "to": f"{refb}.{numb}",
                                "layer": board.GetLayerName(layer),
                                "new_path_mm": round(pcb.ToMM(round(actual)), 3),
                                "points_mm": [[pcb.ToMM(x), pcb.ToMM(y)] for x, y in coords]}
                            break
                        for t in tracks:
                            board.Remove(t)
                        if drc.returncode != 5:
                            raise RuntimeError(f"DRC failed {drc.returncode}: {drc.stderr}")
                if accepted:
                    break
            if accepted:
                break
        pcb.SaveBoard(str(BOARD), board)
        record = {"capacitor": cap, "capacitor_pad": start.GetNumber(), "ic": ic,
                  "target_pad": "7", "old_path_mm": round(pcb.ToMM(round(old)), 3),
                  "possible_bridges": len(candidates), "attempted_paths": tested,
                  "geometry_rejections": geometric, "no_improvement": no_improvement,
                  "native_drc_tests": drc_count,
                  "elapsed_seconds": round(time.monotonic() - begin, 2), "accepted": accepted}
        records.append(record)
        print(json.dumps(record), flush=True)
    Path("/out/bridge-search.json").write_text(json.dumps({"max_seconds_per_pair": LIMIT,
        "max_bridges_per_pair": MAX_BRIDGES, "results": records}, indent=2) + "\n")


if __name__ == "__main__":
    main()
