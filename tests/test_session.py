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


def test_parse_session_backslash_continuation_no_prompt():
    # Real READMEs wrap long piped commands with a trailing backslash and just
    # indent the continuation lines (no ``> `` prompt). They must be joined
    # into one command, not mistaken for expected output.
    body = "$ printf 'a\\nb\\n' | grep \\\n    b\nb"
    s = parse_session(body)
    assert len(s.commands) == 1
    assert s.commands[0].cmd == "printf 'a\\nb\\n' | grep \\\n    b"
    assert s.commands[0].expected == "b"


def test_parse_session_heredoc_body_kept_in_command():
    body = "$ cat <<END\nalpha\nbeta\nEND\nalpha\nbeta"
    s = parse_session(body)
    assert len(s.commands) == 1
    assert s.commands[0].cmd == "cat <<END\nalpha\nbeta\nEND"
    assert s.commands[0].expected == "alpha\nbeta"


def test_parse_session_heredoc_prompt_line_in_body_not_new_command():
    # A body line beginning with the prompt is literal heredoc input, not a
    # new command, until the delimiter closes the here-doc.
    body = "$ cat <<END\n$ still body\nEND\nplain output"
    s = parse_session(body)
    assert len(s.commands) == 1
    assert s.commands[0].cmd == "cat <<END\n$ still body\nEND"
    assert s.commands[0].expected == "plain output"


def test_parse_session_heredoc_dash_and_quoted_delim():
    body = "$ cat <<-'EOF'\n\tindented\nEOF\nindented"
    s = parse_session(body)
    assert len(s.commands) == 1
    assert s.commands[0].cmd == "cat <<-'EOF'\n\tindented\nEOF"


def test_reconstruct_session_heredoc_no_cont_prefix():
    from mdoctest.core import _reconstruct_session

    class C:
        def __init__(self, command, actual):
            self.command = command
            self.actual = actual

    out = _reconstruct_session(
        [C("cat <<END\nalpha\nEND", "alpha")], "$ ", "> ")
    assert out == "$ cat <<END\nalpha\nEND\nalpha"
