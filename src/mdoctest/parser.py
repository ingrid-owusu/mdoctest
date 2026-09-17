"""Minimal, dependency-free parser for fenced code blocks in Markdown.

Handles CommonMark-style fences (``` or ~~~, three or more, up to three
spaces of indentation) which covers essentially every real-world README. It is
deliberately small: mdoctest only needs to find fenced blocks, their info
string, their body, and their line span so ``--fix`` can rewrite them.
"""
from __future__ import annotations

import re
import shlex
from dataclasses import dataclass, field
from typing import Dict, List, Optional

_FENCE_RE = re.compile(r"^(?P<indent> {0,3})(?P<fence>`{3,}|~{3,})(?P<info>.*)$")
_DIRECTIVE_RE = re.compile(r"^\s*<!--\s*mdoctest:\s*(?P<body>.*?)\s*-->\s*$")
_SETUP_OPEN_RE = re.compile(r"^\s*<!--\s*mdoctest:\s*setup\b(?P<rest>.*)$")


@dataclass
class Setup:
    """An invisible ``<!-- mdoctest: setup ... -->`` fixture block.

    The comment is hidden in rendered Markdown, so it never clutters the docs a
    reader sees, but mdoctest runs its shell script (in a throwaway sandbox
    directory) before the session blocks that follow it — the natural way to
    create the fixture files/env a real README's examples assume already exist.
    """
    open_line: int   # 0-based line of the opening ``<!--``
    script: str      # shell script body (lines joined with "\n")


@dataclass
class Block:
    lang: str            # first token of the info string, lowercased
    info: str            # full info string (may carry extra attrs)
    content: str         # body text (no fences), lines joined with "\n"
    open_line: int       # 0-based index of the opening fence line
    close_line: int      # 0-based index of the closing fence line (== EOF span)
    indent: str          # leading indentation of the fence
    directive: Optional[str] = None  # 'skip' | 'run' | None
    # Options attached to the directive, e.g. ``run cmd="go run" ext=.go`` ->
    # {"cmd": "go run", "ext": ".go"}. Empty when there is no directive.
    directive_opts: Dict[str, str] = field(default_factory=dict)

    @property
    def body_start(self) -> int:
        return self.open_line + 1

    @property
    def body_end(self) -> int:
        return self.close_line  # exclusive


def _parse_directive(line: str):
    """Return ``(verb, opts)`` for an ``<!-- mdoctest: ... -->`` line.

    ``verb`` is the lowercased first token ('skip' | 'run' | ...) or ``None``
    when the line is not a directive / is empty. ``opts`` is a dict of the
    ``key=value`` pairs that follow (values may be quoted), e.g.
    ``run cmd="go run" ext=.go`` -> ('run', {'cmd': 'go run', 'ext': '.go'}).
    """
    m = _DIRECTIVE_RE.match(line)
    if not m:
        return None, {}
    try:
        tok = shlex.split(m.group("body"))
    except ValueError:
        tok = m.group("body").split()
    if not tok:
        return None, {}
    verb = tok[0].lower()
    opts: Dict[str, str] = {}
    for t in tok[1:]:
        if "=" in t:
            k, v = t.split("=", 1)
            opts[k.strip().lower()] = v
    return verb, opts


def parse_blocks(text: str) -> List[Block]:
    lines = text.split("\n")
    blocks: List[Block] = []
    i = 0
    n = len(lines)
    while i < n:
        m = _FENCE_RE.match(lines[i])
        if not m:
            i += 1
            continue
        indent = m.group("indent")
        fence = m.group("fence")
        info = m.group("info").strip()
        fence_char = fence[0]
        fence_len = len(fence)
        # An info string may not contain backticks for backtick fences.
        if fence_char == "`" and "`" in info:
            i += 1
            continue
        open_line = i
        j = i + 1
        close_line = n  # default: unclosed runs to EOF
        while j < n:
            cm = re.match(r"^ {0,3}(?P<f>%s{%d,})\s*$" % (re.escape(fence_char), fence_len), lines[j])
            if cm:
                close_line = j
                break
            j += 1
        body = lines[open_line + 1: close_line]
        lang = info.split()[0].lower() if info else ""
        directive, directive_opts = _find_directive(lines, open_line)
        blocks.append(Block(
            lang=lang, info=info, content="\n".join(body),
            open_line=open_line, close_line=close_line, indent=indent,
            directive=directive, directive_opts=directive_opts,
        ))
        i = close_line + 1
    return blocks


def parse_setups(text: str) -> List["Setup"]:
    """Find every ``<!-- mdoctest: setup ... -->`` block and return its script.

    Both one-line (``<!-- mdoctest: setup mkdir demo -->``) and multi-line forms
    are supported; a multi-line comment runs until the closing ``-->``::

        <!-- mdoctest: setup
        cat > data.csv <<'END'
        a,b
        END
        -->

    Any line may contain shell (including here-documents) as long as it does not
    contain the comment terminator ``-->``.
    """
    lines = text.split("\n")
    setups: List[Setup] = []
    i = 0
    n = len(lines)
    while i < n:
        m = _SETUP_OPEN_RE.match(lines[i])
        if not m:
            i += 1
            continue
        open_line = i
        rest = m.group("rest")
        script: List[str] = []
        # One-line form: everything before --> on the opening line is the script.
        if "-->" in rest:
            body = rest.split("-->", 1)[0]
            if body.strip():
                script.append(body.strip())
            else:
                # Empty ``<!-- mdoctest: setup -->`` comment: attach the body of
                # the immediately-following fenced code block as the fixture
                # script. This mirrors how ``run``/``skip`` directives attach to
                # the next block, so ``<!-- mdoctest: setup -->`` above a
                # ```sh block just works instead of silently doing nothing.
                block_body = _following_fence_body(lines, open_line + 1)
                if block_body is not None:
                    script.append(block_body)
            setups.append(Setup(open_line, "\n".join(script)))
            i += 1
            continue
        if rest.strip():
            script.append(rest.strip())
        j = i + 1
        closed_at = None
        while j < n:
            if "-->" in lines[j]:
                before = lines[j].split("-->", 1)[0]
                if before.strip():
                    script.append(before)
                closed_at = j
                break
            script.append(lines[j])
            j += 1
        setups.append(Setup(open_line, "\n".join(script)))
        i = (closed_at + 1) if closed_at is not None else j
    return setups


def _following_fence_body(lines: List[str], start: int):
    """Return the body of the next fenced code block at/after ``start``.

    Only blank lines may separate ``start`` from the opening fence; if the next
    non-blank line is not a fence, return ``None``. Used to let an empty
    ``<!-- mdoctest: setup -->`` comment adopt the following code block as its
    fixture script.
    """
    n = len(lines)
    k = start
    while k < n and lines[k].strip() == "":
        k += 1
    if k >= n:
        return None
    m = _FENCE_RE.match(lines[k])
    if not m:
        return None
    fence_char = m.group("fence")[0]
    fence_len = len(m.group("fence"))
    if fence_char == "`" and "`" in m.group("info"):
        return None
    j = k + 1
    close = n
    while j < n:
        if re.match(r"^ {0,3}(?P<f>%s{%d,})\s*$" % (re.escape(fence_char), fence_len), lines[j]):
            close = j
            break
        j += 1
    return "\n".join(lines[k + 1:close])


def _find_directive(lines: List[str], open_line: int):
    """A directive is an ``<!-- mdoctest: ... -->`` comment that is the nearest
    non-blank line above the fence (blank lines are allowed in between)."""
    k = open_line - 1
    while k >= 0 and lines[k].strip() == "":
        k -= 1
    if k < 0:
        return None, {}
    return _parse_directive(lines[k])
