from mdoctest.parser import parse_blocks


def test_basic_block_span_and_info():
    md = "intro\n\n```python\nx = 1\ny = 2\n```\n\nafter\n"
    blocks = parse_blocks(md)
    assert len(blocks) == 1
    b = blocks[0]
    assert b.lang == "python"
    assert b.content == "x = 1\ny = 2"
    assert b.open_line == 2
    assert b.close_line == 5
    assert b.body_start == 3 and b.body_end == 5


def test_info_string_with_attrs():
    md = "```console title=demo\n$ echo hi\nhi\n```\n"
    b = parse_blocks(md)[0]
    assert b.lang == "console"
    assert b.info == "console title=demo"


def test_tilde_fence_and_backticks_inside():
    md = "~~~text\nhas ``` inside\n~~~\n"
    blocks = parse_blocks(md)
    assert len(blocks) == 1
    assert "```" in blocks[0].content


def test_directive_skip_and_run():
    md = ("<!-- mdoctest: skip -->\n```console\n$ x\n```\n\n"
          "<!-- mdoctest: run -->\n\n```python\nx=1\n```\n")
    blocks = parse_blocks(md)
    assert blocks[0].directive == "skip"
    assert blocks[1].directive == "run"     # blank line between comment and fence is ok


def test_no_directive_when_text_between():
    md = "<!-- mdoctest: run -->\nsome text\n```python\nx=1\n```\n"
    assert parse_blocks(md)[0].directive is None


def test_unclosed_fence_runs_to_eof():
    md = "```console\n$ echo hi\nhi\n"
    b = parse_blocks(md)[0]
    assert b.content.strip() == "$ echo hi\nhi"


def test_directive_opts_parsed():
    from mdoctest.parser import parse_blocks
    text = '<!-- mdoctest: run cmd="go run" ext=.go -->\n```go\nx\n```\n'
    blocks = parse_blocks(text)
    b = blocks[0]
    assert b.directive == "run"
    assert b.directive_opts["cmd"] == "go run"
    assert b.directive_opts["ext"] == ".go"
