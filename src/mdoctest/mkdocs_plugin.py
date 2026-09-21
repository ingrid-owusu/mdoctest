"""MkDocs plugin: verify the code & console examples in your docs on build.

Enable it in ``mkdocs.yml``::

    plugins:
      - search
      - mdoctest

Now every ``mkdocs build`` (and ``mkdocs serve``) runs mdoctest over your
Markdown sources: console sessions and runnable code blocks are executed and
their output is checked against what the docs claim. If anything drifted, the
build fails with a pointer to the offending file and line — your published
docs can never show output that no longer matches reality.

Options (all optional)::

    plugins:
      - mdoctest:
          enabled: true      # master switch (e.g. `!ENV [MDOCTEST, true]`)
          strict: true       # false => warn instead of failing the build
          files: []           # globs (relative to docs_dir); empty => all *.md
          shell: bash         # shell for console-session blocks
          prompt: "$ "        # console prompt to recognise
          timeout: 30.0       # per-block timeout, seconds

This module imports ``mkdocs`` and is only loaded by MkDocs itself via the
``mkdocs.plugins`` entry point; core mdoctest never imports it. Install the
extra with ``pip install "mdoctest[mkdocs]"``.
"""
from __future__ import annotations

from mkdocs.config import config_options
from mkdocs.exceptions import PluginError
from mkdocs.plugins import BasePlugin, get_plugin_logger

from .core import Options
from .mkdocs_check import check_docs

log = get_plugin_logger(__name__)


class MdoctestPlugin(BasePlugin):
    config_scheme = (
        ("enabled", config_options.Type(bool, default=True)),
        ("strict", config_options.Type(bool, default=True)),
        ("files", config_options.Type(list, default=[])),
        ("shell", config_options.Type(str, default="bash")),
        ("prompt", config_options.Type(str, default="$ ")),
        ("timeout", config_options.Type(float, default=30.0)),
    )

    def on_pre_build(self, *, config):
        if not self.config["enabled"]:
            log.info("mdoctest: disabled, skipping doc checks")
            return

        opts = Options(
            shell=self.config["shell"],
            prompt=self.config["prompt"],
            timeout=float(self.config["timeout"]),
        )
        report = check_docs(config["docs_dir"], self.config["files"], opts)

        if report.ok:
            log.info(
                "mdoctest: %d block(s) checked across %d file(s), all OK",
                report.checked,
                report.files,
            )
            return

        summary = "mdoctest found {0} problem(s) in your docs:\n  - {1}".format(
            report.failures + report.errors,
            "\n  - ".join(report.messages),
        )
        if self.config["strict"]:
            raise PluginError(summary)
        log.warning(summary)
