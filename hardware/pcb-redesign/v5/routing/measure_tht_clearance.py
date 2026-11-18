#!/usr/bin/env python3
"""Measure KiCad native copper-shape clearance to plated through-hole pads."""
import argparse
import hashlib
import json
import math
from pathlib import Path

import pcbnew as pcb


LAYERS = ((pcb.F_Cu, "F.Cu"), (pcb.B_Cu, "B.Cu"))


def mm(value):
    return round(pcb.ToMM(value), 6)


def xy(point):
    return [mm(point.x), mm(point.y)]


def related(a, b):
    # Net code zero means unconnected, not one shared electrical net.
    return a.GetNetCode() > 0 and a.GetNetCode() == b.GetNetCode()


def order(record):
    return (record["clearance_mm"], record["pad"]["ref"], record["pad"]["number"],
            record["item"]["uuid"], record["layer"])


def measure(board, threshold_mm):
    if board.GetCopperLayerCount() != 2:
        raise ValueError("This measurement supports two copper layers only")
    if not math.isfinite(threshold_mm) or threshold_mm < 0:
        raise ValueError("Threshold must be finite and nonnegative")
    threshold = pcb.FromMM(threshold_mm)
    tracks = list(board.GetTracks())
    pads = [(f.GetReference(), pad) for f in board.GetFootprints()
            for pad in f.Pads() if pad.GetAttribute() == pcb.PAD_ATTRIB_PTH]
    candidates = []
    pair_count = 0
    minimum = None
    minimum_distance = None
    for ref, pad in pads:
        for layer, layer_name in LAYERS:
            if not pad.IsOnLayer(layer) or not pad.FlashLayer(layer):
                continue
            pad_shape = pad.GetEffectiveShape(layer)
            if pad_shape.IsNull():
                continue
            for track in tracks:
                if not track.IsOnLayer(layer) or related(pad, track):
                    continue
                via = isinstance(track, pcb.PCB_VIA)
                if via and not track.FlashLayer(layer):
                    continue
                shape = track.GetEffectiveShape(layer)
                if shape.IsNull():
                    raise ValueError("Null track/via copper shape")
                pair_count += 1
                distance = pad_shape.GetClearance(shape)
                if distance <= threshold or minimum_distance is None or distance <= minimum_distance:
                    record = {
                        "clearance_mm": mm(distance),
                        "layer": layer_name,
                        "pad": {"ref": ref, "number": pad.GetNumber(),
                                "net": pad.GetNetname(), "position_mm": xy(pad.GetPosition()),
                                "uuid": pad.m_Uuid.AsString()},
                        "item": {"type": "via" if via else
                                 "arc" if isinstance(track, pcb.PCB_ARC) else "track",
                                 "net": track.GetNetname(),
                                 "width_mm": mm(track.GetWidth(layer) if via else track.GetWidth()),
                                 "start_mm": xy(track.GetStart()), "end_mm": xy(track.GetEnd()),
                                 "uuid": track.m_Uuid.AsString()},
                    }
                    if (minimum_distance is None or distance < minimum_distance or
                            (distance == minimum_distance and order(record) < order(minimum))):
                        minimum, minimum_distance = record, distance
                    if distance <= threshold:
                        candidates.append(record)
    candidates.sort(key=order)
    return {"tht_pad_count": len(pads), "track_via_count": len(tracks),
            "unrelated_layer_pairs_examined": pair_count,
            "minimum": minimum, "threshold_mm": threshold_mm, "within_threshold": candidates}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("board", type=Path)
    parser.add_argument("--threshold-mm", type=float, default=0.5,
                        help="include all pairs at or below this distance (default 0.5 mm)")
    args = parser.parse_args()
    if not 0 <= args.threshold_mm < float("inf"):
        parser.error("threshold must be finite and nonnegative")
    board = pcb.LoadBoard(str(args.board))
    result = measure(board, args.threshold_mm)
    result["board_sha256"] = hashlib.sha256(args.board.read_bytes()).hexdigest()
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
