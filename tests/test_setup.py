"""Tests for invisible `<!-- mdoctest: setup -->` fixture blocks."""
import os
import textwrap

from mdoctest.core import Options, process_file
from mdoctest.parser import parse_setups


def _write(tmp_path, text):
    p = tmp_path / "README.md"
    p.write_text(textwrap.dedent(text))
    return str(p)


def test_parse_multiline_setup():
    text = textwrap.dedent(
        """\
        # Doc

        <!-- mdoctest: setup
        echo hi > f.txt
        -->

        ```console
        $ cat f.txt
        hi
        ```
        """
    )
    setups = parse_setups(text)
    assert len(setups) == 1
    assert "echo hi > f.txt" in setups[0].script


def test_parse_oneline_setup():
    text = "<!-- mdoctest: setup mkdir -p demo -->\n"
    setups = parse_setups(text)
    assert len(setups) == 1
    assert setups[0].script == "mkdir -p demo"


def test_setup_creates_fixture_for_session(tmp_path):
    path = _write(
        tmp_path,
        """\
        <!-- mdoctest: setup
        printf 'a\\nb\\nc\\n' > data.txt
        -->

        ```console
        $ cat data.txt
        a
        b
        c
        ```
        """,
    )
    fr = process_file(path, Options())
    assert fr.failures == 0
    assert fr.checked == 1


def test_setup_supports_heredoc(tmp_path):
    path = _write(
        tmp_path,
        """\
        <!-- mdoctest: setup
        cat > people.tsv <<'END'
        John	Smith
        Ada	Lovelace
        END
        -->

        ```console
        $ wc -l < people.tsv
        2
        ```
        """,
    )
    fr = process_file(path, Options())
    assert fr.failures == 0


def test_setup_does_not_pollute_repo(tmp_path):
    """Fixtures live in a sandbox, not next to the Markdown file."""
    path = _write(
        tmp_path,
        """\
        <!-- mdoctest: setup
        echo x > sentinel.txt
        -->

        ```console
        $ cat sentinel.txt
        x
        ```
        """,
    )
    fr = process_file(path, Options())
    assert fr.failures == 0
    assert not os.path.exists(os.path.join(str(tmp_path), "sentinel.txt"))


def test_progressive_setup_only_affects_later_blocks(tmp_path):
    """A setup applies to session blocks that come after it, not before."""
    path = _write(
        tmp_path,
        """\
        ```console
        $ cat late.txt
        cat: late.txt: No such file or directory
        ```

        <!-- mdoctest: setup
        echo ready > late.txt
        -->

        ```console
        $ cat late.txt
        ready
        ```
        """,
    )
    fr = process_file(path, Options())
    assert fr.failures == 0
    assert fr.checked == 2


def test_setup_fix_still_works(tmp_path):
    path = _write(
        tmp_path,
        """\
        <!-- mdoctest: setup
        echo correct > v.txt
        -->

        ```console
        $ cat v.txt
        WRONG
        ```
        """,
    )
    fr = process_file(path, Options(), fix=True)
    assert fr.fixed == 1
    new = open(path).read()
    assert "correct" in new
    assert "WRONG" not in new


def test_block_attached_setup_parses_following_fence():
    text = textwrap.dedent(
        """\
        # Doc

        <!-- mdoctest: setup -->
        ```sh
        printf 'a\\nb\\n' > data.txt
        ```

        ```console
        $ wc -l < data.txt
        2
        ```
        """
    )
    setups = parse_setups(text)
    assert len(setups) == 1
    assert "printf 'a\\nb\\n' > data.txt" in setups[0].script


def test_block_attached_setup_seeds_session(tmp_path):
    path = _write(
        tmp_path,
        """\
        <!-- mdoctest: setup -->
        ```sh
        printf 'a\\nb\\nc\\n' > data.txt
        ```

        ```console
        $ cat data.txt
        a
        b
        c
        ```
        """,
    )
    fr = process_file(path, Options())
    assert fr.failures == 0
    # Only the visible console block is checked; the setup block is not run/counted.
    assert fr.checked == 1


def test_block_attached_setup_block_is_not_executed(tmp_path):
    # The adopted fixture block (a plain script) must not itself be checked as
    # an example: only the visible session below it is checked/counted.
    path = _write(
        tmp_path,
        """\
        <!-- mdoctest: setup -->
        ```sh
        echo seed > s.txt
        ```

        ```console
        $ cat s.txt
        seed
        ```
        """,
    )
    fr = process_file(path, Options())
    assert fr.failures == 0
    assert fr.checked == 1


def test_empty_setup_with_no_following_block_is_noop(tmp_path):
    text = "<!-- mdoctest: setup -->\n\nSome prose, no code block.\n"
    setups = parse_setups(text)
    assert len(setups) == 1
    assert setups[0].script == ""
