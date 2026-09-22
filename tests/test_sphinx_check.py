"""Tests for the sphinx-free helper (mdoctest.sphinx_check).

These do NOT import sphinx; they exercise the real logic the Sphinx extension
delegates to, so they run in the normal test environment.
"""
import os

from mdoctest.sphinx_check import check_sphinx_docs, summarize
from mdoctest.mkdocs_check import DocsReport

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

RST = """Title
=====

.. code-block:: console

   $ echo hello
   goodbye
"""


def _write(d, name, text):
    p = os.path.join(d, name)
    parent = os.path.dirname(p)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(text)
    return p


def test_all_passing(tmp_path):
    d = str(tmp_path)
    _write(d, "index.md", PASS_MD)
    _write(d, "guide/api.md", PASS_MD)
    report = check_sphinx_docs(d)
    assert isinstance(report, DocsReport)
    assert report.ok
    assert report.files == 2
    assert summarize(report) is None


def test_failure_reported(tmp_path):
    d = str(tmp_path)
    _write(d, "index.md", FAIL_MD)
    report = check_sphinx_docs(d)
    assert not report.ok
    assert report.failures == 1
    msg = summarize(report)
    assert msg is not None
    assert "index.md" in msg
    assert "problem" in msg


def test_rst_sources_ignored(tmp_path):
    # mdoctest is Markdown-oriented; .rst is left to sphinx.ext.doctest.
    d = str(tmp_path)
    _write(d, "broken.rst", RST)
    report = check_sphinx_docs(d)
    assert report.ok
    assert report.files == 0


def test_patterns_scope_files(tmp_path):
    d = str(tmp_path)
    _write(d, "index.md", PASS_MD)
    _write(d, "changelog.md", FAIL_MD)
    report = check_sphinx_docs(d, patterns=["index.md"])
    assert report.ok
    assert report.files == 1
