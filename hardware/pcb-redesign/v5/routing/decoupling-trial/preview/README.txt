Decoupling trial inspection views — NOT FOR FABRICATION OR POWER-UP
==================================================================

These are inspection plots of ../result.kicad_pcb, SHA-256:
53428c44aaf48bd0ea867c7b11f82e9277dcee58e0993fbcc820f4a65fc4612f
They depict the final decoupling-trial candidate, NOT silk-7 or placement
trial B. The source board, project, schematic and reports are unchanged.
The "decoupling-plot.kicad_pcb" filename in the title block is a disposable
plot-only copy, not a separate design.

Single-page fitted A4 PDFs and matching 150 dpi PNGs:
  assembly.pdf / .png       F.SilkS, F.CrtYd, Edge.Cuts; black on white
  front-copper.pdf / .png   F.Cu, Edge.Cuts; red copper
  back-copper.pdf / .png    B.Cu, Edge.Cuts; blue copper

The nine closeup-*.png images are 600 dpi crops from the corresponding PDFs,
with identifying headings and warnings added outside the artwork. For each
view, controller is the upper section, audio the lower section, and
c7-u9-c14-u11 focuses on those parts and their nearby routing. Controller
and audio overlap around the section split; crop edges intentionally truncate
some traces. The three crops of each region use identical coordinates, so
the assembly crop can be compared with the copper crops. All views are
unmirrored. Copper plots do not identify nets or footprint references.
The plots are fitted inspection aids, not 1:1 fabrication artwork or
clearance measurements. Full-page previews show the entire PCB outline and
legible titles and warnings inside the drawing frame; reference labels are
more useful in the enlarged assembly images.

This is not physical, electrical, RF, solder-access, or fabrication signoff.
Long supply/return paths and unrelated THT pad clearances remain serious
unresolved issues. Native DRC and parity reports are not proof of acceptable
power integrity, assembly fit or safety. See ../README.txt and its reports
for the candidate's specific limitations and ignored checks.

Reproduce from the repository root using the existing KiCad 10.0.2 image
(which includes Ghostscript, Pillow and DejaVu Sans). The command mounts the
candidate read-only; transient plot data stays in the disposable container
working directory, and only the preview outputs are written here.

  P=hardware/pcb-redesign/v5/routing/decoupling-trial
  docker run --rm --network none --user 0:0 --workdir /workspace \
    -e TMPDIR=/workspace -e PYTHONDONTWRITEBYTECODE=1 \
    -v "$PWD/$P:/source:ro" -v "$PWD/$P/preview:/workspace/output" \
    --entrypoint /bin/bash kicad/kicad:10.0.2 \
    -c 'python3 output/generate.py && chown "$1:$2" output/*.pdf output/*.png' \
    -- "$(id -u)" "$(id -g)"

The generator checks the candidate hash, changes only title-block fields in
the plot copy, and uses explicit KiCad layer selections. It does not refill
zones or modify the board. The PNGs are rendered from the generated PDFs;
closeup crop positions are tied to the fitted A4 page and checked page size.
