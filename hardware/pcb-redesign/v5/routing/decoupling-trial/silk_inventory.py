#!/usr/bin/env python3
"""Inventory silkscreen text; not a visual or assembly-readability check."""
import json
import sys

import pcbnew as pcb

b = pcb.LoadBoard(sys.argv[1])
layers = (pcb.F_SilkS, pcb.B_SilkS)
footprints = []
for f in sorted(b.GetFootprints(), key=lambda x: x.GetReference()):
    texts = []
    for item in list(f.GraphicalItems()) + list(f.GetFields()):
        if (hasattr(item, "GetText") and item.GetLayer() in layers and
                (not hasattr(item, "IsVisible") or item.IsVisible())):
            texts.append(item.GetText())
    ref = f.Reference()
    footprints.append({"ref": f.GetReference(),
                       "reference_visible_on_silk": ref.IsVisible() and ref.GetLayer() in layers,
                       "other_visible_silk_text": sorted(set(texts) - {f.GetReference()})})
drawings = [{"text": x.GetText(), "layer": b.GetLayerName(x.GetLayer())}
            for x in b.GetDrawings() if hasattr(x, "GetText") and x.GetLayer() in layers]
print(json.dumps({"footprints": footprints, "board_silk_text": drawings}, indent=2))
