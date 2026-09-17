"""Run console sessions against a persistent shell.

A single shell subprocess is kept alive for the whole block so that state
(``cd``, environment variables, shell functions) carries across commands,
exactly like a real terminal session. Each command's combined stdout+stderr and
its exit code are captured individually via a unique sentinel line.

POSIX only (uses ``select`` on the shell's stdout pipe); that covers the
``bash``/``sh`` sessions found in READMEs.
"""
from __future__ import annotations

import os
import queue
import re
import subprocess
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import List, Optional


class SessionTimeout(RuntimeError):
    pass


@dataclass
class Command:
    cmd: str            # full command text (continuations joined by "\n")
    expected: str       # expected combined output (may use ... wildcards)


@dataclass
class ParsedSession:
    commands: List[Command] = field(default_factory=list)


def parse_session(body: str, prompt: str = "$ ", cont: str = "> ") -> ParsedSession:
    commands: List[Command] = []
    cur: Optional[str] = None
    exp: List[str] = []

    def flush():
        if cur is not None:
            commands.append(Command(cur, "\n".join(exp)))

    for line in body.split("\n"):
        if cur is not None and not exp and _backslash_continues(cur):
            # Previous command line ends with an (odd) trailing backslash, so
            # this physical line continues the same shell command, even without
            # a ``> `` continuation prompt. Real READMEs wrap long piped
            # commands this way and just indent the continuation lines. If a
            # ``> `` prompt is *also* present, strip it (both conventions used).
            if line.startswith(cont):
                line = line[len(cont):]
            cur = cur + "\n" + line
        elif line.startswith(prompt):
            flush()
            cur = line[len(prompt):]
            exp = []
        elif cur is not None and not exp and line.startswith(cont):
            cur = cur + "\n" + line[len(cont):]
        elif cur is not None:
            exp.append(line)
        # text before the first prompt is ignored
    flush()
    return ParsedSession(commands)


def _backslash_continues(command: str) -> bool:
    """True if *command*'s last physical line ends with a shell line
    continuation (an odd number of trailing backslashes)."""
    last = command.split("\n")[-1]
    m = re.search(r"\\+$", last)
    return bool(m) and len(m.group(0)) % 2 == 1


class Shell:
    def __init__(self, shell: str = "bash", cwd: Optional[str] = None,
                 env: Optional[dict] = None, timeout: float = 30.0):
        self.timeout = timeout
        self.sentinel = "__MDOCTEST_%s__" % uuid.uuid4().hex
        run_env = dict(os.environ if env is None else env)
        run_env.setdefault("PS1", "")
        run_env.setdefault("TERM", "dumb")
        self.proc = subprocess.Popen(
            [shell], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, bufsize=1,
            cwd=cwd, env=run_env,
        )
        # A dedicated reader thread avoids the classic select()+buffered
        # readline() race (readline can pull several lines into Python's buffer,
        # after which select on the fd reports "no data" and blocks forever).
        self._q: "queue.Queue[Optional[str]]" = queue.Queue()
        self._reader = threading.Thread(target=self._pump, daemon=True)
        self._reader.start()

    def _pump(self):
        try:
            assert self.proc.stdout is not None
            for line in self.proc.stdout:
                self._q.put(line)
        finally:
            self._q.put(None)  # EOF

    def _readline(self, deadline: float) -> Optional[str]:
        remaining = deadline - time.time()
        if remaining <= 0:
            return None
        try:
            return self._q.get(timeout=remaining)
        except queue.Empty:
            return None

    def run(self, command: str):
        """Return (combined_output, exit_code) for *command*."""
        assert self.proc.stdin is not None
        self.proc.stdin.write(command + "\n")
        self.proc.stdin.write('printf "%%s %%d\\n" %s "$?"\n' % self.sentinel)
        self.proc.stdin.flush()
        out: List[str] = []
        deadline = time.time() + self.timeout
        while True:
            line = self._readline(deadline)
            if line is None:
                raise SessionTimeout(
                    "command timed out after %ss or shell exited: %r"
                    % (self.timeout, command))
            # The sentinel may be glued to a command's last output line when
            # that line has no trailing newline, so search anywhere in the line.
            if self.sentinel in line:
                pre, _, rest = line.partition(self.sentinel)
                if pre != "":
                    out.append(pre.rstrip("\n"))
                try:
                    code = int(rest.strip())
                except ValueError:
                    code = 0
                return "\n".join(out), code
            out.append(line.rstrip("\n"))

    def close(self):
        try:
            if self.proc.stdin:
                self.proc.stdin.write("exit\n")
                self.proc.stdin.flush()
                self.proc.stdin.close()
            self.proc.wait(timeout=5)
        except Exception:
            try:
                self.proc.kill()
            except Exception:
                pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
