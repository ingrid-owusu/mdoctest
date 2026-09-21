"""Pure (mkdocs-free) helpers that run mdoctest over a docs tree.

Kept deliberately free of any ``mkdocs`` import so the logic can be unit-tested
without MkDocs installed. The thin MkDocs plugin wrapper lives in
``mdoctest.mkdocs_plugin`` and delegates here.
"""
from __future__ import annotations

import glob
import os
from dataclasses import dataclass, field
from typing import List, Optional

from .cli import _walk_dir
from .core import Options, process_file


@dataclass
class DocsReport:
    """Aggregate result of checking a docs tree."""

    files: int = 0
    checked: int = 0
    failures: int = 0
    errors: int = 0
    messages: List[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.failures == 0 and self.errors == 0


def collect_markdown(docs_dir: str, patterns: Optional[List[str]] = None) -> List[str]:
    """Markdown files to check under ``docs_dir``.

    With no ``patterns`` every Markdown file under ``docs_dir`` is returned
    (dot-dirs skipped). ``patterns`` are globs resolved relative to
    ``docs_dir`` (``**`` recursion enabled); a pattern that resolves to a
    directory is walked.
    """
    if not patterns:
        return _walk_dir(docs_dir)
    out: List[str] = []
    for pat in patterns:
        full = pat if os.path.isabs(pat) else os.path.join(docs_dir, pat)
        for hit in sorted(glob.glob(full, recursive=True)):
            if os.path.isdir(hit):
                out.extend(_walk_dir(hit))
            else:
                out.append(hit)
    # de-dup, keep sorted & stable
    return sorted(dict.fromkeys(out))


def check_docs(
    docs_dir: str,
    patterns: Optional[List[str]] = None,
    opts: Optional[Options] = None,
) -> DocsReport:
    """Run mdoctest (check-only, never fixing) over a docs tree."""
    opts = opts or Options()
    report = DocsReport()
    for path in collect_markdown(docs_dir, patterns):
        fr = process_file(path, opts, fix=False)
        report.files += 1
        rel = os.path.relpath(path, docs_dir)
        if fr.error:
            report.errors += 1
            report.messages.append("{0}: {1}".format(rel, fr.error))
            continue
        report.checked += fr.checked
        for b in fr.blocks:
            if not b.ok and not b.skipped_reason:
                report.failures += 1
                detail = b.message or "output does not match"
                report.messages.append(
                    "{0}:{1}: {2}".format(rel, b.open_line, detail)
                )
    return report
