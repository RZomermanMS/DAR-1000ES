#!/usr/bin/env python3
"""Verify transformation scope and inherited electrical/domain checks."""
import hashlib
import importlib.util
import json
from collections import Counter
from pathlib import Path

import pcbnew as pcb
import transform

HERE = Path(__file__).resolve().parent
ROUTING = HERE.parent
SOURCE = ROUTING / "integrated-review/clearance-first-corrected/result.kicad_pcb"
RESULT = HERE / "result.kicad_pcb"


def main():
    spec = importlib.util.spec_from_file_location("power_audit", ROUTING / "power-rework/audit.py")
    audit = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(audit)
    before, after = pcb.LoadBoard(str(SOURCE)), pcb.LoadBoard(str(RESULT))
    originals = {f.GetReference(): f for f in before.GetFootprints()}
    relocated = {f.GetReference(): f for f in after.GetFootprints()}
    expected_tracks = []
    for ref, (_, _, position, angle, _, _) in transform.PLAN.items():
        f = relocated[ref]
        if f.GetPosition() != transform.xy(*position) or f.GetOrientationDegrees() != angle:
            raise ValueError(f"{ref} not at authorized placement")
        _, _, _, _, ic, layer = transform.PLAN[ref]
        supply = next(p for p in f.Pads() if p.GetNetname() == "LOCAL_5V")
        pin = next(p for p in relocated[ic].Pads() if p.GetNumber() == "14")
        expected_tracks.append((layer, supply.GetPosition().x, supply.GetPosition().y,
                                pin.GetPosition().x, pin.GetPosition().y))
        original = originals[ref]
        f.SetOrientationDegrees(original.GetOrientationDegrees())
        f.SetPosition(original.GetPosition())
    if audit.placements(before) != audit.placements(after):
        raise ValueError("unexpected footprint or pad geometry/net change")
    old_ids = {t.m_Uuid.AsString() for t in before.GetTracks()}
    additions = [t for t in after.GetTracks() if t.m_Uuid.AsString() not in old_ids]
    if len(additions) != 4:
        raise ValueError("expected three tracks and one via")
    tracks = [t for t in additions if type(t) == pcb.PCB_TRACK]
    vias = [t for t in additions if isinstance(t, pcb.PCB_VIA)]
    actual_tracks = [(t.GetLayer(), t.GetStart().x, t.GetStart().y,
                      t.GetEnd().x, t.GetEnd().y) for t in tracks]
    if (Counter(actual_tracks) != Counter(expected_tracks) or
            any(t.GetNetname() != "LOCAL_5V" or t.GetWidth() != pcb.FromMM(0.3) for t in tracks)):
        raise ValueError("added supply branches differ from plan")
    if (len(vias) != 1 or vias[0].GetPosition() != transform.xy(25, 222) or
            vias[0].GetNetname() != "LOCAL_5V" or
            vias[0].GetWidth(pcb.F_Cu) != pcb.FromMM(0.8) or
            vias[0].GetDrillValue() != pcb.FromMM(0.4)):
        raise ValueError("former C4 junction via differs from plan")
    for t in additions:
        after.Remove(t)
    # Normalize only authorized placements, new copper and fill caches; all
    # remaining KiCad board content (including marked silk) must match.
    for board in (before, after):
        for zone in board.Zones():
            if not zone.GetIsRuleArea():
                zone.UnFill()
    a, b = HERE / "audit-source.kicad_pcb", HERE / "audit-result.kicad_pcb"
    if a.exists() or b.exists():
        raise ValueError("audit scratch files already exist")
    try:
        pcb.SaveBoard(str(a), before)
        pcb.SaveBoard(str(b), after)
        if a.read_bytes() != b.read_bytes():
            raise ValueError("unexpected change outside authorized placement and copper")
    finally:
        for path in (a, b):
            path.unlink(missing_ok=True)
            path.with_suffix(".kicad_pro").unlink(missing_ok=True)
            path.with_suffix(".kicad_prl").unlink(missing_ok=True)
    # power audit performs real netlist, exact UART, boundary/envelope,
    # antenna-rule and filled-ground/thermal-sample checks on the saved board.
    # Placement invariants have been checked above against the actual source.
    audit.SOURCE = SOURCE
    audit.BOARD = RESULT
    audit.HERE = HERE
    audit.placements = lambda board: None
    audit.main()
    data = json.loads((HERE / "audit.json").read_text())
    data.pop("unchanged_footprint_positions_and_pad_nets")
    data["only_authorized_placements_changed"] = sorted(transform.PLAN)
    data["all_other_board_objects_match_except_fill_and_added_copper"] = True
    data["source_sha256"] = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    (HERE / "audit.json").write_text(json.dumps(data, indent=2) + "\n")


if __name__ == "__main__":
    main()
