"""Tests for path expansion: directory recursion + globs (cli._expand)."""
import os

from mdoctest.cli import _expand, _walk_dir, main


def _mk(tmp_path, rel, body="# t\n\n```console\n$ echo hi\nhi\n```\n"):
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body)
    return p


def test_directory_recurses_for_markdown(tmp_path):
    _mk(tmp_path, "a.md")
    _mk(tmp_path, "docs/b.markdown")
    _mk(tmp_path, "docs/deep/c.md")
    got = _expand([str(tmp_path)])
    assert got == sorted(got)
    names = {os.path.basename(p) for p in got}
    assert names == {"a.md", "b.markdown", "c.md"}


def test_directory_skips_dot_dirs(tmp_path):
    _mk(tmp_path, "keep.md")
    _mk(tmp_path, ".git/nope.md")
    _mk(tmp_path, ".venv/pkg/nope.md")
    got = [os.path.basename(p) for p in _walk_dir(str(tmp_path))]
    assert got == ["keep.md"]


def test_directory_ignores_non_markdown(tmp_path):
    _mk(tmp_path, "a.md")
    (tmp_path / "notes.txt").write_text("hi")
    (tmp_path / "script.py").write_text("print(1)")
    got = [os.path.basename(p) for p in _expand([str(tmp_path)])]
    assert got == ["a.md"]


def test_plain_file_unchanged(tmp_path):
    f = _mk(tmp_path, "only.md")
    assert _expand([str(f)]) == [str(f)]


def test_glob_matching_a_dir_recurses(tmp_path):
    _mk(tmp_path, "docs/a.md")
    _mk(tmp_path, "docs/nested/b.md")
    pattern = os.path.join(str(tmp_path), "*")
    got = {os.path.basename(p) for p in _expand([pattern])}
    assert got == {"a.md", "b.md"}


def test_main_runs_directory(tmp_path, capsys):
    _mk(tmp_path, "a.md")
    _mk(tmp_path, "sub/b.md")
    rc = main([str(tmp_path)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "checked 2 block(s)" in out
