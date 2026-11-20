#!/usr/bin/env python3
"""Audit the integrated board against both independently saved inputs."""
import collections
import hashlib
import importlib.util
import json
from pathlib import Path

import pcbnew as pcb

HERE = Path(__file__).resolve().parent
ROUTING = HERE.parent
POWER = ROUTING / "power-rework" / "result.kicad_pcb"
SILK = ROUTING / "silk-rework" / "result.kicad_pcb"
BASE = ROUTING / "decoupling-trial" / "result.kicad_pcb"
RESULT = HERE / "result.kicad_pcb"


def signature(item):
    if isinstance(item, pcb.PCB_TEXT):
        return ("text", item.GetText(), item.GetLayer(), item.GetPosition().x,
                item.GetPosition().y, item.GetTextAngle().AsDegrees(),
                item.GetTextWidth(), item.GetTextHeight(), item.GetTextThickness())
    if isinstance(item, pcb.PCB_SHAPE):
        return ("shape", item.GetShape(), item.GetLayer(), item.GetStart().x,
                item.GetStart().y, item.GetEnd().x, item.GetEnd().y, item.GetWidth())
    raise ValueError(f"Unexpected overlay item: {type(item)}")


def additions(board, baseline):
    ids = {x.m_Uuid.AsString() for x in baseline.GetDrawings()}
    return [x for x in board.GetDrawings() if x.m_Uuid.AsString() not in ids]


def main():
    power, silk, base, result = [pcb.LoadBoard(str(p)) for p in (POWER, SILK, BASE, RESULT)]
    expected, actual = additions(silk, base), additions(result, power)
    if len(expected) != 61 or len(actual) != 61:
        raise ValueError("Expected exactly 60 texts and one line")
    if collections.Counter(map(signature, expected)) != collections.Counter(map(signature, actual)):
        raise ValueError("Integrated overlay does not match the saved silk candidate")
    if any(x.GetLayer() != pcb.F_SilkS for x in actual):
        raise ValueError("Unexpected non-silkscreen overlay")
    for item in actual:
        result.Remove(item)
    # Refill can change cached polygon serialization; compare every other
    # normalized board object after removing the fill caches from both copies.
    for board in (power, result):
        for zone in board.Zones():
            if not zone.GetIsRuleArea():
                zone.UnFill()
    scratch = [HERE / "audit-power.kicad_pcb", HERE / "audit-stripped.kicad_pcb"]
    sidecars = [p.with_suffix(ext) for p in scratch for ext in (".kicad_pro", ".kicad_prl")]
    if any(p.exists() for p in scratch + sidecars):
        raise ValueError("Audit scratch files already exist")
    try:
        for path, board in zip(scratch, (power, result)):
            pcb.SaveBoard(str(path), board)
        if scratch[0].read_bytes() != scratch[1].read_bytes():
            raise ValueError("Non-overlay board data differs from power input")
    finally:
        for path in scratch + sidecars:
            path.unlink(missing_ok=True)

    spec = importlib.util.spec_from_file_location("power_audit", ROUTING / "power-rework" / "audit.py")
    audit = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(audit)
    audit.BOARD = RESULT
    audit.HERE = HERE
    audit.main()
    output = {"board_sha256": hashlib.sha256(RESULT.read_bytes()).hexdigest(),
              "power_sha256": hashlib.sha256(POWER.read_bytes()).hexdigest(),
              "silk_sha256": hashlib.sha256(SILK.read_bytes()).hexdigest(),
              "overlay_items": len(actual), "overlay_matches_saved_silk_geometry": True,
              "non_overlay_matches_power_ignoring_fill_caches": True}
    (HERE / "integration-audit.json").write_text(json.dumps(output, indent=2) + "\n")
    print("Overlay matches saved silk; remaining normalized board matches power.")


if __name__ == "__main__":
    main()
