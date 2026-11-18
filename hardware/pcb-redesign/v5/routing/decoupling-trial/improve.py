#!/usr/bin/env python3
"""Try bounded DRC-checked direct connections on a copy of trial B."""
import json
import math
import subprocess
import sys
from pathlib import Path

import pcbnew as pcb
from measure_paths import PAIRS, SUPPLY_PINS, build, dist, point, shortest


def main(board_path, report_path):
    board_path, report_path = Path(board_path), Path(report_path)
    board = pcb.LoadBoard(str(board_path))
    if any(not z.GetIsRuleArea() for z in board.Zones()):
        raise ValueError("unexpected copper zone")
    changes = []
    for cap, target in PAIRS.items():
        if cap not in ("C7", "C14"):
            continue
        fps = {f.GetReference(): f for f in board.GetFootprints()}
        for pad in fps[cap].Pads():
            net = pad.GetNetname()
            pin = SUPPLY_PINS[target][1 if net == "GND" else 0]
            targets = [p for p in fps[target].Pads()
                       if p.GetNumber() == pin and p.GetNetname() == net]
            if len(targets) != 1:
                raise ValueError(f"{target}.{pin} is not uniquely on {net}")
            graph, _ = build(board, net)
            source = ("pad", cap, pad.GetNumber())
            goals = {("pad", target, p.GetNumber()) for p in targets}
            old = shortest(graph, source, goals)
            if old is None:
                raise ValueError(f"{source} was not connected")
            a = point(pad.GetPosition())
            candidates = sorted(targets, key=lambda p: dist(a, point(p.GetPosition())))
            accepted = False
            for dest in candidates:
                b = point(dest.GetPosition())
                if dist(a, b) + pcb.FromMM(0.5) >= old[0]:
                    continue
                bends = [None, (a[0], b[1]), (b[0], a[1])]
                if cap == "C7" and net == "GND":
                    for dx in (-6, -3, 3, 6):
                        for dy in (-6, -3, 3, 6):
                            bends.append((a[0] + pcb.FromMM(dx), a[1] + pcb.FromMM(dy)))
                for layer in (pcb.B_Cu, pcb.F_Cu):
                    if not pad.IsOnLayer(layer) or not dest.IsOnLayer(layer):
                        continue
                    for bend in bends:
                        coords = [a, b] if bend is None else [a, bend, b]
                        coords = [p for i, p in enumerate(coords) if not i or p != coords[i-1]]
                        if sum(dist(x, y) for x, y in zip(coords, coords[1:])) + pcb.FromMM(0.5) >= old[0]:
                            continue
                        added = []
                        for start, end in zip(coords, coords[1:]):
                            track = pcb.PCB_TRACK(board)
                            track.SetStart(pcb.VECTOR2I(*start))
                            track.SetEnd(pcb.VECTOR2I(*end))
                            track.SetLayer(layer)
                            track.SetWidth(pcb.FromMM(0.30))
                            track.SetNetCode(pad.GetNetCode())
                            board.Add(track)
                            added.append(track)
                        if not pcb.SaveBoard(str(board_path), board):
                            raise OSError("KiCad failed to save candidate")
                        report_path.unlink(missing_ok=True)
                        result = subprocess.run(
                            ["kicad-cli", "pcb", "drc", "--format", "json",
                             "--severity-all", "--exit-code-violations",
                             "--output", str(report_path), str(board_path)],
                            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
                        if result.returncode == 0:
                            changes.append({"capacitor": cap, "pad": pad.GetNumber(),
                                            "target": target, "target_pad": dest.GetNumber(),
                                            "net": net, "layer": board.GetLayerName(layer),
                                            "points_mm": [[pcb.ToMM(x), pcb.ToMM(y)] for x, y in coords],
                                            "previous_path_mm": round(pcb.ToMM(round(old[0])), 3)})
                            accepted = True
                            print("accepted", changes[-1], flush=True)
                            break
                        for track in added:
                            board.Remove(track)
                        if result.returncode not in (0, 5):
                            raise RuntimeError(f"DRC failed: {result.returncode} {result.stderr}")
                    if accepted:
                        break
                if accepted:
                    break
    if not pcb.SaveBoard(str(board_path), board):
        raise OSError("KiCad failed to save candidate")
    report_path.unlink(missing_ok=True)
    subprocess.run(["kicad-cli", "pcb", "drc", "--format", "json", "--severity-all",
                    "--exit-code-violations", "--output", str(report_path), str(board_path)],
                   check=True)
    print(json.dumps(changes, indent=2))


if __name__ == "__main__":
    main(*sys.argv[1:])
