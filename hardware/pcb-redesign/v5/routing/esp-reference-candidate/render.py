#!/usr/bin/env python3
"""Render fitted KiCad inspection PDFs and labeled ESP-region closeups."""
import io
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

out = Path(sys.argv[1]) / "preview"
font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
plots = (("assembly", "ASSEMBLY - F.SILKS / F.FAB / F.CRTYD"),
         ("front-copper", "FRONT COPPER - F.CU"),
         ("back-copper", "BACK COPPER - B.CU (UNMIRRORED)"))
# Autoscaled landscape A4 output for the fixed 100 x 300 mm outline, at 150 dpi.
board_pixels = (711, 123, 1042, 1116)
regions = (("controller", (40, -4, 104, 80)),
           ("audio", (40, 215, 104, 304)))


def render(pdf, dpi):
    data = subprocess.run(
        ["gs", "-q", "-dSAFER", "-dBATCH", "-dNOPAUSE", "-sDEVICE=png16m",
         f"-r{dpi}", "-sOutputFile=-", str(pdf)], check=True,
        stdout=subprocess.PIPE).stdout
    return Image.open(io.BytesIO(data)).convert("RGB")


def label(image, title):
    result = Image.new("RGB", (max(image.width, 760), image.height + 70), "white")
    result.paste(image, (0, 38))
    draw = ImageDraw.Draw(result)
    draw.text((8, 6), title, font=font, fill="black")
    draw.text((8, image.height + 42), "EXPERIMENTAL - NOT FOR FABRICATION OR POWER",
              font=font, fill="black")
    return result


for name, title in plots:
    pdf = out / (name + ".pdf")
    page = render(pdf, 150)
    if page.size != (1754, 1240):
        raise ValueError(f"Unexpected PDF page size: {page.size}")
    label(page, title).save(out / (name + ".png"))
    high = render(pdf, 600)
    if high.size != (7016, 4961):
        raise ValueError(f"Unexpected high-resolution PDF page size: {high.size}")
    left, top, right, bottom = board_pixels
    for region, (x1, y1, x2, y2) in regions:
        rect = tuple(round(v * 4) for v in (
            left + x1 * (right - left) / 100, top + y1 * (bottom - top) / 300,
            left + x2 * (right - left) / 100, top + y2 * (bottom - top) / 300))
        label(high.crop(rect), f"{title} - {region.upper()} ESP").save(
            out / f"closeup-{name}-{region}.png")
