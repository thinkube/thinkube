# Copyright Alejandro Martínez Corriá and the Thinkube contributors
# SPDX-License-Identifier: Apache-2.0

"""Write the JupyterLab tab icons from the Thinkube Notebooks icon.

The notebook server shows favicon.ico, one icon per kind of document
(favicon-notebook.ico, favicon-file.ico, favicon-terminal.ico) and, while a
kernel runs code, favicon-busy-1.ico to favicon-busy-3.ico in turn. All of
them show the notebook-text hexagon from thinkube-style; the busy ones add
a yellow dot that grows over the three steps, so a busy kernel still shows
in the tab.

Usage: python3 make_favicons.py SOURCE_PNG FAVICON_DIR
"""

import sys
from pathlib import Path

from PIL import Image, ImageDraw

SIZES = [(16, 16), (32, 32), (48, 48)]
BUSY = "#eab308"  # thinkube-style warning yellow
PLAIN = ("favicon", "favicon-notebook", "favicon-file", "favicon-terminal")
# Dot diameter as a share of the icon's side, one per busy step.
BUSY_STEPS = (0.30, 0.38, 0.46)


def main(source: str, out_dir: str) -> None:
    out = Path(out_dir)
    if not out.is_dir():
        raise SystemExit(f"{out} is not a directory")

    icon = Image.open(source).convert("RGBA")
    # The hexagon is taller than wide; centre it on a square canvas.
    side = max(icon.size)
    square = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    square.paste(icon, ((side - icon.width) // 2, (side - icon.height) // 2))

    # The symbol is cut out of the hexagon, so it shows the tab behind it and
    # disappears on a dark tab. Everything not reached from the corners is
    # the hexagon or its cut-out: put white under it.
    shape = square.getchannel("A").point(lambda a: 255 if a else 0)
    for corner in ((0, 0), (side - 1, 0), (0, side - 1), (side - 1, side - 1)):
        if shape.getpixel(corner) == 0:
            ImageDraw.floodfill(shape, corner, 128)
    inside = shape.point(lambda v: 0 if v == 128 else 255)
    white = Image.new("RGBA", (side, side), (255, 255, 255, 0))
    white.putalpha(inside)
    square = Image.alpha_composite(white, square)

    for name in PLAIN:
        square.save(out / f"{name}.ico", sizes=SIZES)

    for step, share in enumerate(BUSY_STEPS, start=1):
        busy = square.copy()
        r = side * share / 2
        c = side - r
        ImageDraw.Draw(busy).ellipse(
            (c - r, c - r, c + r, c + r), fill=BUSY, outline="#ffffff", width=max(1, round(side * 0.04))
        )
        busy.save(out / f"favicon-busy-{step}.ico", sizes=SIZES)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    main(sys.argv[1], sys.argv[2])
