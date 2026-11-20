#!/usr/bin/env python3
"""Apply clearance trial C's two U11 supply junction shifts to this candidate."""
import subprocess
import sys
from pathlib import Path

import pcbnew as pcb

MOVES = [
    ((51.8983, 258.8983), (51.8983, 258.748299),
     ("4304d9ab-dc66-46c8-89c6-7cae4011158f", "1d136c58-c19d-4810-aed8-150d7f338747")),
    ((47.27, 258.8983), (47.27, 258.748299),
     ("4304d9ab-dc66-46c8-89c6-7cae4011158f", "5838e9e0-28ff-4d5e-8ca3-a7cda0aa2cc4")),
]


def point(pair):
    return pcb.VECTOR2I(*(round(x * 1000000) for x in pair))


def main(board_path, report):
    path = Path(board_path)
    original = path.read_bytes()
    board = pcb.LoadBoard(board_path)
    tracks = list(board.GetTracks())
    by_id = {t.m_Uuid.AsString(): t for t in tracks}
    for old, new, ids in MOVES:
        old, new = point(old), point(new)
        attached = {t.m_Uuid.AsString() for t in tracks
                    if t.GetStart() == old or t.GetEnd() == old}
        if attached != set(ids):
            raise ValueError(f"unexpected junction tracks: {attached}")
        for uuid in ids:
            track = by_id[uuid]
            if track.GetNetname() != "SONY_5V_SENSE" or track.GetLayer() != pcb.B_Cu:
                raise ValueError("unexpected track")
            if track.GetStart() == old:
                track.SetStart(new)
            else:
                track.SetEnd(new)
    if not pcb.SaveBoard(board_path, board):
        raise OSError("KiCad failed to save candidate")
    try:
        Path(report).unlink(missing_ok=True)
        subprocess.run(["kicad-cli", "pcb", "drc", "--format", "json", "--severity-all",
                        "--exit-code-violations", "--output", report, board_path], check=True)
    except Exception:
        path.write_bytes(original)
        raise


if __name__ == "__main__":
    main(*sys.argv[1:])
