#!/usr/bin/env python3
"""Compare KiCad native-shape measurements for identical pad/item UUIDs."""
import json
import sys
from collections import Counter


def key(record):
    return (record["pad"]["uuid"], record["item"]["uuid"], record["layer"])


def main(before_path, after_path):
    before, after = [json.load(open(path)) for path in (before_path, after_path)]
    if before["threshold_mm"] != after["threshold_mm"]:
        raise ValueError("thresholds must match")
    threshold = before["threshold_mm"]
    b = {key(r): r for r in before["within_threshold"]}
    a = {key(r): r for r in after["within_threshold"]}
    if len(b) != len(before["within_threshold"]) or len(a) != len(after["within_threshold"]):
        raise ValueError("duplicate measurement keys")
    common = b.keys() & a.keys()
    changed = [(b[k], a[k]) for k in common
               if abs(b[k]["clearance_mm"] - a[k]["clearance_mm"]) > 0.000002]
    worsened_under_03 = [(x, y) for x, y in changed
                         if y["clearance_mm"] < .3
                         and y["clearance_mm"] < x["clearance_mm"] - 0.000002]
    entered_under_03 = [a[k] for k in a.keys() - b.keys() if a[k]["clearance_mm"] < .3]
    counts = lambda d, limit: sum(r["clearance_mm"] < limit for r in d.values())
    improved = [(x, y) for x, y in changed if y["clearance_mm"] > x["clearance_mm"]]
    refs = Counter(x["pad"]["ref"] for x, _ in improved)
    summary = {
        "threshold_mm": threshold,
        "before_hash": before["board_sha256"], "after_hash": after["board_sha256"],
        "pairs_examined": [before["unrelated_layer_pairs_examined"], after["unrelated_layer_pairs_examined"]],
        "minimum_mm": [before["minimum"]["clearance_mm"], after["minimum"]["clearance_mm"]],
        "pairs_below_0_3_mm": [counts(b, .3), counts(a, .3)],
        "pairs_below_0_25_mm": [counts(b, .25), counts(a, .25)],
        "within_threshold": [len(b), len(a)],
        "common_improved": len(improved),
        "common_worsened": len(changed) - len(improved),
        "entered_threshold": len(a.keys() - b.keys()),
        "left_threshold": len(b.keys() - a.keys()),
        "worsened_under_0_3": len(worsened_under_03),
        "entered_under_0_3": len(entered_under_03),
        "improved_pad_refs": dict(sorted(refs.items())),
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main(*sys.argv[1:])
