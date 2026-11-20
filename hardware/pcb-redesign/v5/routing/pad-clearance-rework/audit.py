#!/usr/bin/env python3
"""Verify that only listed existing segment endpoints differ."""
import hashlib
import json
import re
import sys
from pathlib import Path


def blocks(text):
    return {m.group(1): m.group(0) for m in re.finditer(
        r'\t\(segment\n.*?\n\t\t\(uuid "([^"]+)"\)\n\t\)', text, re.S)}


def main(source, candidate):
    old_bytes, new_bytes = Path(source).read_bytes(), Path(candidate).read_bytes()
    old, new = old_bytes.decode(), new_bytes.decode()
    a, b = blocks(old), blocks(new)
    if a.keys() != b.keys():
        raise ValueError("segment IDs differ")
    moves = json.loads((Path(__file__).resolve().parent / "moves.json").read_text())
    allowed = {c["uuid"] for step in moves for c in step["changes"]}
    changed = {k for k in a if a[k] != b[k]}
    if changed != allowed:
        raise ValueError("changed segments do not match the move manifest")
    for k in changed:
        erase = lambda s: re.sub(r'\((start|end) [^)]+\)', r'(\1)', s)
        if erase(a[k]) != erase(b[k]):
            raise ValueError(f"non-endpoint segment data changed: {k}")
        old = old.replace(a[k], b[k], 1)
    if old != new:
        raise ValueError("non-segment board text changed")
    print(json.dumps({"source_sha256": hashlib.sha256(old_bytes).hexdigest(),
                      "candidate_sha256": hashlib.sha256(new_bytes).hexdigest(),
                      "steps": len(moves), "changed_segments": len(changed),
                      "other_board_text_unchanged": True}, indent=2))


if __name__ == "__main__":
    main(*sys.argv[1:])
