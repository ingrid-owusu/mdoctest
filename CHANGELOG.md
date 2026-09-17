# Changelog

All notable changes to mdoctest are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/) and the project uses
[semantic versioning](https://semver.org/).

## [0.1.0] - 2026-09-17

Initial release.

### Added
- Verify `console`/`shell-session` blocks in Markdown: each `$` command runs in
  a persistent shell (state carries across the session) and its combined
  stdout+stderr is compared to the documented output.
- `bash`/`sh` blocks whose first line is a `$ ` prompt are treated as sessions.
- `--fix`: re-run and rewrite expected output in place, preserving prose.
- `...` wildcard matching (inline and whole-line) for non-deterministic output.
- `<!-- mdoctest: run -->` to execute a code block in its language and assert
  exit 0; `<!-- mdoctest: skip -->` to leave a block alone.
- Zero dependencies, stdlib only, Python 3.8+.
- Ships as a pre-commit hook and a GitHub Action.
