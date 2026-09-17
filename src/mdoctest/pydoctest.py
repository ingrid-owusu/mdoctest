"""Python REPL (``>>>``) doctest blocks for mdoctest.

A fenced block tagged ``pycon`` (or a ``python`` / untagged block whose first
non-blank line is a ``>>>`` prompt) is treated the way Python's own ``doctest``
treats a docstring: every ``>>>`` / ``...`` statement is executed in a shared
namespace and its result is checked against the expected output that follows.

Parsing reuses the standard-library :mod:`doctest` parser, so all the usual
prompt/continuation rules apply. Execution is done here (rather than through
``doctest.DocTestRunner``) so we can capture the *actual* output for ``--fix``
and reuse mdoctest's own ``...`` wildcard matcher for checking.
"""
from __future__ import annotations

import doctest
import io
import sys
import traceback
from typing import List, Tuple

from .match import matches, normalize

#: Info-string languages that are always Python REPL sessions.
PYCON_LANGS = {"pycon", "python-repl", "python-console", "py-repl", "pyrepl"}
#: Languages that *may* be a REPL session if they open with a ``>>>`` prompt.
MAYBE_PYCON_LANGS = {"python", "py", "python3", ""}

_TRACEBACK_HEADER = "Traceback (most recent call last):"


def _first_nonblank(text: str) -> str:
    for ln in text.split("\n"):
        if ln.strip():
            return ln
    return ""


def is_pydoctest(lang: str, content: str) -> bool:
    """True if *content* should be run as a Python ``>>>`` doctest block."""
    if lang in PYCON_LANGS:
        return True
    if lang in MAYBE_PYCON_LANGS:
        return _first_nonblank(content).lstrip().startswith(">>>")
    return False


def _format_exception(exc: BaseException) -> str:
    """Render an exception the way a doctest expects it.

    The traceback body is elided to ``...`` (mdoctest's wildcard), so expected
    output stays portable across machines and Python versions while the header
    and final ``ExcType: message`` line are matched exactly.
    """
    last = traceback.format_exception_only(type(exc), exc)[-1].rstrip("\n")
    return "%s\n  ...\n%s" % (_TRACEBACK_HEADER, last)


def run_examples(content: str, name: str = "<md>") -> List[Tuple[doctest.Example, str]]:
    """Execute every example in *content*, returning ``(example, actual)`` pairs.

    Examples share a single namespace, so names defined by one example are
    visible to the next -- exactly like a real REPL session.
    """
    examples = doctest.DocTestParser().get_doctest(content, {}, name, name, 0).examples
    ns: dict = {"__name__": "__mdoctest__"}
    results: List[Tuple[doctest.Example, str]] = []
    for ex in examples:
        actual = _exec_one(ex.source, name, ns)
        results.append((ex, actual))
    return results


def _exec_one(source: str, filename: str, ns: dict) -> str:
    old_stdout = sys.stdout
    old_displayhook = sys.displayhook
    buf = io.StringIO()
    sys.stdout = buf
    sys.displayhook = sys.__displayhook__  # print reprs into our buffer
    try:
        try:
            code = compile(source, filename, "single")
        except SyntaxError:
            code = compile(source, filename, "exec")
        exec(code, ns)
    except SystemExit as exc:  # don't let a doc example kill the process
        return _finish(buf, old_stdout, old_displayhook) + _format_exception(exc)
    except BaseException as exc:  # noqa: BLE001 - report, like the REPL does
        return _finish(buf, old_stdout, old_displayhook) + _format_exception(exc)
    return _finish(buf, old_stdout, old_displayhook)


def _finish(buf: io.StringIO, old_stdout, old_displayhook) -> str:
    sys.stdout = old_stdout
    sys.displayhook = old_displayhook
    return buf.getvalue()


def check(content: str, name: str = "<md>"):
    """Run *content*; return ``(ok, [(source, want, got, ok), ...])``."""
    out = []
    all_ok = True
    for ex, actual in run_examples(content, name):
        want = ex.want
        ok = matches(want, actual)
        if not ok:
            all_ok = False
        out.append((ex.source.rstrip("\n"), want, actual, ok))
    return all_ok, out


def fix(content: str, name: str = "<md>") -> str:
    """Return *content* with every example's expected output replaced by reality."""
    results = run_examples(content, name)
    got_by_lineno = {ex.lineno: actual for ex, actual in results}

    pieces = doctest.DocTestParser().parse(content, name)
    rebuilt: List[str] = []
    for piece in pieces:
        if isinstance(piece, str):
            rebuilt.append(piece)
            continue
        rebuilt.append(_render_example(piece, got_by_lineno.get(piece.lineno, piece.want)))
    return "".join(rebuilt)


def _render_example(ex: doctest.Example, got: str) -> str:
    indent = " " * ex.indent
    src_lines = ex.source.rstrip("\n").split("\n")
    lines = [indent + ">>> " + src_lines[0]]
    for extra in src_lines[1:]:
        lines.append(indent + "... " + extra)
    want = normalize(got)
    if want:
        for wl in want.split("\n"):
            lines.append(indent + wl if wl else wl)
    return "\n".join(lines) + "\n"
