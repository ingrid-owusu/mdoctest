import os

from mdoctest.core import Options, process_file
from mdoctest.pydoctest import check, fix, is_pydoctest

OPTS = Options()


def _write(tmp_path, text):
    p = tmp_path / "doc.md"
    p.write_text(text, encoding="utf-8")
    return str(p)


def test_detection():
    assert is_pydoctest("pycon", ">>> 1\n1\n")
    assert is_pydoctest("python", ">>> 1\n1\n")
    assert is_pydoctest("", ">>> 1\n1\n")
    # a plain python block without a prompt is *not* a doctest block
    assert not is_pydoctest("python", "import os\nprint(os)\n")
    assert not is_pydoctest("json", '{"a": 1}\n')


def test_passing_pycon(tmp_path):
    md = "```pycon\n>>> 2 + 3\n5\n```\n"
    fr = process_file(_write(tmp_path, md), OPTS)
    assert fr.failures == 0 and fr.checked == 1
    assert fr.blocks[0].kind == "pydoctest"


def test_failing_pycon(tmp_path):
    md = "```pycon\n>>> 2 + 3\n6\n```\n"
    fr = process_file(_write(tmp_path, md), OPTS)
    assert fr.failures == 1


def test_shared_namespace(tmp_path):
    md = "```pycon\n>>> x = 21\n>>> x * 2\n42\n```\n"
    fr = process_file(_write(tmp_path, md), OPTS)
    assert fr.failures == 0


def test_multiline_statement(tmp_path):
    md = "```pycon\n>>> for i in range(2):\n...     print(i)\n0\n1\n```\n"
    fr = process_file(_write(tmp_path, md), OPTS)
    assert fr.failures == 0


def test_untagged_prompt_block(tmp_path):
    md = "```\n>>> 6 * 7\n42\n```\n"
    fr = process_file(_write(tmp_path, md), OPTS)
    assert fr.failures == 0 and fr.checked == 1


def test_plain_python_ignored(tmp_path):
    md = "```python\nimport os\nprint('x')\n```\n"
    fr = process_file(_write(tmp_path, md), OPTS)
    assert fr.checked == 0


def test_exception_ellipsis():
    ok, rows = check(">>> raise ValueError('boom')\n"
                     "Traceback (most recent call last):\n  ...\nValueError: boom\n")
    assert ok


def test_ellipsis_in_value():
    ok, rows = check(">>> print('id 0x' + format(0xabc, 'x'))\nid 0x...\n")
    assert ok


def test_fix_rewrites(tmp_path):
    path = _write(tmp_path, "```pycon\n>>> 1 + 1\n99\n```\n")
    fr = process_file(path, OPTS, fix=True)
    assert fr.fixed == 1
    assert "\n2\n" in open(path).read()
    # and it passes after fixing
    assert process_file(path, OPTS).failures == 0


def test_fix_preserves_prose_between_examples(tmp_path):
    md = "```pycon\n>>> 1 + 1\n0\n\nsome note\n\n>>> 2 + 2\n0\n```\n"
    path = _write(tmp_path, md)
    process_file(path, OPTS, fix=True)
    out = open(path).read()
    assert "some note" in out
    assert process_file(path, OPTS).failures == 0
