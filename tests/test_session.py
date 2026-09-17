from mdoctest.session import Shell, parse_session


def test_parse_session_commands_and_output():
    body = "$ echo a\na\n$ echo b\nb\nextra"
    s = parse_session(body)
    assert len(s.commands) == 2
    assert s.commands[0].cmd == "echo a"
    assert s.commands[0].expected == "a"
    assert s.commands[1].expected == "b\nextra"


def test_parse_session_continuation():
    body = "$ echo one \\\n> two\nsomething"
    s = parse_session(body)
    assert s.commands[0].cmd == "echo one \\\ntwo"
    assert s.commands[0].expected == "something"


def test_parse_session_ignores_preamble():
    body = "just text\nno prompt"
    assert parse_session(body).commands == []


def test_shell_runs_and_reports_exit_code():
    with Shell() as sh:
        out, code = sh.run("echo hello")
        assert out == "hello" and code == 0
        _, code2 = sh.run("false")
        assert code2 == 1


def test_shell_state_persists_across_commands():
    with Shell() as sh:
        sh.run("X=42")
        out, _ = sh.run("echo $X")
        assert out == "42"
        sh.run("cd /tmp")
        out2, _ = sh.run("pwd")
        assert out2 == "/tmp"


def test_shell_merges_stderr():
    with Shell() as sh:
        out, _ = sh.run("echo to_err 1>&2")
        assert out == "to_err"


def test_shell_partial_line_without_trailing_newline():
    with Shell() as sh:
        out, code = sh.run("printf 'x'")
        assert out == "x" and code == 0
        out2, _ = sh.run("printf 'a\\nb'")
        assert out2 == "a\nb"
