#!/usr/bin/env python3
"""Focused mutation tests for safety-critical exported component metadata."""
import copy
import unittest
import xml.etree.ElementTree as ET

from verify_netlist import HERE, verify_safety_parts


REFS = ("R1", "R2", "R3", "R5", "R6", "R7", "R8", "R9", "R10", "R11",
        "R12", "R13", "R14", "R15", "U8", "U9", "U2", "U3", "U4", "U6",
        "U7", "U10", "U11", "C8", "C14", "C9", "C10", "C11", "C12", "C13")
MPN_REFS = ("U2", "U3", "U4", "U6", "U7", "C9", "C10", "C12")


class SafetyPartTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = ET.parse(HERE / "DAR-1000ES-v5.net.xml").getroot()

    def component(self, root, ref):
        result = root.find(f"./components/comp[@ref='{ref}']")
        self.assertIsNotNone(result)
        return result

    def test_unmodified_netlist_passes(self):
        verify_safety_parts(self.original)

    def test_wrong_value_for_each_required_part_is_rejected(self):
        for ref in REFS:
            with self.subTest(ref=ref):
                root = copy.deepcopy(self.original)
                self.component(root, ref).find("value").text = "0"
                with self.assertRaisesRegex(ValueError, rf"^{ref}:"):
                    verify_safety_parts(root)

    def test_wrong_symbol_for_each_required_part_is_rejected(self):
        for ref in REFS:
            with self.subTest(ref=ref):
                root = copy.deepcopy(self.original)
                self.component(root, ref).find("libsource").set("part", "incorrect")
                with self.assertRaisesRegex(ValueError, rf"^{ref}:"):
                    verify_safety_parts(root)

    def test_wrong_or_missing_mpn_is_rejected(self):
        for ref in MPN_REFS:
            for kind in ("field", "property"):
                for mode in ("wrong", "missing", "duplicate"):
                    with self.subTest(ref=ref, kind=kind, mode=mode):
                        root = copy.deepcopy(self.original)
                        component = self.component(root, ref)
                        parent = component.find("fields") if kind == "field" else component
                        item = parent.find(f"{kind}[@name='MPN']")
                        self.assertIsNotNone(item)
                        if mode == "wrong":
                            if kind == "field":
                                item.text = "incorrect"
                            else:
                                item.set("value", "incorrect")
                        elif mode == "missing":
                            parent.remove(item)
                        else:
                            parent.append(copy.deepcopy(item))
                        with self.assertRaisesRegex(ValueError, rf"^{ref}:"):
                            verify_safety_parts(root)

    def test_missing_and_duplicate_components_are_rejected(self):
        for ref in REFS:
            for mode in ("missing", "duplicate"):
                with self.subTest(ref=ref, mode=mode):
                    root = copy.deepcopy(self.original)
                    components = root.find("components")
                    component = self.component(root, ref)
                    if mode == "missing":
                        components.remove(component)
                    else:
                        components.append(copy.deepcopy(component))
                    with self.assertRaises(ValueError):
                        verify_safety_parts(root)


if __name__ == "__main__":
    unittest.main(verbosity=2)
