#!/usr/bin/env python3
"""Explore small junction moves; each accepted step must pass native DRC."""
import json
import subprocess
from pathlib import Path

import pcbnew as pcb

ROOT = Path(__file__).resolve().parent
BOARD = ROOT / "result.kicad_pcb"
REPORT = ROOT / "search-drc.json"
LIMIT = pcb.FromMM(.3)
MARGIN = pcb.FromMM(2)


def pos(p):
    return (p.x, p.y)


def nearby(pad, track):
    a, b = track.GetStart(), track.GetEnd()
    box = pad.GetBoundingBox()
    return (min(a.x, b.x) - MARGIN <= box.GetRight()
            and max(a.x, b.x) + MARGIN >= box.GetLeft()
            and min(a.y, b.y) - MARGIN <= box.GetBottom()
            and max(a.y, b.y) + MARGIN >= box.GetTop())


def main():
    board = pcb.LoadBoard(str(BOARD))
    tracks = list(board.GetTracks())
    pads = [p for f in board.GetFootprints() for p in f.Pads()
            if p.GetAttribute() == pcb.PAD_ATTRIB_PTH]
    original = json.loads((ROOT.parent / "decoupling-trial/tht-clearance.json").read_text())
    priorities = {}
    for pair in original["within_threshold"]:
        if pair["clearance_mm"] < .3 and pair["item"]["type"] == "track":
            uuid = pair["item"]["uuid"]
            priorities[uuid] = priorities.get(uuid, 0) + 1
    by_id = {t.m_Uuid.AsString(): t for t in tracks}
    accepted = []

    def junction(point, layer, net):
        hits = [t for t in tracks if t.IsOnLayer(layer)
                and (pos(t.GetStart()) == point or pos(t.GetEnd()) == point)]
        if (not hits or any(isinstance(t, (pcb.PCB_VIA, pcb.PCB_ARC))
                            or t.GetLayer() != layer or t.GetNetCode() != net for t in hits)
                or any(p.IsOnLayer(layer) and p.HitTest(pcb.VECTOR2I(*point)) for p in pads)):
            return None
        return hits

    def apply(changes):
        for t, endpoint, p in changes:
            getattr(t, "Set" + endpoint)(pcb.VECTOR2I(*p))

    def distances(changed):
        result = {}
        for t in changed:
            layer = t.GetLayer()
            shape = t.GetEffectiveShape(layer)
            for p in pads:
                if (not p.IsOnLayer(layer) or not p.FlashLayer(layer)
                    or (p.GetNetCode() > 0 and p.GetNetCode() == t.GetNetCode())
                    or not nearby(p, t)):
                    continue
                result[(t.m_Uuid.AsString(), p.m_Uuid.AsString())] = p.GetEffectiveShape(layer).GetClearance(shape)
        return result

    for uuid in sorted(priorities, key=lambda x: (-priorities[x], x)):
        target = by_id[uuid]
        start, end = pos(target.GetStart()), pos(target.GetEnd())
        joints = [(p, junction(p, target.GetLayer(), target.GetNetCode())) for p in (start, end)]
        groups = [[x for x in joints if x[1]]] + [[x] for x in joints if x[1]]
        groups = [g for g in groups if g]
        best = []
        for group in groups:
            affected = list({t.m_Uuid.AsString(): t for _, ts in group for t in ts}.values())
            old_dist = distances(affected)
            for dx, dy in ((-.3, 0), (.3, 0), (0, -.3), (0, .3),
                           (-.2, 0), (.2, 0), (0, -.2), (0, .2),
                           (-.1, 0), (.1, 0), (0, -.1), (0, .1)):
                delta = (pcb.FromMM(dx), pcb.FromMM(dy))
                changes = []
                for p, ts in group:
                    for t in ts:
                        for endpoint in ("Start", "End"):
                            if pos(getattr(t, "Get" + endpoint)()) == p:
                                changes.append((t, endpoint, (p[0] + delta[0], p[1] + delta[1])))
                saved = [(t, ep, pos(getattr(t, "Get" + ep)())) for t, ep, _ in changes]
                apply(changes)
                new_dist = distances(affected)
                apply(saved)
                keys = old_dist.keys() | new_dist.keys()
                # Out-of-bounds pairs are safely beyond 0.3 mm.
                old = [old_dist.get(k, LIMIT) for k in keys]
                new = [new_dist.get(k, LIMIT) for k in keys]
                if any(min(n, LIMIT) + 2000 < min(o, LIMIT) for o, n in zip(old, new)):
                    continue
                gain = sum(max(0, LIMIT-o)-max(0, LIMIT-n) for o, n in zip(old, new))
                if gain > pcb.FromMM(.02):
                    best.append((gain, dx, dy, saved, changes))
        for gain, dx, dy, saved, changes in sorted(best, key=lambda x: -x[0]):
            apply(changes)
            pcb.SaveBoard(str(BOARD), board)
            r = subprocess.run(["kicad-cli", "pcb", "drc", "--format", "json",
                                "--severity-all", "--exit-code-violations",
                                "-o", str(REPORT), str(BOARD)],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if r.returncode == 0:
                entry = {"target": uuid, "gain_mm": round(pcb.ToMM(gain), 5),
                         "changes": [{"uuid": t.m_Uuid.AsString(), "endpoint": ep,
                                      "old": list(p), "new": list(next(q for tt, ee, q in changes if tt == t and ee == ep))}
                                     for t, ep, p in saved]}
                accepted.append(entry)
                print("accepted", uuid, gain / 1e6, dx, dy, flush=True)
                break
            if r.returncode != 5:
                raise RuntimeError(f"DRC command failed {r.returncode}")
            apply(saved)
    pcb.SaveBoard(str(BOARD), board)
    (ROOT / "moves.json").write_text(json.dumps(accepted, indent=2) + "\n")
    REPORT.unlink(missing_ok=True)
    print("accepted total", len(accepted), flush=True)


if __name__ == "__main__":
    main()
