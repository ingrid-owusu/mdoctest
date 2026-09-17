"""Orchestration: find runnable blocks in Markdown, run them, check or fix."""
from __future__ import annotations

import difflib
import os
import shlex
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from typing import List, Optional

from .match import matches, normalize
from .parser import Block, parse_blocks, parse_setups
from .pydoctest import check as pydoctest_check
from .pydoctest import fix as pydoctest_fix
from .pydoctest import is_pydoctest
from .session import Shell, parse_session, _pending_heredoc

CONSOLE_LANGS = {"console", "shell-session", "sh-session", "shellsession",
                 "terminal", "con"}
SHELLISH = {"sh", "bash", "shell", "zsh", "console"}

# language -> interpreter argv for `run` (whole-block) mode.
# For anything not listed here, tag the block with an explicit command, e.g.
#   <!-- mdoctest: run cmd="go run" ext=.go -->
# so mdoctest is genuinely language-agnostic (see _run_block).
INTERPRETERS = {
    "python": ["python3"], "py": ["python3"], "python3": ["python3"],
    "bash": ["bash"], "sh": ["sh"], "shell": ["bash"], "zsh": ["zsh"],
    "node": ["node"], "js": ["node"], "javascript": ["node"], "mjs": ["node"],
    "ruby": ["ruby"], "rb": ["ruby"],
    "perl": ["perl"],
    "php": ["php"],
    "lua": ["lua"],
    "go": ["go", "run"],
    "r": ["Rscript"],
    "deno": ["deno", "run", "-"],
}

# language -> temp-file suffix (some interpreters, e.g. `go run`, require it).
SUFFIXES = {
    "python": ".py", "py": ".py", "python3": ".py",
    "node": ".js", "js": ".js", "javascript": ".js", "mjs": ".mjs",
    "ruby": ".rb", "rb": ".rb",
    "perl": ".pl",
    "php": ".php",
    "lua": ".lua",
    "go": ".go",
    "r": ".R",
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
        for i, extra in enumerate(cmd_lines[1:], start=1):
            # A here-document body/terminator must be emitted literally: if the
            # command formed by the preceding physical lines is still inside a
            # here-doc, this line is heredoc content, not a ``> `` continuation.
            if _pending_heredoc("\n".join(cmd_lines[:i])):
                out_lines.append(extra)
            else:
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
    setups = parse_setups(text)
    # Collect edits for fix mode as (body_start, body_end, new_body_lines).
    edits = []
    cwd = opts.cwd or os.path.dirname(os.path.abspath(path)) or None

    for block in blocks:
        if block.directive == "skip":
            fr.blocks.append(BlockResult("skip", block.open_line + 1, True,
                                         skipped_reason="skip directive"))
            continue

        # A code block adopted as an ``<!-- mdoctest: setup -->`` fixture script
        # is invisible plumbing (parse_setups already captured it); never run or
        # check it as an example.
        if block.directive == "setup":
            continue

        if is_pydoctest(block.lang, block.content):
            br = BlockResult("pydoctest", block.open_line + 1, True)
            ok_all, rows = pydoctest_check(block.content, path)
            for src, want, got, ok in rows:
                br.cmds.append(CmdResult(src, want, got, ok))
                if not ok:
                    br.ok = False
            if not br.cmds:
                continue
            fr.blocks.append(br)
            if fix and not br.ok:
                new_body = pydoctest_fix(block.content, path)
                new_lines = new_body.split("\n")
                if new_lines and new_lines[-1] == "":
                    new_lines.pop()
                edits.append((block.body_start, block.body_end, new_lines))
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
        # Setup fixtures: any `<!-- mdoctest: setup -->` block earlier in the
        # document seeds this session. To keep fixtures from touching the user's
        # repo, sessions run in a throwaway sandbox dir whenever the file uses
        # setup at all; otherwise cwd stays the Markdown file's directory.
        pre_scripts = [s.script for s in setups
                       if s.open_line < block.open_line and s.script.strip()]
        sandbox = tempfile.mkdtemp(prefix="mdoctest-setup-") if setups else None
        run_cwd = sandbox or cwd
        try:
            with Shell(opts.shell, cwd=run_cwd, timeout=opts.timeout) as sh:
                for ps in pre_scripts:
                    sh.run(ps)
                for c in parsed.commands:
                    actual, _code = sh.run(c.cmd)
                    ok = matches(c.expected, actual)
                    cr = CmdResult(c.cmd, c.expected, actual, ok)
                    br.cmds.append(cr)
                    if not ok:
                        br.ok = False
        finally:
            if sandbox:
                shutil.rmtree(sandbox, ignore_errors=True)
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
    # An explicit `cmd="..."` on the directive makes mdoctest work with *any*
    # language/toolchain, not just the built-in interpreters.
    cmd_override = block.directive_opts.get("cmd")
    if cmd_override:
        try:
            argv = shlex.split(cmd_override)
        except ValueError:
            argv = cmd_override.split()
    else:
        argv = INTERPRETERS.get(block.lang)
    if not argv:
        br.ok = True
        br.skipped_reason = (
            "no interpreter for '%s' (add `cmd=\"...\"` to the directive)"
            % (block.lang or "?"))
        return br
    exe = shutil.which(argv[0])
    if not exe:
        br.ok = True
        br.skipped_reason = "%s not installed" % argv[0]
        return br
    suffix = block.directive_opts.get("ext") or SUFFIXES.get(block.lang, ".sh")
    if suffix and not suffix.startswith("."):
        suffix = "." + suffix
    with tempfile.NamedTemporaryFile("w", suffix=suffix, delete=False,
                                     dir=cwd, encoding="utf-8") as tf:
        tf.write(block.content)
        tmp = tf.name
    try:
        proc = subprocess.run([exe] + argv[1:] + [tmp], cwd=cwd,
                              capture_output=True, text=True, timeout=60)
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
