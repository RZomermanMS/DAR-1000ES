#!/usr/bin/env python3
"""Measure shortest traced centerline paths through actual same-net copper.

Run with KiCad's pcbnew Python. This deliberately rejects zones and arcs:
it is not a field solver and does not model current division or inductance.
"""
import collections
import heapq
import json
import math
import sys

import pcbnew as pcb

PAIRS = {
    "C1": "U3", "C2": "U4", "C3": "U2", "C4": "U6", "C5": "U7",
    "C6": "U8", "C7": "U9", "C8": "U10", "C14": "U11",
    "C10": "U1-CONTROLLER1", "C11": "U1-CONTROLLER1",
    "C12": "U6-AUDIO1", "C13": "U6-AUDIO1",
}
SUPPLY_PINS = {
    "U2": ("14", "7"), "U3": ("14", "7"), "U4": ("14", "7"),
    "U6": ("14", "7"), "U7": ("14", "7"), "U8": ("14", "7"),
    "U9": ("14", "7"), "U10": ("2", "3"), "U11": ("2", "3"),
    "U1-CONTROLLER1": ("J1.21", "J1.22"),
    "U6-AUDIO1": ("J1.21", "J1.22"),
}
LAYERS = (pcb.F_Cu, pcb.B_Cu)


def point(v):
    return (v.x, v.y)


def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def projection(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    length2 = dx * dx + dy * dy
    t = max(0, min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / length2)) if length2 else 0
    return (round(a[0] + t * dx), round(a[1] + t * dy))


def crossing(a, b, c, d):
    x, y = b[0] - a[0], b[1] - a[1]
    u, v = d[0] - c[0], d[1] - c[1]
    den = x * v - y * u
    if not den:
        return None
    t = ((c[0] - a[0]) * v - (c[1] - a[1]) * u) / den
    s = ((c[0] - a[0]) * y - (c[1] - a[1]) * x) / den
    if 0 <= t <= 1 and 0 <= s <= 1:
        return (round(a[0] + t * x), round(a[1] + t * y))
    return None


def build(board, net):
    graph = collections.defaultdict(list)
    segments, vias, pads = [], [], []

    def edge(a, b, length, kind):
        graph[a].append((b, length, kind))
        graph[b].append((a, length, kind))

    for track in board.GetTracks():
        if track.GetNetname() != net:
            continue
        if isinstance(track, pcb.PCB_VIA):
            vias.append(track)
        elif type(track) == pcb.PCB_TRACK:
            segments.append((track.GetLayer(), point(track.GetStart()), point(track.GetEnd())))
        else:
            raise ValueError(f"unsupported track {type(track).__name__}")
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            if pad.GetNetname() == net:
                pads.append((fp.GetReference(), pad))
    # Split at same-layer centerline crossings, including T junctions.
    splits = [{a, b} for _, a, b in segments]
    for i, (layer, a, b) in enumerate(segments):
        for j in range(i):
            layer2, c, d = segments[j]
            if layer != layer2:
                continue
            q = crossing(a, b, c, d)
            if q is not None:
                splits[i].add(q)
                splits[j].add(q)
            for q in (a, b):
                if dist(projection(q, c, d), q) <= 1:
                    splits[j].add(q)
            for q in (c, d):
                if dist(projection(q, a, b), q) <= 1:
                    splits[i].add(q)
    # Pad hit testing is native KiCad copper geometry, at the centerline
    # closest to the pad center. Pad-center to contact distance is included.
    for ref, pad in pads:
        center = point(pad.GetPosition())
        pad_node = ("pad", ref, pad.GetNumber())
        for i, (layer, a, b) in enumerate(segments):
            if not pad.IsOnLayer(layer):
                continue
            q = projection(center, a, b)
            if pad.HitTest(pcb.VECTOR2I(*q)):
                splits[i].add(q)
                edge(pad_node, (layer, *q), dist(center, q), "pad")
    for via in vias:
        q = point(via.GetPosition())
        for i, (layer, a, b) in enumerate(segments):
            if via.IsOnLayer(layer) and dist(projection(q, a, b), q) <= 1:
                splits[i].add(q)
        edge((pcb.F_Cu, *q), (pcb.B_Cu, *q), 0, "via")
    for (layer, a, b), points in zip(segments, splits):
        ordered = sorted(points, key=lambda q: dist(a, q))
        for x, y in zip(ordered, ordered[1:]):
            edge((layer, *x), (layer, *y), dist(x, y), "track")
    return graph, pads


def shortest(graph, source, goals):
    queue = [(0, 0, source)]
    best = {source: 0}
    previous = {}
    serial = 0
    while queue:
        length, _, node = heapq.heappop(queue)
        if length != best[node]:
            continue
        if node in goals:
            path = []
            while node != source:
                before, kind = previous[node]
                path.append((node, kind))
                node = before
            path.reverse()
            return length, path
        for other, weight, kind in graph[node]:
            new = length + weight
            if new < best.get(other, math.inf):
                best[other] = new
                previous[other] = (node, kind)
                serial += 1
                heapq.heappush(queue, (new, serial, other))
    return None


def main(filename):
    board = pcb.LoadBoard(filename)
    if any(not zone.GetIsRuleArea() for zone in board.Zones()):
        raise ValueError("copper zones are not supported")
    fps = {fp.GetReference(): fp for fp in board.GetFootprints()}
    nets = {pad.GetNetname() for cap in PAIRS for pad in fps[cap].Pads()}
    graphs = {net: build(board, net) for net in nets}
    results = []
    for cap, target in PAIRS.items():
        for pad in fps[cap].Pads():
            net = pad.GetNetname()
            graph, _ = graphs[net]
            source = ("pad", cap, pad.GetNumber())
            number = SUPPLY_PINS[target][1 if net == "GND" else 0]
            targets = [p for p in fps[target].Pads()
                       if p.GetNumber() == number and p.GetNetname() == net]
            if len(targets) != 1:
                raise ValueError(f"{target}.{number} is not uniquely on {net}")
            goals = {("pad", target, number)}
            found = shortest(graph, source, goals)
            row = {"capacitor": cap, "capacitor_pad": pad.GetNumber(), "ic": target,
                   "net": net}
            if found:
                length, path = found
                row.update({"target_pad": path[-1][0][2], "path_mm": round(pcb.ToMM(round(length)), 3),
                            "vias": sum(kind == "via" for _, kind in path),
                            "intermediate_pads": [f"{n[1]}.{n[2]}" for n, _ in path[:-1]
                                                  if n[0] == "pad"],
                            "path": [{"pad": f"{n[1]}.{n[2]}", "edge_kind": kind}
                                     if n[0] == "pad" else
                                     {"layer": board.GetLayerName(n[0]),
                                      "xy_mm": [pcb.ToMM(n[1]), pcb.ToMM(n[2])],
                                      "edge_kind": kind} for n, kind in path]})
            else:
                row.update({"target_pad": None, "path_mm": None, "vias": None,
                            "intermediate_pads": []})
            results.append(row)
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main(sys.argv[1])
