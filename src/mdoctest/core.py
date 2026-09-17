"""Orchestration: find runnable blocks in Markdown, run them, check or fix."""
from __future__ import annotations

import difflib
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from typing import List, Optional

from .match import matches, normalize
from .parser import Block, parse_blocks
from .session import Shell, parse_session

CONSOLE_LANGS = {"console", "shell-session", "sh-session", "shellsession",
                 "terminal", "con"}
SHELLISH = {"sh", "bash", "shell", "zsh", "console"}

# language -> interpreter argv for `run` (whole-block) mode
INTERPRETERS = {
    "python": ["python3"], "py": ["python3"], "python3": ["python3"],
    "bash": ["bash"], "sh": ["sh"], "shell": ["bash"], "zsh": ["zsh"],
    "node": ["node"], "js": ["node"], "javascript": ["node"],
    "ruby": ["ruby"], "rb": ["ruby"],
    "perl": ["perl"],
}


@dataclass
class CmdResult:
    command: str
    expected: str
    actual: str
    ok: bool


@dataclass
class BlockResult:
    kind: str                 # 'session' | 'run'
    open_line: int            # 1-based, for display
    ok: bool
    cmds: List[CmdResult] = field(default_factory=list)
    message: str = ""
    skipped_reason: str = ""


@dataclass
class FileResult:
    path: str
    blocks: List[BlockResult] = field(default_factory=list)
    fixed: int = 0
    error: str = ""

    @property
    def failures(self) -> int:
        return sum(1 for b in self.blocks if not b.ok and not b.skipped_reason)

    @property
    def checked(self) -> int:
        return sum(1 for b in self.blocks if not b.skipped_reason)


def _first_nonblank(body: str) -> str:
    for ln in body.split("\n"):
        if ln.strip():
            return ln
    return ""


def is_session(block: Block, prompt: str) -> bool:
    if block.lang in CONSOLE_LANGS:
        return True
    if block.lang in SHELLISH and _first_nonblank(block.content).startswith(prompt):
        return True
    return False


@dataclass
class Options:
    shell: str = "bash"
    prompt: str = "$ "
    cont: str = "> "
    timeout: float = 30.0
    cwd: Optional[str] = None


def _reconstruct_session(cmds, prompt, cont) -> str:
    out_lines: List[str] = []
    for c in cmds:
        cmd_lines = c.command.split("\n")
        out_lines.append(prompt + cmd_lines[0])
        for extra in cmd_lines[1:]:
            out_lines.append(cont + extra)
        actual = normalize(c.actual)
        if actual:
            out_lines.extend(actual.split("\n"))
    return "\n".join(out_lines)


def process_file(path: str, opts: Options, fix: bool = False) -> FileResult:
    fr = FileResult(path=path)
    try:
        with open(path, "r", encoding="utf-8") as fh:
            text = fh.read()
    except OSError as e:
        fr.error = str(e)
        return fr

    trailing_nl = text.endswith("\n")
    lines = text.split("\n")
    blocks = parse_blocks(text)
    # Collect edits for fix mode as (body_start, body_end, new_body_lines).
    edits = []
    cwd = opts.cwd or os.path.dirname(os.path.abspath(path)) or None

    for block in blocks:
        if block.directive == "skip":
            fr.blocks.append(BlockResult("skip", block.open_line + 1, True,
                                         skipped_reason="skip directive"))
            continue

        if block.directive == "run" and block.lang not in CONSOLE_LANGS:
            fr.blocks.append(_run_block(block, cwd))
            continue

        if not is_session(block, opts.prompt):
            continue

        br = BlockResult("session", block.open_line + 1, True)
        parsed = parse_session(block.content, opts.prompt, opts.cont)
        if not parsed.commands:
            continue
        with Shell(opts.shell, cwd=cwd, timeout=opts.timeout) as sh:
            for c in parsed.commands:
                actual, _code = sh.run(c.cmd)
                ok = matches(c.expected, actual)
                cr = CmdResult(c.cmd, c.expected, actual, ok)
                br.cmds.append(cr)
                if not ok:
                    br.ok = False
        fr.blocks.append(br)

        if fix and not br.ok:
            new_body = _reconstruct_session(
                [(_C(cr.command, cr.actual)) for cr in br.cmds],
                opts.prompt, opts.cont)
            edits.append((block.body_start, block.body_end, new_body.split("\n")))

    if fix and edits:
        for body_start, body_end, new_lines in sorted(edits, reverse=True):
            lines[body_start:body_end] = new_lines
        new_text = "\n".join(lines)
        if trailing_nl and not new_text.endswith("\n"):
            new_text += "\n"
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(new_text)
        fr.fixed = len(edits)
        # After a fix, the file passes by construction.
        for b in fr.blocks:
            b.ok = True
    return fr


class _C:
    def __init__(self, command, actual):
        self.command = command
        self.actual = actual


def _run_block(block: Block, cwd) -> BlockResult:
    br = BlockResult("run", block.open_line + 1, True)
    argv = INTERPRETERS.get(block.lang)
    if not argv:
        br.ok = True
        br.skipped_reason = "no interpreter for '%s'" % block.lang
        return br
    exe = shutil.which(argv[0])
    if not exe:
        br.ok = True
        br.skipped_reason = "%s not installed" % argv[0]
        return br
    suffix = {"python": ".py", "py": ".py", "python3": ".py",
              "node": ".js", "js": ".js", "javascript": ".js",
              "ruby": ".rb", "rb": ".rb"}.get(block.lang, ".sh")
    with tempfile.NamedTemporaryFile("w", suffix=suffix, delete=False,
                                     dir=cwd, encoding="utf-8") as tf:
        tf.write(block.content)
        tmp = tf.name
    try:
        proc = subprocess.run([exe, tmp], cwd=cwd, capture_output=True,
                              text=True, timeout=60)
        if proc.returncode != 0:
            br.ok = False
            br.message = (proc.stdout + proc.stderr).strip()[-2000:]
    except Exception as e:  # noqa: BLE001
        br.ok = False
        br.message = str(e)
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass
    return br


def render_diff(expected: str, actual: str, color: bool = False) -> str:
    exp = normalize(expected).split("\n")
    act = normalize(actual).split("\n")
    lines = []
    for ln in difflib.unified_diff(exp, act, fromfile="expected",
                                   tofile="actual", lineterm=""):
        if color:
            if ln.startswith("+") and not ln.startswith("+++"):
                ln = "\033[32m%s\033[0m" % ln
            elif ln.startswith("-") and not ln.startswith("---"):
                ln = "\033[31m%s\033[0m" % ln
            elif ln.startswith("@@"):
                ln = "\033[36m%s\033[0m" % ln
        lines.append(ln)
    return "\n".join(lines)
