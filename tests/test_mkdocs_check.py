"""Tests for the mkdocs-free doc-tree checker (mdoctest.mkdocs_check).

These do NOT import mkdocs; they exercise the real logic the MkDocs plugin
delegates to, so they run in the normal test environment.
"""
import os

from mdoctest.mkdocs_check import DocsReport, check_docs, collect_markdown

PASS_MD = """# Ok

```console
$ echo hello
hello
```
"""

FAIL_MD = """# Drift

```console
$ echo hello
goodbye
```
"""


def _write(d, name, text):
    p = os.path.join(d, name)
    os.makedirs(os.path.dirname(p), exist_ok=True) if os.path.dirname(p) else None
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(text)
    return p


def test_all_passing(tmp_path):
    d = str(tmp_path)
    _write(d, "index.md", PASS_MD)
    _write(d, "guide.md", PASS_MD)
    report = check_docs(d)
    assert isinstance(report, DocsReport)
    assert report.files == 2
    assert report.failures == 0
    assert report.errors == 0
    assert report.ok
    assert report.checked >= 2


def test_detects_drift(tmp_path):
    d = str(tmp_path)
    _write(d, "index.md", PASS_MD)
    _write(d, "bad.md", FAIL_MD)
    report = check_docs(d)
    assert report.files == 2
    assert report.failures == 1
    assert not report.ok
    assert any("bad.md" in m for m in report.messages)


def test_dot_dirs_skipped(tmp_path):
    d = str(tmp_path)
    _write(d, "index.md", PASS_MD)
    _write(d, os.path.join(".ignored", "bad.md"), FAIL_MD)
    report = check_docs(d)
    # the file under a dot-dir must not be picked up
    assert report.files == 1
    assert report.ok


def test_files_glob_restricts_scope(tmp_path):
    d = str(tmp_path)
    _write(d, "index.md", PASS_MD)
    _write(d, "bad.md", FAIL_MD)
    # only check index.md -> the drift in bad.md is ignored
    report = check_docs(d, patterns=["index.md"])
    assert report.files == 1
    assert report.ok


def test_collect_markdown_all(tmp_path):
    d = str(tmp_path)
    _write(d, "a.md", PASS_MD)
    _write(d, os.path.join("sub", "b.md"), PASS_MD)
    _write(d, "notes.txt", "not markdown")
    found = collect_markdown(d)
    names = sorted(os.path.relpath(p, d) for p in found)
    assert names == ["a.md", os.path.join("sub", "b.md")]
