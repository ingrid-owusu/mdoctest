# Changelog

All notable changes to mdoctest are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/) and the project uses
[semantic versioning](https://semver.org/).

## [0.3.1] - 2026-09-17

### Fixed
- **Backslash line-continuations in console sessions.** A shell command wrapped
  across lines with a trailing `\` (with the continuation lines just indented,
  as most READMEs write long piped commands) is now joined into a single
  command instead of being sent half-finished — which previously left the shell
  waiting for input and stalled the block until the timeout.

## [0.3.0] - 2026-09-17

### Added
- **Any language, for real.** A `run` directive now accepts `cmd="..."` to run
  a block with an arbitrary command (e.g. `<!-- mdoctest: run cmd="go run"
  ext=.go -->`), and `ext=` to control the temp-file extension. Syntax-check,
  compile, or execute blocks in Go, Rust, TypeScript, SQL — anything — with no
  plugins and no config file.
- More built-in interpreters for `run` blocks: `php`, `lua`, `go`, `r`, `deno`,
  plus `perl`. The skip message for an unknown language now points at `cmd=`.

## [0.2.0] - 2026-09-17

### Added
- **Python `>>>` doctest blocks run natively.** A block tagged `pycon` (or a
  `python`/untagged block whose first line is a `>>>` prompt) is executed like
  Python's own `doctest`: each statement runs in a shared namespace and its
  output is checked. No `run` directive needed.
- Exceptions match `doctest`-style — elide the traceback body with `...`.
- `--fix` rewrites expected output for `pycon` blocks too, preserving prose
  between examples.

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
