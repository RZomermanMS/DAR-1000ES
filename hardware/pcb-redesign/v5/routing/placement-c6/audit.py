#!/usr/bin/env python3
"""Verify only the intended placement changes and run inherited domain audits."""
import hashlib
import importlib.util
import json
from pathlib import Path

import pcbnew as pcb

HERE = Path(__file__).resolve().parent
ROUTING = HERE.parent
SOURCE = ROUTING / "integrated-review/clearance-first-corrected/result.kicad_pcb"
RESULT = HERE / "result.kicad_pcb"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def point(v):
    return [pcb.ToMM(v.x), pcb.ToMM(v.y)]


def pads(board):
    return sorted((f.GetReference(), p.GetNumber(), p.GetNetname(),
                   p.GetShape(), p.GetAttribute(), point(p.GetSize()),
                   point(p.GetDrillSize()), p.GetOrientationDegrees())
                  for f in board.GetFootprints() for p in f.Pads())


def tracks(board):
    def signature(t):
        return (type(t).__name__, t.GetNetname(), t.GetLayer(),
                tuple(point(t.GetStart())), tuple(point(t.GetEnd())),
                pcb.ToMM(t.GetWidth(pcb.F_Cu) if isinstance(t, pcb.PCB_VIA) else t.GetWidth()),
                pcb.ToMM(t.GetDrillValue()) if isinstance(t, pcb.PCB_VIA) else None)
    return {t.m_Uuid.AsString(): signature(t) for t in board.GetTracks()}


def main():
    audit = load("power_audit", ROUTING / "power-rework/audit.py")
    original, actual = pcb.LoadBoard(str(SOURCE)), pcb.LoadBoard(str(RESULT))
    before = {f.GetReference(): f for f in original.GetFootprints()}
    after = {f.GetReference(): f for f in actual.GetFootprints()}
    if set(before) != set(after) or pads(original) != pads(actual):
        raise ValueError("Footprint set, pad nets, or pad geometry changed")
    old_tracks, new_tracks = tracks(original), tracks(actual)
    if any(old_tracks[k] != new_tracks[k] for k in old_tracks.keys() & new_tracks.keys()):
        raise ValueError("An existing track was modified")
    removed = sorted(old_tracks[k] for k in old_tracks.keys() - new_tracks.keys())
    added = sorted(new_tracks[k] for k in new_tracks.keys() - old_tracks.keys())
    if removed != sorted([
            ("PCB_TRACK", "GND", pcb.F_Cu, (50.0, 52.7), (50.0, 68.0), 0.8, None),
            ("PCB_TRACK", "GND", pcb.B_Cu, (50.0, 70.38), (50.0, 68.0), 0.8, None)]):
        raise ValueError(f"Unexpected removed tracks: {removed}")
    if added != sorted([
            ("PCB_TRACK", "LOCAL_5V", pcb.F_Cu, (52.62, 45.0), (55.5, 41.5), 0.3, None),
            ("PCB_VIA", "LOCAL_5V", pcb.F_Cu, (45.0, 68.0), (45.0, 68.0), 0.8, 0.4)]):
        raise ValueError(f"Unexpected added tracks: {added}")
    overlay = load("overlay", ROUTING / "integrated-review/audit_integration.py")
    from collections import Counter
    if Counter(map(overlay.signature, original.GetDrawings())) != Counter(map(overlay.signature, actual.GetDrawings())):
        raise ValueError("Board artwork changed")
    cap = before["C6"]
    old_pos = point(cap.GetPosition())
    old_pads = {p.GetNumber(): point(p.GetPosition()) for p in cap.Pads()}
    cap.SetPosition(pcb.VECTOR2I(pcb.FromMM(55.5), pcb.FromMM(41.5)))
    if audit.placements(original) != audit.placements(actual):
        raise ValueError("Unexpected footprint or pad position")
    new_pads = {p.GetNumber(): point(p.GetPosition()) for p in after["C6"].Pads()}
    if new_pads != {"1": [55.5, 41.5], "2": [60.5, 41.5]}:
        raise ValueError("Unexpected saved C6 pads")
    if not after["C6"].Reference().IsVisible() or after["C6"].Reference().GetLayer() != pcb.F_SilkS:
        raise ValueError("C6 reference is not visible on front silkscreen")
    audit.SOURCE, audit.BOARD, audit.HERE = SOURCE, RESULT, HERE
    real_placements = audit.placements
    audit.placements = lambda b: [p for p in real_placements(b) if p[0] != "C6"]
    audit.main()
    report_path = HERE / "audit.json"
    data = json.loads(report_path.read_text())
    data.pop("unchanged_footprint_positions_and_pad_nets")
    data.update({
        "only_c6_moved_pad_nets_and_geometry_unchanged": True,
        "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        "c6_position_before_mm": old_pos,
        "c6_position_after_mm": point(after["C6"].GetPosition()),
        "c6_pads_before_mm": old_pads,
        "c6_pads_after_mm": new_pads,
        "u8_pin14_mm": point(next(p for p in after["U8"].Pads() if p.GetNumber() == "14").GetPosition()),
        "c6_reference_visible_on_front_silk": True,
        "unchanged_existing_tracks": len(old_tracks) - len(removed),
        "removed_tracks": removed,
        "added_tracks": added,
        "board_artwork_unchanged": True,
    })
    report_path.write_text(json.dumps(data, indent=2) + "\n")


if __name__ == "__main__":
    main()
