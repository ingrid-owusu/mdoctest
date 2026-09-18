"""Tests for `mdoctest --init` scaffolding."""
import os

from mdoctest import __version__
from mdoctest.cli import main
from mdoctest.scaffold import PRECOMMIT_FILE, WORKFLOW_FILE, init


def _run_init(tmp_path):
    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        lines = []
        rc = init(emit=lines.append)
        return rc, "\n".join(lines)
    finally:
        os.chdir(cwd)


def test_init_creates_both_files(tmp_path):
    rc, out = _run_init(tmp_path)
    assert rc == 0
    pc = tmp_path / PRECOMMIT_FILE
    wf = tmp_path / WORKFLOW_FILE
    assert pc.exists() and wf.exists()
    text = pc.read_text()
    assert "id: mdoctest" in text
    assert ("rev: v%s" % __version__) in text
    assert "repos:" in text
    wtext = wf.read_text()
    assert "ingrid-owusu/mdoctest@v1" in wtext
    assert "files: README.md" in wtext
    assert "created" in out


def test_init_is_idempotent(tmp_path):
    _run_init(tmp_path)
    pc_before = (tmp_path / PRECOMMIT_FILE).read_text()
    rc, out = _run_init(tmp_path)
    assert rc == 0
    assert (tmp_path / PRECOMMIT_FILE).read_text() == pc_before
    assert "already configured" in out
    assert "nothing to do" in out


def test_init_appends_to_existing_precommit(tmp_path):
    pc = tmp_path / PRECOMMIT_FILE
    pc.write_text(
        "repos:\n"
        "  - repo: https://github.com/pre-commit/pre-commit-hooks\n"
        "    rev: v4.5.0\n"
        "    hooks:\n"
        "      - id: end-of-file-fixer\n"
    )
    rc, out = _run_init(tmp_path)
    assert rc == 0
    text = pc.read_text()
    # existing hook preserved, mdoctest appended once
    assert "end-of-file-fixer" in text
    assert text.count("id: mdoctest") == 1
    assert "updated" in out


def test_init_does_not_clobber_existing_workflow(tmp_path):
    wf = tmp_path / WORKFLOW_FILE
    wf.parent.mkdir(parents=True)
    wf.write_text("name: my custom workflow\n")
    rc, out = _run_init(tmp_path)
    assert rc == 0
    assert wf.read_text() == "name: my custom workflow\n"
    assert "already configured" in out


def test_init_via_cli(tmp_path):
    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        rc = main(["--init"])
    finally:
        os.chdir(cwd)
    assert rc == 0
    assert (tmp_path / PRECOMMIT_FILE).exists()
