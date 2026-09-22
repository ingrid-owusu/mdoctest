"""Sphinx extension: verify the code & console examples in your Markdown docs.

Enable it in your ``conf.py``::

    extensions = [
        "myst_parser",   # so Sphinx reads Markdown sources
        "mdoctest.sphinx_ext",
    ]

Now every ``sphinx-build`` (and ``make html``) runs mdoctest over the project's
Markdown (MyST) sources: console sessions, ``pycon`` ``>>>`` blocks and
language-tagged ``run`` blocks are executed and their output is checked against
what the docs claim. If anything drifted, the build fails with a pointer to the
offending file and line — your published docs can never show output that no
longer matches reality.

Configuration (all optional, set in ``conf.py``)::

    mdoctest_enabled = True     # master switch
    mdoctest_strict = True      # False => warn instead of failing the build
    mdoctest_files = []         # globs relative to the source dir; [] => all *.md
    mdoctest_shell = "bash"     # shell for console-session blocks
    mdoctest_prompt = "$ "      # console prompt to recognise
    mdoctest_timeout = 30.0     # per-block timeout, seconds

This module imports ``sphinx`` and is only loaded when a project lists it in
``extensions``; core mdoctest never imports it. Install the extra with
``pip install "mdoctest[sphinx]"``. ``.rst`` sources are intentionally left to
Sphinx's own ``sphinx.ext.doctest``.
"""
from __future__ import annotations

from sphinx.util import logging as sphinx_logging

from . import __version__
from .core import Options
from .sphinx_check import check_sphinx_docs, summarize

logger = sphinx_logging.getLogger(__name__)


def _run(app):
    cfg = app.config
    if not cfg.mdoctest_enabled:
        logger.info("[mdoctest] disabled, skipping doc checks")
        return

    opts = Options(
        shell=cfg.mdoctest_shell,
        prompt=cfg.mdoctest_prompt,
        timeout=float(cfg.mdoctest_timeout),
    )
    report = check_sphinx_docs(app.srcdir, cfg.mdoctest_files, opts)

    problem = summarize(report)
    if problem is None:
        logger.info(
            "[mdoctest] %d block(s) checked across %d file(s), all OK",
            report.checked,
            report.files,
        )
        return

    if cfg.mdoctest_strict:
        # Fail the build with a clean summary and a non-zero exit code, the way
        # ``sphinx.ext.doctest`` does — no misleading "report to Sphinx" crash.
        logger.error(problem)
        app.statuscode = 1
    else:
        logger.warning(problem)


def _on_build_finished(app, exception):
    # Don't pile on if the build already failed for another reason.
    if exception is None:
        _run(app)


def setup(app):
    app.add_config_value("mdoctest_enabled", True, "env")
    app.add_config_value("mdoctest_strict", True, "env")
    app.add_config_value("mdoctest_files", [], "env")
    app.add_config_value("mdoctest_shell", "bash", "env")
    app.add_config_value("mdoctest_prompt", "$ ", "env")
    app.add_config_value("mdoctest_timeout", 30.0, "env")
    app.connect("build-finished", _on_build_finished)
    return {
        "version": __version__,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
