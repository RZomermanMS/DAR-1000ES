#!/usr/bin/env python3
"""Fail if reported sub-0.30 mm pad clearance worsens or does not improve."""
import json
import sys

report = json.load(open(sys.argv[1]))
if (report["minimum_mm"][1] + 0.000002 < report["minimum_mm"][0] or
        report["pairs_below_0_3_mm"][1] >= report["pairs_below_0_3_mm"][0] or
        report["pairs_below_0_25_mm"][1] > report["pairs_below_0_25_mm"][0] or
        report["common_worsened"] or report["entered_threshold"] or
        report["worsened_under_0_3"] or report["entered_under_0_3"]):
    raise ValueError(f"Clearance objective or no-regression guard failed: {report}")
