import os

from mdoctest.core import Options, process_file

OPTS = Options()


def _write(tmp_path, text):
    p = tmp_path / "doc.md"
    p.write_text(text, encoding="utf-8")
    return str(p)


def test_passing_session(tmp_path):
    md = "```console\n$ echo hi\nhi\n```\n"
    fr = process_file(_write(tmp_path, md), OPTS)
    assert fr.failures == 0 and fr.checked == 1


def test_failing_session(tmp_path):
    md = "```console\n$ echo hi\nBYE\n```\n"
    fr = process_file(_write(tmp_path, md), OPTS)
    assert fr.failures == 1


def test_fix_rewrites_output(tmp_path):
    path = _write(tmp_path, "```console\n$ echo hi\nWRONG\n```\n")
    fr = process_file(path, OPTS, fix=True)
    assert fr.fixed == 1
    assert "hi" in open(path).read()
    # now clean
    fr2 = process_file(path, OPTS)
    assert fr2.failures == 0


def test_bash_block_with_prompt_is_a_session(tmp_path):
    md = "```bash\n$ echo yo\nyo\n```\n"
    fr = process_file(_write(tmp_path, md), OPTS)
    assert fr.checked == 1 and fr.failures == 0


def test_plain_bash_block_without_prompt_ignored(tmp_path):
    md = "```bash\necho this is illustrative\n```\n"
    fr = process_file(_write(tmp_path, md), OPTS)
    assert fr.checked == 0


def test_skip_directive(tmp_path):
    md = "<!-- mdoctest: skip -->\n```console\n$ rm -rf /\n```\n"
    fr = process_file(_write(tmp_path, md), OPTS)
    assert fr.checked == 0 and fr.failures == 0


def test_run_directive_python_pass(tmp_path):
    md = "<!-- mdoctest: run -->\n```python\nassert 1 + 1 == 2\n```\n"
    fr = process_file(_write(tmp_path, md), OPTS)
    assert fr.failures == 0 and fr.checked == 1


def test_run_directive_python_fail(tmp_path):
    md = "<!-- mdoctest: run -->\n```python\nraise SystemExit(3)\n```\n"
    fr = process_file(_write(tmp_path, md), OPTS)
    assert fr.failures == 1


def test_state_persists_within_a_block(tmp_path):
    md = "```console\n$ cd /tmp\n$ pwd\n/tmp\n```\n"
    fr = process_file(_write(tmp_path, md), OPTS)
    assert fr.failures == 0


def test_ellipsis_in_expected(tmp_path):
    md = "```console\n$ echo build-12345\nbuild-...\n```\n"
    fr = process_file(_write(tmp_path, md), OPTS)
    assert fr.failures == 0


def test_fix_preserves_surrounding_text(tmp_path):
    md = "# Title\n\ntext before\n\n```console\n$ echo new\nold\n```\n\ntext after\n"
    path = _write(tmp_path, md)
    process_file(path, OPTS, fix=True)
    out = open(path).read()
    assert "text before" in out and "text after" in out and "# Title" in out
    assert out.endswith("\n")


def test_run_cmd_override_any_language(tmp_path):
    # A block in an arbitrary "language" runs via an explicit cmd override.
    md = ('<!-- mdoctest: run cmd="python3" ext=.py -->\n'
          '```text\nprint("ok")\n```\n')
    fr = process_file(_write(tmp_path, md), OPTS)
    assert fr.checked == 1 and fr.failures == 0


def test_run_cmd_override_nonzero_fails(tmp_path):
    md = ('<!-- mdoctest: run cmd="python3" ext=.py -->\n'
          '```text\nimport sys; sys.exit(3)\n```\n')
    fr = process_file(_write(tmp_path, md), OPTS)
    assert fr.failures == 1


def test_run_unknown_lang_without_cmd_is_skipped(tmp_path):
    # No built-in interpreter and no cmd override -> skipped, not failed.
    md = "<!-- mdoctest: run -->\n```haskell\nmain = return ()\n```\n"
    fr = process_file(_write(tmp_path, md), OPTS)
    assert fr.failures == 0
