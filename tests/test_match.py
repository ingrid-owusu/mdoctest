from mdoctest.match import matches, normalize


def test_normalize_trailing_ws_and_blanks():
    assert normalize("a  \nb\n\n\n") == "a\nb"
    assert normalize("\r\nx\r\n") == "\nx"


def test_exact_match():
    assert matches("a\nb", "a\nb")
    assert matches("a\nb\n", "a\nb")          # trailing newline ignored
    assert matches("a \nb", "a\nb")            # trailing space ignored
    assert not matches("a\nb", "a\nc")


def test_inline_ellipsis():
    assert matches("hello ... world", "hello brave new world")
    assert matches("v...", "v1.2.3")
    assert not matches("v...z", "v1.2.3")


def test_multiline_ellipsis():
    expected = "start\n...\nend"
    assert matches(expected, "start\nnoise 1\nnoise 2\nend")
    assert matches(expected, "start\nend")     # matches zero lines too
    assert not matches(expected, "start\nno-finish")


def test_ellipsis_is_non_greedy_but_full():
    assert matches("a...b", "aXXbYYb")         # fullmatch over whole string
