#!/usr/bin/env python3
"""Rebuild the v5 schematic from the checked-in v3 baseline, not the PCB."""
import copy
import json
import re
import shutil
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / "baseline-v3"
OLD, NEW = "DAR-1000ES-v3", "DAR-1000ES-v5"
NS = uuid.UUID("0bc871a3-dd7c-4a46-8aa2-6432e4691c15")


def parse(text):
    tokens = iter(re.findall(r'"(?:\\.|[^"\\])*"|[()]|[^\s()]+', text))

    def read(token):
        if token != "(":
            return token
        out = []
        for token in tokens:
            if token == ")":
                return out
            out.append(read(token))
        raise ValueError("unclosed expression")

    return read(next(tokens))


def emit(node, depth=0):
    if not isinstance(node, list):
        return node
    parts = [emit(item, depth + 1) for item in node]
    flat = "(" + " ".join(parts) + ")"
    if "\n" not in flat and len(flat) < 110:
        return flat
    return "(" + parts[0] + "\n" + "\n".join("\t" * (depth + 1) + p for p in parts[1:]) + "\n" + "\t" * depth + ")"


def q(text):
    return json.dumps(str(text), ensure_ascii=True)


def ch(node, key):
    return [n for n in node if isinstance(n, list) and n[0] == key]


def at(node):
    a = ch(node, "at")[0]
    return tuple(round(float(x), 2) for x in a[1:3])


def uid(name):
    return q(str(uuid.uuid5(NS, name)))


def ref(node):
    return next((json.loads(p[2]) for p in ch(node, "property") if p[1] == q("Reference")), None)


def label(kind, name, xy, angle, tag):
    return [kind, q(name), *([["shape", "bidirectional"]] if kind == "global_label" else []),
            ["at", *map(str, xy), str(angle)],
            ["effects", ["font", ["size", "0.8", "0.8"]], ["justify", "left" if angle == 0 else "right"]],
            ["uuid", uid(tag)]]


def wire_component(root, start):
    wires = ch(root, "wire")
    points = {}
    for w in wires:
        pts = [tuple(round(float(n), 2) for n in p[1:3]) for p in ch(ch(w, "pts")[0], "xy")]
        for p in pts:
            points.setdefault(p, []).append((w, pts))
    pending, visited, found = [start], {start}, []
    while pending:
        for w, pts in points.get(pending.pop(), []):
            if w not in found:
                found.append(w)
            for p in pts:
                if p not in visited:
                    visited.add(p)
                    pending.append(p)
    return found, visited


def move(node, dx, dy):
    if not isinstance(node, list):
        return
    if node and node[0] == "at":
        node[1] = str(round(float(node[1]) + dx, 2))
        node[2] = str(round(float(node[2]) + dy, 2))
    for item in node:
        move(item, dx, dy)


def clone_with_new_ids(node, tag):
    node = copy.deepcopy(node)

    def replace(item):
        if not isinstance(item, list):
            return
        if item and item[0] == "uuid":
            item[1] = uid(tag + json.loads(item[1]))
        for sub in item:
            replace(sub)

    replace(node)
    return node


def change_ref(node, old, new):
    for p in ch(node, "property"):
        if p[1] == q("Reference"):
            assert p[2] == q(old)
            p[2] = q(new)
    for project in ch(ch(node, "instances")[0], "project"):
        for path in ch(project, "path"):
            for entry in ch(path, "reference"):
                assert entry[1] == q(old)
                entry[1] = q(new)


def find_label(root, name, xy):
    found = [n for n in ch(root, "global_label") if n[1] == q(name) and at(n) == xy]
    assert len(found) == 1, (name, xy)
    return found[0]


def add_unused_marker(root, group, xy):
    # Refuse to hide a connection if the inherited schematic changes.
    for kind in ("no_connect", "label", "global_label", "hierarchical_label", "junction"):
        assert not any(at(n) == xy for n in ch(root, kind)), (group, xy, kind)
    for wire in ch(root, "wire"):
        ends = [tuple(round(float(v), 2) for v in p[1:3])
                for p in ch(ch(wire, "pts")[0], "xy")]
        (x1, y1), (x2, y2) = ends
        x, y = xy
        assert not (min(x1, x2) <= x <= max(x1, x2) and
                    min(y1, y2) <= y <= max(y1, y2) and
                    abs((x - x1) * (y2 - y1) - (y - y1) * (x2 - x1)) < 1e-6), (group, xy)
    root.append(["no_connect", ["at", *map(str, xy)],
                 ["uuid", uid(f"unused-{group}-{xy}")]])


def main_sheet(root):
    # Keep the existing U4-to-J4 nets and attach the three labels to J4 pins.
    for name in ("FLSTB", "FLSDATA", "FLSCLK"):
        found = [n for n in ch(root, "label") if n[1] == q(name)]
        assert len(found) == 1 and at(found[0])[0] == 74.93
        ch(found[0], "at")[0][1] = "76.2"

    # U2's four input nets each consisted solely of a controller GPIO and
    # a buffer input. Replace them with named audio-GPIO-to-buffer nets.
    for name, old_pin, buffer_pin, audio_pin in [
        ("AUDIO_U2_AMUTE", (215.9, 175.26), (257.81, 168.91), (158.75, 95.25)),
        ("AUDIO_U2_DMUTE", (215.9, 177.8), (293.37, 168.91), (158.75, 97.79)),
        ("AUDIO_U2_RELAY", (215.9, 180.34), (257.81, 189.23), (158.75, 100.33)),
        ("AUDIO_U2_SPARE", (215.9, 182.88), (293.37, 189.23), (158.75, 102.87)),
    ]:
        wires, points = wire_component(root, buffer_pin)
        assert old_pin in points and len(wires) >= 2
        for w in wires:
            root.remove(w)
        root.append(label("label", name, buffer_pin, 180, name + "-buffer"))
        root.append(label("label", name, audio_pin, 180, name + "-esp"))

    # Move the active-high request to AUDIO GPIO8.
    root.remove(find_label(root, "ENABLE_U2", (215.9, 172.72)))
    root.append(label("global_label", "ENABLE_U2", (214.63, 72.39), 0, "audio-enable"))

    # Both dev boards' second GND pin was tied together but not to GND.
    # Attach the existing common node to the actual ground net.
    root.append(label("global_label", "GND", (215.9, 165.1), 0, "second-ground"))

    # These are unused by the motherboard, not necessarily by the dev board.
    # Leave EN, 3V3 and GND pins visible for review.
    unused = {
        "buffer": [(82.55, 210.82), (83.82, 57.15),
                   (116.84, 190.5), (308.61, 189.23)],
        "audio-j1": [(158.75, y) for y in (72.39, 74.93, 77.47, 80.01, 85.09, 87.63, 92.71)],
        "audio-j3": [(214.63, y) for y in (74.93, 77.47, 87.63, 90.17, 92.71,
                                            95.25, 97.79, 100.33, 102.87)],
        "controller-j1": [(160.02, y) for y in (198.12, 200.66, 213.36)],
        "controller-j3": [(215.9, y) for y in (172.72, 175.26, 177.8, 180.34, 182.88,
                                                185.42, 187.96, 198.12, 200.66, 203.2,
                                                205.74, 208.28, 210.82, 213.36)],
    }
    for group, positions in unused.items():
        for xy in positions:
            add_unused_marker(root, group, xy)


def interlock(root):
    # U8 gate 1 becomes unused; U9 gate 3 controls the audio-owned U2.
    find_label(root, "ENABLE_U2", (78.74, 76.2))[1] = q("GND")
    find_label(root, "SONY_POWER_GOOD", (78.74, 78.74))[1] = q("GND")
    root.remove(find_label(root, "U2_OE_N", (119.38, 77.47)))
    root.append(["no_connect", ["at", "119.38", "77.47"], ["uuid", uid("u8-unused")]])
    find_label(root, "GND", (256.54, 91.44))[1] = q("ENABLE_U2")
    find_label(root, "GND", (256.54, 93.98))[1] = q("AUDIO_POWER_GOOD")
    old_nc = [n for n in ch(root, "no_connect") if at(n) == (297.18, 92.71)]
    assert len(old_nc) == 1
    root.remove(old_nc[0])
    root.append(label("global_label", "U2_OE_N", (297.18, 92.71), 0, "u9-u2-oe"))
    for xy in [(78.74, 86.36), (78.74, 93.98), (99.06, 181.61), (147.32, 199.39)]:
        find_label(root, "SONY_POWER_GOOD", xy)[1] = q("CTRL_POWER_GOOD")
    for xy in [(256.54, 78.74), (256.54, 86.36)]:
        find_label(root, "SONY_POWER_GOOD", xy)[1] = q("AUDIO_POWER_GOOD")
    # Separate sensor/output networks, with the same sense supply and GND.
    for old, new, dx in [("U10", "U11", 175.26), ("R12", "R14", 175.26),
                         ("R13", "R15", 175.26), ("C8", "C14", 251.46)]:
        original = next(s for s in ch(root, "symbol") if ref(s) == old)
        duplicate = clone_with_new_ids(original, new)
        change_ref(duplicate, old, new)
        move(duplicate, dx, 0)
        root.append(duplicate)
    for name, xy, dx, newname in [
        ("SONY_RESET_N_RAW", (60.96, 177.8), 175.26, "AUDIO_RESET_N_RAW"),
        ("SONY_5V_SENSE", (50.8, 165.1), 175.26, "SONY_5V_SENSE"),
        ("GND", (50.8, 190.5), 175.26, "GND"),
        ("SONY_RESET_N_RAW", (99.06, 173.99), 175.26, "AUDIO_RESET_N_RAW"),
        ("CTRL_POWER_GOOD", (99.06, 181.61), 175.26, "AUDIO_POWER_GOOD"),
        ("CTRL_POWER_GOOD", (147.32, 199.39), 175.26, "AUDIO_POWER_GOOD"),
        ("GND", (147.32, 207.01), 175.26, "GND"),
        ("SONY_5V_SENSE", (99.06, 224.79), 251.46, "SONY_5V_SENSE"),
        ("GND", (99.06, 232.41), 251.46, "GND"),
    ]:
        original = find_label(root, name, xy)
        duplicate = clone_with_new_ids(original, "duplicate-" + newname + str(xy))
        duplicate[1] = q(newname)
        move(duplicate, dx, 0)
        root.append(duplicate)


def main():
    footprints = set()
    for suffix in ("", "-interlock", "-power"):
        root = parse((BASE / (OLD + suffix + ".kicad_sch")).read_text())
        if suffix == "":
            main_sheet(root)
        elif suffix == "-interlock":
            interlock(root)
        for symbol in ch(root, "symbol"):
            for prop in ch(symbol, "property"):
                if prop[1] == q("Footprint"):
                    value = json.loads(prop[2])
                    if value.startswith("DAR1000ES:"):
                        footprints.add(value.split(":", 1)[1] + ".kicad_mod")
        text = (emit(root).replace(OLD, NEW)
                .replace("DAR-1000ES v3 - bottom routing and ESP power capacitors",
                         "DAR-1000ES v5 - schematic under electrical review")
                .replace("V3 bottom-routing revision - electrical and hardware review required",
                         "Schematic only - not approved for fabrication")
                .replace("V3: bottom copper routing; insulated top wire links as marked; ESP power capacitors added.",
                         "V5 schematic only: electrical and physical verification required.")
                .replace("DAR-1000ES v3 - local 5 V and ESP decoupling",
                         "DAR-1000ES v5 - local 5 V and ESP decoupling")) + "\n"
        (HERE / (NEW + suffix + ".kicad_sch")).write_text(text)
    for name in ("DAR1000ES.kicad_sym", "fp-lib-table", "Adafruit-TCA8418-README.txt",
                 "Adafruit-TCA8418-LICENSE.txt"):
        shutil.copyfile(BASE / name, HERE / name)
    sym_table = parse((BASE / "sym-lib-table").read_text())
    for name in ("Device", "Connector_Generic", "Jumper", "power"):
        sym_table.append(["lib", ["name", q(name)], ["type", q("KiCad")],
                          ["uri", q("${KICAD10_SYMBOL_DIR}/" + name + ".kicad_sym")],
                          ["options", q("")], ["descr", q("")]])
    (HERE / "sym-lib-table").write_text(emit(sym_table) + "\n")
    (HERE / (NEW + ".kicad_pro")).write_text(
        (BASE / (OLD + ".kicad_pro")).read_text().replace(OLD, NEW))
    (HERE / "DAR1000ES.pretty").mkdir(exist_ok=True)
    for footprint in sorted(footprints):
        shutil.copyfile(BASE / "DAR1000ES.pretty" / footprint, HERE / "DAR1000ES.pretty" / footprint)


if __name__ == "__main__":
    main()
