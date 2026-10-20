"""Split a Bash command line into the simple commands it would run.

Best effort and standard library only. It handles quoting, the usual
operators (&& || ; | & and newlines), subshells, $( ), backticks outside
quotes, heredoc bodies, redirections, leading VAR=value assignments,
wrappers such as env, sudo, nohup, nice, timeout and time, and the
script given to bash -c, sh -c or eval. It also follows cd and pushd so
a later command knows which directory it runs in.

When the input can't be parsed (an unterminated quote, say) it returns
no commands. The hooks built on it then let the command through: a
guard that misses odd syntax is better than one that blocks harmless
commands.
"""

import os
import re
import shlex

_PUNCT = "();<>|&\n`"

# Longest first, so "&&" wins over "&" when splitting a run of punctuation.
_OPERATORS = sorted(
    [
        "<<<", ";;&", "&>>",
        "&&", "||", "|&", ";;", ";&", ">>", "<<", ">&", "<&", "&>", ">|", "<>",
        ";", "&", "|", "(", ")", "<", ">", "\n", "`",
    ],
    key=len,
    reverse=True,
)
_SEPARATORS = {";", "&&", "||", "|", "|&", "&", ";;", ";&", ";;&", "\n", "`"}
_REDIRECTS = {">", ">>", "<", "<<", "<<<", ">&", "<&", "&>", "&>>", ">|", "<>"}

# Words that can start a simple command without being the command.
_KEYWORDS = {
    "if", "then", "else", "elif", "fi", "do", "done", "while", "until",
    "!", "{", "}", "case", "esac", "select", "coproc",
}

_SHELLS = {"bash", "sh", "zsh", "dash", "ksh"}

_ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")

_HEREDOC = re.compile(
    r"(?<!<)<<(?!<)(-?)[ \t]*"
    r"(?:'([^'\n]*)'|\"([^\"\n]*)\"|\\?([A-Za-z0-9_.:@%+-]+))"
)

_MAX_DEPTH = 3


class Command(object):
    """One simple command: its words, the directory it runs in and the
    VAR=value assignments written in front of it."""

    __slots__ = ("argv", "cwd", "env")

    def __init__(self, argv, cwd, env):
        self.argv = argv
        self.cwd = cwd  # None when we can't tell
        self.env = env

    @property
    def name(self):
        return os.path.basename(self.argv[0]) if self.argv else ""

    def __repr__(self):
        return "Command(%r, cwd=%r)" % (self.argv, self.cwd)


def strip_heredocs(text):
    """Remove heredoc bodies so their lines aren't read as commands."""
    out = []
    pos = 0
    while True:
        m = _HEREDOC.search(text, pos)
        if not m:
            out.append(text[pos:])
            break
        delim = m.group(2) if m.group(2) is not None else (
            m.group(3) if m.group(3) is not None else m.group(4))
        strip_tabs = m.group(1) == "-"
        line_end = text.find("\n", m.end())
        if line_end == -1:
            out.append(text[pos:])
            break
        out.append(text[pos:line_end + 1])
        i = line_end + 1
        found = False
        while i < len(text):
            j = text.find("\n", i)
            line = text[i:] if j == -1 else text[i:j]
            if (line.lstrip("\t") if strip_tabs else line) == delim:
                pos = i + len(line)
                found = True
                break
            if j == -1:
                break
            i = j + 1
        if not found:
            # No terminator: bash reads to the end of the input.
            break
    return "".join(out)


def _split_punct(token):
    parts = []
    i = 0
    while i < len(token):
        for op in _OPERATORS:
            if token.startswith(op, i):
                parts.append(op)
                i += len(op)
                break
        else:
            parts.append(token[i])
            i += 1
    return parts


def tokenize(text):
    """Return shell words and operators, or None if the text can't be lexed."""
    text = strip_heredocs(text.replace("\\\n", " "))
    lex = shlex.shlex(text, posix=True, punctuation_chars=_PUNCT)
    lex.whitespace = " \t\r"
    lex.whitespace_split = True
    lex.commenters = ""
    try:
        raw = list(lex)
    except ValueError:
        return None
    tokens = []
    for tok in raw:
        if tok and all(c in _PUNCT for c in tok):
            tokens.extend(_split_punct(tok))
        else:
            tokens.append(tok)
    return tokens


def _segments(tokens):
    """Group tokens into simple commands. Yields lists of words, plus the
    markers "(" and ")" so callers can scope cd to a subshell."""
    current = []
    in_comment = False
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if in_comment:
            if tok == "\n":
                in_comment = False
            i += 1
            continue
        if tok in ("(", ")"):
            if current:
                yield current
                current = []
            yield tok
        elif tok in _SEPARATORS:
            if current:
                yield current
                current = []
        elif tok in _REDIRECTS:
            if current and current[-1].isdigit():
                current.pop()  # the fd number in 2>&1
            nxt = tokens[i + 1] if i + 1 < len(tokens) else None
            if nxt is not None and not (nxt and all(c in _PUNCT for c in nxt)):
                i += 1  # the redirect target
        elif tok.startswith("#"):
            if current:
                yield current
                current = []
            in_comment = True
        else:
            current.append(tok)
        i += 1
    if current:
        yield current


def _skip_options(argv, i, with_value=(), stop_at_assignment=False):
    while i < len(argv):
        a = argv[i]
        if a == "--":
            return i + 1
        if stop_at_assignment and _ASSIGNMENT.match(a):
            return i
        if a.startswith("-") and len(a) > 1:
            if "=" not in a and a in with_value:
                i += 2
            else:
                i += 1
            continue
        return i
    return i


def _peel(argv):
    """Strip assignments, keywords and wrapper commands from the front.

    Returns (argv, env) or (None, env) when the command only looks up a
    name (command -v) and runs nothing.
    """
    env = {}
    i = 0
    while i < len(argv):
        a = argv[i]
        if _ASSIGNMENT.match(a):
            k, v = a.split("=", 1)
            env[k] = v
            i += 1
            continue
        if a in _KEYWORDS:
            i += 1
            continue
        name = os.path.basename(a)
        if name == "env":
            i = _skip_options(argv, i + 1, ("-u", "--unset", "-C", "--chdir", "-S", "--split-string", "-P"),
                              stop_at_assignment=True)
            continue
        if name in ("sudo", "doas"):
            i = _skip_options(argv, i + 1, ("-u", "-g", "-h", "-p", "-C", "-D", "-r", "-t", "-U", "-T", "-R"))
            continue
        if name in ("nohup", "builtin", "chronic"):
            i += 1
            continue
        if name == "exec":
            i = _skip_options(argv, i + 1, ("-a",))
            continue
        if name == "command":
            j = i + 1
            while j < len(argv) and argv[j].startswith("-"):
                if "v" in argv[j] or "V" in argv[j]:
                    return None, env
                j += 1
            i = j
            continue
        if name == "time":
            i = _skip_options(argv, i + 1, ("-f", "-o", "--format", "--output"))
            continue
        if name == "nice":
            i = _skip_options(argv, i + 1, ("-n", "--adjustment"))
            continue
        if name == "ionice":
            i = _skip_options(argv, i + 1, ("-c", "-n", "-p", "-P", "-u", "--class", "--classdata"))
            continue
        if name == "stdbuf":
            i = _skip_options(argv, i + 1, ("-i", "-o", "-e", "--input", "--output", "--error"))
            continue
        if name == "caffeinate":
            i = _skip_options(argv, i + 1, ("-t", "-w"))
            continue
        if name == "timeout":
            i = _skip_options(argv, i + 1, ("-s", "-k", "--signal", "--kill-after"))
            i += 1  # the duration
            continue
        if name == "xargs":
            i = _skip_options(argv, i + 1, ("-n", "-I", "-L", "-P", "-d", "-E", "-s", "-a",
                                            "--max-args", "--max-procs", "--delimiter", "--arg-file"))
            continue
        if name in ("k3s", "microk8s") and i + 1 < len(argv) and argv[i + 1] in ("kubectl", "helm"):
            i += 1
            continue
        break
    rest = argv[i:]
    if rest and os.path.basename(rest[0]) == "microk8s.kubectl":
        rest = ["kubectl"] + rest[1:]
    return rest, env


def _shell_script(argv):
    """The script string from `bash -c '...'`, or None."""
    i = 1
    while i < len(argv):
        a = argv[i]
        if a == "--":
            return None
        if a.startswith("-") and not a.startswith("--") and "c" in a[1:]:
            j = i + 1
            while j < len(argv) and argv[j].startswith("-"):
                j += 1
            return argv[j] if j < len(argv) else None
        if a.startswith("-") or a.startswith("+"):
            i += 1
            continue
        return None  # bash script.sh ...
    return None


def _cd_target(argv, cwd):
    args = [a for a in argv[1:] if not (a.startswith("-") and a != "-")]
    if argv[0] == "popd":
        return None
    if not args:
        return os.path.expanduser("~")
    target = args[0]
    if target == "-":
        return None
    if target == "~" or target.startswith("~/"):
        target = os.path.expanduser(target)
    for var in ("$HOME", "${HOME}"):
        if target == var or target.startswith(var + "/"):
            target = os.path.expanduser("~") + target[len(var):]
    if any(c in target for c in "$`*?["):
        return None
    if not os.path.isabs(target):
        if cwd is None:
            return None
        target = os.path.join(cwd, target)
    return os.path.normpath(target)


def commands(text, cwd=None, _depth=0):
    """Return the simple commands in `text` as a list of Command objects."""
    if not isinstance(text, str) or _depth > _MAX_DEPTH:
        return []
    tokens = tokenize(text)
    if tokens is None:
        return []
    result = []
    stack = []
    here = cwd
    for seg in _segments(tokens):
        if seg == "(":
            stack.append(here)
            continue
        if seg == ")":
            if stack:
                here = stack.pop()
            continue
        argv, env = _peel(seg)
        if not argv:
            continue
        name = os.path.basename(argv[0])
        if name in ("cd", "pushd", "popd"):
            here = _cd_target(argv, here)
            continue
        if name in _SHELLS:
            script = _shell_script(argv)
            if script is not None:
                result.extend(commands(script, here, _depth + 1))
                continue
        if name == "eval" and len(argv) > 1:
            result.extend(commands(" ".join(argv[1:]), here, _depth + 1))
            continue
        result.append(Command(argv, here, env))
    return result
