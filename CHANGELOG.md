# Changelog

All notable changes to mdoctest are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/) and the project uses
[semantic versioning](https://semver.org/).

## [0.9.0] - 2026-09-22

### Added
- **Sphinx extension.** `pip install "mdoctest[sphinx]"` and add
  `"mdoctest.sphinx_ext"` to `extensions` in your `conf.py` to verify every
  runnable console/code block in your Markdown (MyST) docs on each
  `sphinx-build`. Drift fails the build with a clean, non-zero exit and a
  `file:line` pointer (or warns, with `mdoctest_strict = False`). Settings:
  `mdoctest_enabled`, `mdoctest_strict`, `mdoctest_files` (globs relative to the
  source dir), `mdoctest_shell`, `mdoctest_prompt`, `mdoctest_timeout`. `.rst`
  sources are intentionally left to Sphinx's own `sphinx.ext.doctest`. The
  checker logic lives in a sphinx-free helper (`mdoctest.sphinx_check`) so it is
  unit-tested; core mdoctest keeps zero runtime dependencies. Added the
  `Framework :: Sphinx` classifiers.

## [0.8.0] - 2026-09-21

### Added
- **MkDocs plugin.** `pip install "mdoctest[mkdocs]"` and add `mdoctest` to the
  `plugins:` list in `mkdocs.yml` to verify every runnable code/console block in
  your docs on each `mkdocs build`/`serve`. Drift fails the build (or warns, with
  `strict: false`) and points at the offending file and line. Options: `enabled`,
  `strict`, `files` (globs relative to `docs_dir`), `shell`, `prompt`, `timeout`.
  The plugin logic lives in a mkdocs-free helper (`mdoctest.mkdocs_check`) so it
  is fully unit-tested; core mdoctest keeps zero runtime dependencies.

## [0.7.0] - 2026-09-19

### Added
- **Directory arguments.** `mdoctest docs/` (or `mdoctest .`) now walks a
  directory recursively for `*.md`/`*.markdown`/`*.mdown`/`*.mkd` files instead
  of erroring with "Is a directory". Dot-directories (`.git`, `.venv`, …) are
  skipped, and results are sorted for stable output. Globs that resolve to a
  directory recurse the same way. This is the natural invocation for docs-as-code
  projects that keep many Markdown files under a docs tree.

## [0.6.0] - 2026-09-18

### Added
- **`mdoctest --init`.** One command scaffolds a pre-commit hook
  (`.pre-commit-config.yaml`) *and* a GitHub Actions workflow
  (`.github/workflows/mdoctest.yml`) so a project checks its own docs on every
  commit and every pull request. Idempotent and non-destructive: an existing
  `.pre-commit-config.yaml` gets the mdoctest hook appended (never duplicated),
  and an existing workflow is left untouched. Lowers adoption to a single step.

## [0.5.1] - 2026-09-17

### Added
- **Block-attached setup form.** An empty `<!-- mdoctest: setup -->` comment
  placed directly above a fenced code block now adopts that block as its fixture
  script, mirroring how `run`/`skip` directives attach to the following block.
  Previously an empty setup comment silently did nothing and the following block
  was ignored, so `$ cat data.txt` examples failed with confusing "No such file"
  errors — a real first-run footgun. The inline `<!-- mdoctest: setup ... -->`
  form is unchanged. The adopted block is treated as invisible plumbing: it is
  never run or checked as an example itself.

## [0.5.0] - 2026-09-17

### Added
- **Invisible setup / fixture blocks.** A `<!-- mdoctest: setup ... -->` comment
  holds a shell script that runs before the session blocks after it — the
  natural way to create the files and environment that a real README's examples
  assume already exist (`$ cat data.csv`, `$ ./run input.txt`, …). Because it's
  an HTML comment it is hidden in the rendered Markdown, so it never clutters
  your docs. When a file uses setup, its sessions run in a fresh throwaway
  directory that is deleted afterward, so fixtures never touch your repo or
  working tree. Supports multi-line scripts and here-documents; progressive
  setups apply only to the blocks that follow them.

## [0.4.1] - 2026-09-17

### Fixed
- **Here-documents in console sessions.** A `$` command that opens a here-doc
  (`cat <<END` … `END`) had its body misread as expected output and the command
  sent to the shell alone, so the shell blocked on stdin waiting for the
  delimiter and the block hung to a timeout. The here-doc body and terminator
  are now kept as part of the command (including body lines that start with the
  prompt, `<<-`, and quoted delimiters), and `--fix` rewrites such blocks
  without corrupting the here-doc. This is a common README pattern.

## [0.4.0] - 2026-09-17

### Added
- **GitHub Actions inline annotations.** When a doc example drifts in CI,
  mdoctest now emits an `::error` workflow command pointing at the exact fenced
  block, so the failure appears as an inline annotation on the pull request's
  *Files changed* tab (not just in the log). Automatic when `GITHUB_ACTIONS` is
  set; controllable everywhere with `--annotate auto|always|never`. `--fix`
  never annotates.

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
