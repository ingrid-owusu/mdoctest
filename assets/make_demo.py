#!/usr/bin/env python3
"""Generate assets/demo.svg: a self-contained animated terminal demo for mdoctest.

No external dependencies. Uses SMIL <animate> so it plays on GitHub (which
serves README images via camo and preserves SMIL animation). Regenerate with:
    python assets/make_demo.py

The demo mirrors mdoctest's real output verbatim: a drifted example is caught
with a diff, `--fix` repairs it in place, and a re-check goes green.
"""
import os
from html import escape

BG = "#1b1e24"
FG = "#d7dae0"
GREEN = "#7ec699"
BLUE = "#6cb6ff"
YELLOW = "#e2c08d"
GREY = "#7d8590"
RED = "#f47067"
PROMPT = "#8ddb8c"

FONT = "ui-monospace, 'SF Mono', 'Cascadia Code', Menlo, Consolas, monospace"
FS = 15
LH = 22
PAD_X = 18
PAD_Y = 46
W = 800
CHARW = FS * 0.60
TOTAL = 11.0

# (delay seconds, [(text, color), ...])
lines = [
    (0.2, [("$ ", PROMPT), ("mdoctest README.md", FG), ("        # your docs are untested code", GREY)]),
    (1.3, [("FAIL  ", RED), ("README.md:12 (session)", FG)]),
    (1.6, [("    $ echo hello | tr a-z A-Z", FG)]),
    (1.9, [("      -HELXO", RED), ("   documented", GREY)]),
    (2.2, [("      +HELLO", GREEN), ("   actual", GREY)]),
    (2.6, [("FAIL  ", RED), ("checked 6 block(s), 1 failed", FG)]),
    (4.4, [("$ ", PROMPT), ("mdoctest --fix README.md", FG)]),
    (5.6, [("FIXED  ", GREEN), ("fixed 1 block(s) across 1 file(s)", FG)]),
    (7.2, [("$ ", PROMPT), ("mdoctest README.md", FG)]),
    (8.4, [("OK  ", GREEN), ("checked 6 block(s), 0 failed", FG), ("   \u2713 docs match", GREY)]),
]

n = len(lines)
H = PAD_Y + LH * n + 14


def loop_anim(delay):
    fade = 0.25
    return (
        f'<animate attributeName="opacity" '
        f'values="0;0;1;1;0" '
        f'keyTimes="0;{delay/TOTAL:.3f};{(delay+fade)/TOTAL:.3f};0.965;1" '
        f'dur="{TOTAL:.1f}s" repeatCount="indefinite"/>'
    )


parts = [
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
    f'viewBox="0 0 {W} {H}" font-family="{FONT}" font-size="{FS}">',
    f'<rect x="0" y="0" width="{W}" height="{H}" rx="10" fill="{BG}"/>',
    '<circle cx="20" cy="20" r="6" fill="#ff5f56"/>',
    '<circle cx="40" cy="20" r="6" fill="#ffbd2e"/>',
    '<circle cx="60" cy="20" r="6" fill="#27c93f"/>',
    f'<text x="{W//2}" y="25" fill="{GREY}" text-anchor="middle" '
    f'font-size="13">mdoctest \u2014 keep your README examples correct</text>',
]

for i, (delay, segs) in enumerate(lines):
    y = PAD_Y + 15 + i * LH
    tspans = []
    x = PAD_X
    for text, color in segs:
        tspans.append(
            f'<tspan x="{x}" fill="{color}" xml:space="preserve">{escape(text)}</tspan>'
        )
        x += len(text) * CHARW
    parts.append(
        f'<text y="{y}" opacity="1">' + "".join(tspans) + loop_anim(delay) + "</text>"
    )

parts.append("</svg>")

out = os.path.join(os.path.dirname(__file__), "demo.svg")
with open(out, "w") as f:
    f.write("\n".join(parts))
print("wrote", out, f"({H}px tall)")
