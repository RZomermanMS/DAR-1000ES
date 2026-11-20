#!/usr/bin/env python3
"""Compare all named net partitions, including singleton and no-connect nodes."""
import sys
import xml.etree.ElementTree as ET
from collections import Counter


def read(path):
    root = ET.parse(path).getroot()
    nets = {}
    seen = set()
    for net in root.findall("./nets/net"):
        name = net.attrib["name"]
        nodes = [(node.attrib["ref"], node.attrib["pin"]) for node in net.findall("node")]
        if name in nets or len(nodes) != len(set(nodes)) or seen.intersection(nodes):
            raise ValueError(f"duplicate net or node in {path}: {name}")
        seen.update(nodes)
        nets[name] = frozenset(nodes)
    return nets


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: compare_connectivity.py BEFORE.xml AFTER.xml")
    before, after = map(read, sys.argv[1:])
    if before != after:
        for name in sorted(before.keys() | after.keys()):
            if before.get(name) != after.get(name):
                print(name, sorted(before.get(name, ())), "->", sorted(after.get(name, ())))
        raise SystemExit("FAIL: named net/node partitions differ")
    counts = Counter(len(nodes) for nodes in before.values())
    print(f"PASS: {len(before)} named nets, {sum(k * v for k, v in counts.items())} nodes, "
          f"{counts[1]} singleton nets identical (including no-connect singletons)")


if __name__ == "__main__":
    main()
