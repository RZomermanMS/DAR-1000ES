#!/usr/bin/env python3
"""Plot the integrated board and generate unmirrored inspection images."""
import io
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
BOARD = HERE.parent / "result.kicad_pcb"
PLOT_BOARD = HERE / "clearance-first-plot.kicad_pcb"
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
PLOTS = (("assembly", "F.SilkS,F.CrtYd,Edge.Cuts"),
         ("front-copper", "F.Cu,Edge.Cuts"),
         ("back-copper", "B.Cu,Edge.Cuts"))
CROPS = (("controller", (700, 112, 1044, 650)),
         ("audio", (700, 630, 1044, 1128)),
         ("c7-u9-c14-u11", (700, 920, 960, 1080)))


def run(*args, **kwargs):
    return subprocess.run(args, check=True, **kwargs)


def main():
    if PLOT_BOARD.exists():
        raise ValueError("Plot scratch board already exists")
    text = BOARD.read_text()
    substitutions = {
        '(title "DAR-1000ES v5 - experimental, not for fabrication")':
            '(title "DAR-1000ES v5 CLEARANCE FIXED")',
        '(rev "v5 experimental")': '(rev "v5")',
        '(comment 1 "100 x 300 mm outline; mechanical fit unverified")':
            '(comment 1 "EXPERIMENTAL - NOT FOR FABRICATION")',
        '(comment 2 "Experimental routing; electrical and RF review required")':
            '(comment 2 "Electrical, RF and mechanical review required")',
    }
    for old, new in substitutions.items():
        if text.count(old) != 1:
            raise ValueError(f"Unexpected title block: {old}")
        text = text.replace(old, new)
    PLOT_BOARD.write_text(text)
    try:
        plot_all()
    finally:
        PLOT_BOARD.unlink(missing_ok=True)
        PLOT_BOARD.with_suffix(".kicad_pro").unlink(missing_ok=True)
        PLOT_BOARD.with_suffix(".kicad_prl").unlink(missing_ok=True)


def plot_all():
    for name, layers in PLOTS:
        pdf = HERE / f"{name}.pdf"
        cmd = ["kicad-cli", "pcb", "export", "pdf", "--mode-single",
               "--include-border-title", "--scale", "0", "--layers", layers,
               "--output", str(pdf)]
        if name == "assembly":
            cmd.append("--black-and-white")
        run(*cmd, str(PLOT_BOARD))
        run("gs", "-q", "-dSAFER", "-dBATCH", "-dNOPAUSE", "-sDEVICE=png16m",
            "-r150", f"-sOutputFile={HERE / (name + '.png')}", str(pdf))
        rendered = run("gs", "-q", "-dSAFER", "-dBATCH", "-dNOPAUSE",
                       "-sDEVICE=png16m", "-r600", "-sOutputFile=-", str(pdf),
                       stdout=subprocess.PIPE)
        page = Image.open(io.BytesIO(rendered.stdout)).convert("RGB")
        if page.size != (7016, 4961):
            raise ValueError(f"Unexpected page size: {page.size}")
        font = ImageFont.truetype(FONT, 32)
        for region, bounds in CROPS:
            crop = page.crop(tuple(x * 4 for x in bounds))
            canvas = Image.new("RGB", (crop.width, crop.height + 110), "white")
            canvas.paste(crop, (0, 60))
            draw = ImageDraw.Draw(canvas)
            draw.text((10, 10), f"CLEARANCE FIXED - {name.upper()} - {region.upper()}",
                      font=font, fill="black")
            draw.text((10, crop.height + 67), "EXPERIMENTAL - NOT FOR FABRICATION",
                      font=font, fill="black")
            canvas.save(HERE / f"closeup-{name}-{region}.png")


if __name__ == "__main__":
    main()
