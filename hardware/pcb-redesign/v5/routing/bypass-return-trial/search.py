#!/usr/bin/env python3
"""Bounded additive ground-return search; native KiCad DRC is the final oracle."""
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
REPORT = Path("/out/search-drc.json")
LIMIT_SECONDS = 210
PAIRS = (("C1", "U3"), ("C2", "U4"), ("C3", "U2"), ("C4", "U6"))
SCALE = pcb.FromMM(1)


def pos(p):
    p = p.GetPosition()
    return p.x, p.y


def mm(p):
    return [round(x / SCALE, 6) for x in p]


def main():
    board = pcb.LoadBoard(str(BOARD))
    fps = {f.GetReference(): f for f in board.GetFootprints()}
    pad = lambda ref, number: next(p for p in fps[ref].Pads() if p.GetNumber() == number)
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

    start_time = time.monotonic()
    records = []
    for cap, ic in PAIRS:
        a_pad = next(p for p in fps[cap].Pads() if p.GetNetname() == "GND")
        b_pad = pad(ic, "7")
        if b_pad.GetNetname() != "GND":
            raise ValueError(f"{ic}.7 is not GND")
        a, b = pos(a_pad), pos(b_pad)
        graph, _ = build(board, "GND")
        before = shortest(graph, ("pad", cap, a_pad.GetNumber()), {("pad", ic, "7")})
        if before is None:
            raise ValueError("baseline open")
        candidates = [(a, b), (a, (a[0], b[1]), b), (a, (b[0], a[1]), b)]
        for x in range(min(a[0], b[0]) // SCALE - 4, max(a[0], b[0]) // SCALE + 5, 2):
            for y in range(min(a[1], b[1]) // SCALE - 4, max(a[1], b[1]) // SCALE + 5, 2):
                candidates.append((a, (x * SCALE, y * SCALE), b))
        candidates.sort(key=lambda c: sum(math.dist(x, y) for x, y in zip(c, c[1:])))
        tested, geometric_rejects, drc_rejects = 0, 0, 0
        accepted = None
        for coords in candidates:
            if time.monotonic() - start_time > LIMIT_SECONDS:
                break
            coords = tuple(p for i, p in enumerate(coords) if not i or p != coords[i - 1])
            if sum(math.dist(x, y) for x, y in zip(coords, coords[1:])) >= before[0] - SCALE / 2:
                continue
            for layer in (pcb.F_Cu, pcb.B_Cu):
                new = []
                clear = True
                for x, y in zip(coords, coords[1:]):
                    t = pcb.PCB_TRACK(board)
                    t.SetStart(pcb.VECTOR2I(*x))
                    t.SetEnd(pcb.VECTOR2I(*y))
                    t.SetWidth(pcb.FromMM(0.30))
                    t.SetLayer(layer)
                    t.SetNetCode(a_pad.GetNetCode())
                    shape = t.GetEffectiveShape(layer)
                    if any(shape.GetClearance(other) < clearance for other, clearance in obstacles[layer]):
                        clear = False
                        break
                    new.append(t)
                if not clear:
                    geometric_rejects += 1
                    continue
                for t in new:
                    board.Add(t)
                pcb.SaveBoard(str(BOARD), board)
                tested += 1
                result = subprocess.run(
                    ["kicad-cli", "pcb", "drc", "--format", "json", "--severity-all",
                     "--exit-code-violations", "--output", str(REPORT), str(BOARD)],
                    stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
                if result.returncode == 0:
                    accepted = {"layer": board.GetLayerName(layer),
                                "points_mm": [mm(p) for p in coords]}
                    break
                if result.returncode != 5:
                    raise RuntimeError(f"DRC failed {result.returncode}: {result.stderr}")
                drc_rejects += 1
                for t in new:
                    board.Remove(t)
            if accepted:
                break
        pcb.SaveBoard(str(BOARD), board)
        record = {"capacitor": cap, "capacitor_pad": a_pad.GetNumber(), "ic": ic,
                  "target_pad": "7", "old_path_mm": round(before[0] / SCALE, 3),
                  "candidates": len(candidates), "geometric_rejections": geometric_rejects,
                  "native_drc_tests": tested, "native_drc_rejections": drc_rejects,
                  "accepted": accepted}
        records.append(record)
        print(json.dumps(record), flush=True)
    Path("/out/search.json").write_text(json.dumps({"limit_seconds": LIMIT_SECONDS,
        "elapsed_seconds": round(time.monotonic() - start_time, 2), "results": records}, indent=2) + "\n")


if __name__ == "__main__":
    main()
