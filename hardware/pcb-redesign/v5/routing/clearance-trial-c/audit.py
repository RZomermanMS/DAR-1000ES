#!/usr/bin/env python3
"""Verify exact scope of edits and apply the existing v5 domain audits."""
import hashlib
import re
import sys
from pathlib import Path

import pcbnew as pcb

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "placement-trial"))
import board_ops
from build import MOVES, SOURCE_SHA256, point


def blocks(text):
    return {match.group(1): match.group(0) for match in
            re.finditer(r'\t\(segment\n.*?\n\t\t\(uuid "([^"]+)"\)\n\t\)', text, re.S)}


def main(source, candidate, netlist):
    src_text = Path(source).read_text()
    dst_text = Path(candidate).read_text()
    assert hashlib.sha256(Path(source).read_bytes()).hexdigest() == SOURCE_SHA256
    before = pcb.LoadBoard(source)
    after = pcb.LoadBoard(candidate)
    old_tracks = {t.m_Uuid.AsString(): t for t in before.GetTracks()}
    new_tracks = {t.m_Uuid.AsString(): t for t in after.GetTracks()}
    assert old_tracks.keys() == new_tracks.keys()
    expected = {}
    for old, new, ids in MOVES:
        for uuid in ids:
            expected.setdefault(uuid, {})[(point(old).x, point(old).y)] = point(new)
    for uuid in old_tracks:
        old, new = old_tracks[uuid], new_tracks[uuid]
        for get in ("GetStart", "GetEnd"):
            p = getattr(old, get)()
            wanted = expected.get(uuid, {}).get((p.x, p.y), p)
            assert getattr(new, get)() == wanted, (uuid, get)
    original_blocks, new_blocks = blocks(src_text), blocks(dst_text)
    for uuid in expected:
        original, revised = original_blocks[uuid], new_blocks[uuid]
        strip_ends = lambda s: re.sub(r'\((start|end) [^)]+\)', r'(\1)', s)
        assert strip_ends(original) == strip_ends(revised), uuid
        src_text = src_text.replace(original, revised, 1)
    assert src_text == dst_text, "unexpected non-routing or other board change"
    board_ops.verify_netlist(after, netlist)
    board_ops.verify_uart(netlist)
    board_ops.audit_sections(after, 150, "lower")
    board_ops.audit_component_envelopes(after, 150, "lower")
    zones = list(after.Zones())
    assert len(zones) == 2 and all(
        z.GetIsRuleArea() and z.GetLayerSet().Contains(pcb.F_Cu)
        and z.GetLayerSet().Contains(pcb.B_Cu)
        and all((z.GetDoNotAllowTracks(), z.GetDoNotAllowVias(),
                 z.GetDoNotAllowPads(), z.GetDoNotAllowZoneFills(),
                 z.GetDoNotAllowFootprints())) for z in zones)
    segments = [t for t in after.GetTracks() if not isinstance(t, pcb.PCB_VIA)]
    vias = [t for t in after.GetTracks() if isinstance(t, pcb.PCB_VIA)]
    assert after.GetCopperLayerCount() == 2
    assert min(t.GetWidth() for t in segments) >= pcb.FromMM(0.25)
    print(f"Exact board diff: {len(expected)} existing segments, endpoints only; "
          "all other board text unchanged.")
    print(f"Netlist and UART endpoint checks passed; {len(segments)} segments, "
          f"{len(vias)} vias, minimum width {pcb.ToMM(min(t.GetWidth() for t in segments)):.3f} mm.")
    print("Both inherited two-layer antenna rule areas retained; outline and placement unchanged.")
    print("Candidate SHA-256:", hashlib.sha256(Path(candidate).read_bytes()).hexdigest())


if __name__ == "__main__":
    main(*sys.argv[1:])
