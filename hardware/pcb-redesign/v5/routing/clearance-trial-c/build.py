#!/usr/bin/env python3
"""Move selected existing track junctions on the exact placement-trial B board."""
import hashlib
import sys

import pcbnew as pcb

SOURCE_SHA256 = "2a6f2adb1d2c4078de47b7a6d337af844bace43cf1a1155d9afe8d2e7d51e7e8"

# A junction move changes all listed track endpoints, but not any remote ends.
MOVES = [
    ((86.6583, 54.9023), (86.4583, 54.9023),
     ("4e96da88-b1c1-4874-9a37-b97d896ee0bb", "c07899fe-b797-49ef-b61d-0011dd9ace6b")),
    ((51.8983, 258.8983), (51.8983, 258.7483),
     ("4304d9ab-dc66-46c8-89c6-7cae4011158f", "1d136c58-c19d-4810-aed8-150d7f338747")),
    ((47.27, 258.8983), (47.27, 258.7483),
     ("4304d9ab-dc66-46c8-89c6-7cae4011158f", "5838e9e0-28ff-4d5e-8ca3-a7cda0aa2cc4")),
]


def point(pair):
    return pcb.VECTOR2I(*(pcb.FromMM(value) for value in pair))


def main(source, output):
    with open(source, "rb") as f:
        if hashlib.sha256(f.read()).hexdigest() != SOURCE_SHA256:
            raise ValueError("unexpected source board")
    board = pcb.LoadBoard(source)
    tracks = list(board.GetTracks())
    by_id = {track.m_Uuid.AsString(): track for track in tracks}
    for old, new, ids in MOVES:
        old, new = point(old), point(new)
        attached = {t.m_Uuid.AsString() for t in tracks
                    if t.GetStart() == old or t.GetEnd() == old}
        if attached != set(ids):
            raise ValueError(f"unexpected junction tracks: {attached}")
        for uuid in ids:
            track = by_id[uuid]
            if isinstance(track, (pcb.PCB_VIA, pcb.PCB_ARC)):
                raise ValueError("expected straight track")
            if track.GetStart() == old:
                track.SetStart(new)
            else:
                track.SetEnd(new)
    pcb.SaveBoard(output, board)


if __name__ == "__main__":
    main(*sys.argv[1:])
