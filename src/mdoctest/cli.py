"""Command-line interface for mdoctest."""
from __future__ import annotations

import argparse
import glob
import os
import sys
from typing import List

from . import __version__
from .core import Options, process_file, render_diff
from .session import SessionTimeout


# Markdown file extensions discovered when a directory is given.
_MD_EXTS = (".md", ".markdown", ".mdown", ".mkd")


def _walk_dir(root: str) -> List[str]:
    """Return every Markdown file under `root`, sorted, skipping dot-dirs
    (e.g. .git, .venv) so `mdoctest docs/` (or `mdoctest .`) Just Works."""
    found: List[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if not d.startswith("."))
        for name in filenames:
            if name.lower().endswith(_MD_EXTS):
                found.append(os.path.join(dirpath, name))
    return sorted(found)


def _expand(paths: List[str]) -> List[str]:
    out: List[str] = []
    for p in paths:
        if any(ch in p for ch in "*?["):
            for hit in sorted(glob.glob(p, recursive=True)):
                out.extend(_walk_dir(hit) if os.path.isdir(hit) else [hit])
        elif os.path.isdir(p):
            out.extend(_walk_dir(p))
        else:
            out.append(p)
    return out


def _want_color(choice: str) -> bool:
    if choice == "always":
        return True
    if choice == "never":
        return False
    return sys.stdout.isatty() and os.environ.get("NO_COLOR") is None


def _want_annotations(choice: str) -> bool:
    if choice == "always":
        return True
    if choice == "never":
        return False
    return os.environ.get("GITHUB_ACTIONS") == "true"


def _gh_escape_data(s: str) -> str:
    return s.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def _gh_escape_prop(s: str) -> str:
    return (_gh_escape_data(s)
            .replace(":", "%3A").replace(",", "%2C"))


def _emit_annotation(path: str, line: int, message: str) -> None:
    """Emit a GitHub Actions error workflow command so the failure shows up as
    an inline annotation on the PR diff (not just buried in the log)."""
    print("::error file=%s,line=%d,title=mdoctest::%s" % (
        _gh_escape_prop(path), line, _gh_escape_data(message)))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="mdoctest",
        description="doctest for Markdown, in any language: run the code and "
                    "console sessions in your docs and verify their output "
                    "still matches. --fix updates them for you.",
    )
    p.add_argument("paths", nargs="*", default=None,
                   help="Markdown files or globs (default: README.md)")
    p.add_argument("--fix", action="store_true",
                   help="rewrite expected output in place to match reality")
    p.add_argument("--init", action="store_true",
                   help="scaffold a pre-commit hook + GitHub Actions workflow so "
                        "this repo checks its own docs, then exit")
    p.add_argument("--shell", default="bash", help="shell for sessions (default: bash)")
    p.add_argument("--prompt", default="$ ", help="command prompt (default: '$ ')")
    p.add_argument("--cont", default="> ", help="continuation prompt (default: '> ')")
    p.add_argument("--timeout", type=float, default=30.0,
                   help="per-command timeout in seconds (default: 30)")
    p.add_argument("--cwd", default=None,
                   help="working directory (default: the Markdown file's dir)")
    p.add_argument("--color", choices=["auto", "always", "never"], default="auto")
    p.add_argument("--annotate", choices=["auto", "always", "never"], default="auto",
                   help="emit GitHub Actions ::error annotations for failures "
                        "(auto: on when GITHUB_ACTIONS=true)")
    p.add_argument("-q", "--quiet", action="store_true", help="only print failures")
    p.add_argument("-V", "--version", action="version",
                   version="mdoctest %s" % __version__)
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    if args.init:
        from .scaffold import init
        return init()
    color = _want_color(args.color)
    annotate = _want_annotations(args.annotate) and not args.fix
    paths = _expand(args.paths) if args.paths else (
        ["README.md"] if os.path.exists("README.md") else [])
    if not paths:
        sys.stderr.write("mdoctest: no Markdown files given and README.md not found\n")
        return 2

    opts = Options(shell=args.shell, prompt=args.prompt, cont=args.cont,
                   timeout=args.timeout, cwd=args.cwd)

    total_checked = 0
    total_failures = 0
    total_fixed = 0

    def c(code, s):
        return "\033[%sm%s\033[0m" % (code, s) if color else s

    for path in paths:
        try:
            fr = process_file(path, opts, fix=args.fix)
        except SessionTimeout as e:
            sys.stderr.write("%s: %s\n" % (path, e))
            if annotate:
                _emit_annotation(path, 1, "timed out: %s" % e)
            total_failures += 1
            continue
        if fr.error:
            sys.stderr.write("%s: %s\n" % (path, fr.error))
            if annotate:
                _emit_annotation(path, 1, str(fr.error))
            total_failures += 1
            continue

        total_checked += fr.checked
        total_failures += fr.failures
        total_fixed += fr.fixed

        for b in fr.blocks:
            if b.skipped_reason:
                continue
            loc = "%s:%d" % (path, b.open_line)
            if b.ok:
                if not args.quiet and not args.fix:
                    print("%s  %s (%s)" % (c("32", "PASS"), loc, b.kind))
                continue
            print("%s  %s (%s)" % (c("31", "FAIL"), loc, b.kind))
            if b.kind in ("session", "pydoctest"):
                prompt = ">>>" if b.kind == "pydoctest" else "$"
                failed_cmd = None
                for cr in b.cmds:
                    if cr.ok:
                        continue
                    if failed_cmd is None:
                        failed_cmd = cr.command
                    print("    %s %s" % (c("36", prompt), cr.command.replace("\n", "\n      ")))
                    diff = render_diff(cr.expected, cr.actual, color=color)
                    for dl in diff.split("\n"):
                        print("      " + dl)
                if annotate:
                    cmd1 = (failed_cmd or "").split("\n")[0]
                    _emit_annotation(
                        path, b.open_line,
                        "output no longer matches for `%s` — run `mdoctest --fix`"
                        % cmd1)
            elif b.message:
                for dl in b.message.split("\n"):
                    print("      " + dl)
                if annotate:
                    _emit_annotation(path, b.open_line,
                                     b.message.split("\n")[0])

    if args.fix:
        print("%s  fixed %d block(s) across %d file(s)"
              % (c("32", "FIXED"), total_fixed, len(paths)))
        return 0

    summary = "checked %d block(s), %d failed" % (total_checked, total_failures)
    print(("%s  %s" % (c("31" if total_failures else "32",
                          "FAIL" if total_failures else "OK"), summary)))
    return 1 if total_failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
