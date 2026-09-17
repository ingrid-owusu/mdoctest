from mdoctest.cli import (
    _gh_escape_data,
    _gh_escape_prop,
    _want_annotations,
    main,
)


def _write(tmp_path, text):
    p = tmp_path / "doc.md"
    p.write_text(text, encoding="utf-8")
    return str(p)


def test_escape_data():
    assert _gh_escape_data("a%b\nc") == "a%25b%0Ac"


def test_escape_prop():
    assert _gh_escape_prop("a:b,c") == "a%3Ab%2Cc"


def test_want_annotations(monkeypatch):
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    assert _want_annotations("auto") is False
    assert _want_annotations("always") is True
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    assert _want_annotations("auto") is True
    assert _want_annotations("never") is False


def test_annotation_emitted_on_failure(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    path = _write(tmp_path, "# Doc\n\n```console\n$ echo HELLO\nHELXO\n```\n")
    rc = main([path])
    out = capsys.readouterr().out
    assert rc == 1
    assert "::error file=%s,line=3,title=mdoctest::" % path in out
    assert "run `mdoctest --fix`" in out


def test_no_annotation_when_disabled(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    path = _write(tmp_path, "```console\n$ echo HELLO\nHELXO\n```\n")
    main(["--annotate", "never", path])
    assert "::error" not in capsys.readouterr().out


def test_no_annotation_on_pass(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    path = _write(tmp_path, "```console\n$ echo hi\nhi\n```\n")
    rc = main([path])
    assert rc == 0
    assert "::error" not in capsys.readouterr().out
