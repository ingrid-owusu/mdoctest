"""Output matching for mdoctest.

Comparison is line-oriented and forgiving of trailing whitespace. The ellipsis
token ``...`` is a wildcard, so non-deterministic fragments -- timestamps,
durations, temp paths -- can be elided in docs:

* inline, ``build ... done`` matches ``build 12345 done``;
* on a line of its own, ``...`` matches any number of lines (including none).
"""
from __future__ import annotations

import re
from functools import lru_cache
from typing import Tuple

ELLIPSIS = "..."


def normalize(text: str) -> str:
    """Strip trailing whitespace on each line and drop trailing blank lines."""
    lines = [ln.rstrip() for ln in text.replace("\r\n", "\n").split("\n")]
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines)


def _line_pattern(line: str) -> "re.Pattern":
    parts = line.split(ELLIPSIS)
    return re.compile(".*?".join(re.escape(p) for p in parts))


def matches(expected: str, actual: str) -> bool:
    exp = normalize(expected)
    act = normalize(actual)
    if ELLIPSIS not in exp:
        return exp == act
    exp_lines: Tuple[str, ...] = tuple(exp.split("\n"))
    act_lines: Tuple[str, ...] = tuple(act.split("\n"))
    return _match(exp_lines, 0, act_lines, 0)


@lru_cache(maxsize=None)
def _match(exp: Tuple[str, ...], ei: int, act: Tuple[str, ...], ai: int) -> bool:
    if ei == len(exp):
        return ai == len(act)
    line = exp[ei]
    if line.strip() == ELLIPSIS:
        # multi-line wildcard: consume zero or more actual lines
        for k in range(ai, len(act) + 1):
            if _match(exp, ei + 1, act, k):
                return True
        return False
    if ai >= len(act):
        return False
    if _line_pattern(line).fullmatch(act[ai]):
        return _match(exp, ei + 1, act, ai + 1)
    return False
