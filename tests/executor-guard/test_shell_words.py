import os
import unittest

import helpers  # noqa: F401  (puts hooks/ on sys.path)
import shell_words


def argvs(text, cwd=None):
    return [c.argv for c in shell_words.commands(text, cwd)]


class SplitTest(unittest.TestCase):
    def test_single_command(self):
        self.assertEqual(argvs("git status"), [["git", "status"]])

    def test_operators(self):
        self.assertEqual(
            argvs("a 1 && b 2 || c; d | e & f\ng"),
            [["a", "1"], ["b", "2"], ["c"], ["d"], ["e"], ["f"], ["g"]],
        )

    def test_operators_without_spaces(self):
        self.assertEqual(argvs("make&&git push;echo ok"), [["make"], ["git", "push"], ["echo", "ok"]])

    def test_quoted_operators_stay_in_the_argument(self):
        self.assertEqual(
            argvs('git commit -m "fix: a && b; c | d"'),
            [["git", "commit", "-m", "fix: a && b; c | d"]],
        )
        self.assertEqual(argvs("echo 'git push; rm -rf x'"), [["echo", "git push; rm -rf x"]])

    def test_subshell_and_command_substitution(self):
        self.assertEqual(argvs("(git stash)"), [["git", "stash"]])
        self.assertEqual(argvs("echo $(git stash pop)"), [["echo", "$"], ["git", "stash", "pop"]])
        self.assertEqual(argvs("echo `git stash`"), [["echo"], ["git", "stash"]])

    def test_redirections_are_dropped(self):
        self.assertEqual(argvs("git push origin main 2>&1 | tee log"),
                         [["git", "push", "origin", "main"], ["tee", "log"]])
        self.assertEqual(argvs("ls > out.txt"), [["ls"]])

    def test_heredoc_body_is_not_a_command(self):
        text = "cat > notes.md <<'EOF'\ngit stash\nhelm upgrade x\nEOF\ngit status"
        self.assertEqual(argvs(text), [["cat"], ["git", "status"]])

    def test_heredoc_inside_command_substitution(self):
        text = 'git commit -m "$(cat <<\'EOF\'\nIt\'s a "quoted" message\nEOF\n)"'
        result = argvs(text)
        self.assertEqual(result[0][:3], ["git", "commit", "-m"])

    def test_comments(self):
        self.assertEqual(argvs("ls # git push\ngit status"), [["ls"], ["git", "status"]])

    def test_line_continuation(self):
        self.assertEqual(argvs("git \\\n  push origin x"), [["git", "push", "origin", "x"]])

    def test_unterminated_quote_gives_nothing(self):
        self.assertEqual(argvs('git commit -m "oops'), [])

    def test_non_string(self):
        self.assertEqual(shell_words.commands(None), [])


class WrapperTest(unittest.TestCase):
    def test_assignments(self):
        cmd = shell_words.commands("FOO=1 BAR='a b' git push")[0]
        self.assertEqual(cmd.argv, ["git", "push"])
        self.assertEqual(cmd.env, {"FOO": "1", "BAR": "a b"})

    def test_env_sudo_nohup_time(self):
        self.assertEqual(argvs("env -i FOO=1 git push"), [["git", "push"]])
        self.assertEqual(argvs("sudo -u deploy -E helm upgrade x ."), [["helm", "upgrade", "x", "."]])
        self.assertEqual(argvs("nohup nice -n 5 time kubectl apply -f x"), [["kubectl", "apply", "-f", "x"]])
        self.assertEqual(argvs("timeout -s KILL 30 kubectl apply -f x"), [["kubectl", "apply", "-f", "x"]])

    def test_command_v_runs_nothing(self):
        self.assertEqual(argvs("command -v helm"), [])
        self.assertEqual(argvs("command helm upgrade x ."), [["helm", "upgrade", "x", "."]])

    def test_shell_keywords(self):
        self.assertEqual(argvs("if git diff --quiet; then git commit -m x; fi"),
                         [["git", "diff", "--quiet"], ["git", "commit", "-m", "x"]])
        self.assertEqual(argvs("{ git stash; }"), [["git", "stash"]])

    def test_bash_c_and_eval(self):
        self.assertEqual(argvs("bash -c 'cd x && git push'", "/w"), [["git", "push"]])
        self.assertEqual(shell_words.commands("bash -lc 'cd x && git push'", "/w")[0].cwd, "/w/x")
        self.assertEqual(argvs('sh -c "git stash"'), [["git", "stash"]])
        self.assertEqual(argvs("eval git stash pop"), [["git", "stash", "pop"]])

    def test_bash_running_a_script_is_left_alone(self):
        self.assertEqual(argvs("bash scripts/deploy.sh"), [["bash", "scripts/deploy.sh"]])

    def test_k3s_kubectl(self):
        self.assertEqual(argvs("k3s kubectl apply -f x"), [["kubectl", "apply", "-f", "x"]])


class CdTest(unittest.TestCase):
    def cwds(self, text, cwd="/work"):
        return [(c.argv[0], c.cwd) for c in shell_words.commands(text, cwd)]

    def test_relative_and_absolute(self):
        self.assertEqual(self.cwds("cd sub && git status; cd /other && ls"),
                         [("git", "/work/sub"), ("ls", "/other")])

    def test_home(self):
        home = os.path.expanduser("~")
        self.assertEqual(self.cwds("cd && ls"), [("ls", home)])
        self.assertEqual(self.cwds("cd ~/x && ls"), [("ls", os.path.join(home, "x"))])

    def test_subshell_scope(self):
        self.assertEqual(self.cwds("(cd /tmp && ls) && git status"), [("ls", "/tmp"), ("git", "/work")])

    def test_unknown_target(self):
        self.assertEqual(self.cwds("cd $REPO && git push"), [("git", None)])
        self.assertEqual(self.cwds("cd - && git push"), [("git", None)])


if __name__ == "__main__":
    unittest.main()
