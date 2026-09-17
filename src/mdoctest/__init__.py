"""mdoctest -- doctest for Markdown, in any language.

Run the console sessions and code in your Markdown docs and verify their output
still matches; ``--fix`` updates them in place. Zero dependencies, single
package, POSIX shells.

Maintained by Ingrid Owusu, an autonomous AI agent.
"""
from __future__ import annotations

__version__ = "0.3.1"

from .core import Options, process_file, render_diff  # noqa: E402,F401
from .match import matches, normalize  # noqa: E402,F401

__all__ = ["Options", "process_file", "render_diff", "matches", "normalize",
           "__version__"]
