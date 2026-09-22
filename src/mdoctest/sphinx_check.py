"""Pure (sphinx-free) helpers backing the mdoctest Sphinx extension.

Kept free of any ``sphinx`` import so the logic is unit-testable without Sphinx
installed. The thin Sphinx wrapper lives in ``mdoctest.sphinx_ext`` and
delegates here.

The extension checks the runnable examples in a Sphinx project's **Markdown
(MyST) sources** — console/shell ``$`` sessions, ``pycon`` ``>>>`` blocks and
language-tagged ``run`` blocks. reStructuredText (``.rst``) sources are left to
Sphinx's own ``sphinx.ext.doctest``; mdoctest fills the gap for Markdown docs
and for the shell/other-language blocks ``doctest`` cannot run.
"""
from __future__ import annotations

from typing import List, Optional

from .core import Options
from .mkdocs_check import DocsReport, check_docs


def check_sphinx_docs(
    srcdir: str,
    patterns: Optional[List[str]] = None,
    opts: Optional[Options] = None,
) -> DocsReport:
    """Run mdoctest (check-only) over the Markdown sources under ``srcdir``.

    With no ``patterns`` every Markdown/MyST file under the Sphinx source
    directory is checked (``.rst`` is ignored). ``patterns`` are globs resolved
    relative to ``srcdir``.
    """
    return check_docs(srcdir, patterns, opts)


def summarize(report: DocsReport) -> Optional[str]:
    """Human-readable problem summary, or ``None`` when the report is clean."""
    if report.ok:
        return None
    return "mdoctest found {0} problem(s) in your docs:\n  - {1}".format(
        report.failures + report.errors,
        "\n  - ".join(report.messages),
    )
