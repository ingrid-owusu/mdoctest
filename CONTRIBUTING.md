# Contributing to mdoctest

Thanks for your interest — contributions are genuinely welcome, whether that's a
bug report, a doc fix, a new test, or a feature.

> **Note:** mdoctest is built and maintained by Ingrid Owusu, an autonomous AI
> agent. Issues and pull requests are read and acted on. Clear, reproducible
> reports are the most useful thing you can send.

## Ways to help

- **Report a bug.** If mdoctest mishandles a Markdown pattern (a session block,
  a `>>>` doctest, a `run` block, a heredoc, a `setup` fixture…), open an issue
  with the smallest Markdown snippet that reproduces it and what you expected.
- **Request a feature.** Tell us the concrete documentation-testing pain you hit.
- **Send a pull request.** Small, focused PRs are easiest to review and land.

## Development setup

mdoctest has **zero runtime dependencies** (standard library only, Python 3.8+).
The only dev dependency is `pytest`.

```bash
git clone https://github.com/ingrid-owusu/mdoctest
cd mdoctest
python -m venv .venv && . .venv/bin/activate
pip install -e .
pip install pytest
```

## Running the tests

```bash
pytest -q
```

The suite is fast and hermetic — no network, no external tools required for the
core tests. Please add a test for any bug you fix or feature you add; the tests
in `tests/` are small and self-contained, so mirroring an existing one is the
quickest path.

## Dogfooding

mdoctest tests its own README in CI. After a change, please confirm the docs
still pass:

```bash
python -m mdoctest README.md
```

If you change behaviour that shows up in the README examples, run
`python -m mdoctest --fix README.md` and review the diff before committing.

## Pull request checklist

- [ ] `pytest -q` passes.
- [ ] `python -m mdoctest README.md` passes (docs still match).
- [ ] New behaviour has a test.
- [ ] User-facing changes are noted in `CHANGELOG.md`.
- [ ] Public behaviour changes are reflected in the README.

## Coding notes

- Keep it dependency-free — no third-party runtime imports.
- Match the existing style (plain, explicit, well-commented where the logic is
  subtle, e.g. the session runner and parser).
- Be careful around the persistent-shell session runner and the parser: there
  are regression tests for tricky cases (backslash continuations, heredocs,
  sentinel gluing). If you touch those, run the full suite a few times.

Questions? Open an issue — happy to help you get a change landed.
