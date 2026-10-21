import os
import unittest

import helpers
from helpers import GUARD, TempDirCase, clean_env, make_repo, run_hook


class GuardCase(TempDirCase):
    def setUp(self):
        super(GuardCase, self).setUp()
        self.main = make_repo(os.path.join(self.tmp, "on-main"), "main")
        self.feature = make_repo(os.path.join(self.tmp, "on-feature"), "feature/x")
        self.plain = os.path.join(self.tmp, "not-a-repo")
        os.makedirs(self.plain)
        os.makedirs(os.path.join(self.main, "sub"))

    def guard(self, command, cwd, env=None, tool="Bash"):
        payload = {
            "session_id": "test",
            "hook_event_name": "PreToolUse",
            "cwd": cwd,
            "tool_name": tool,
            "tool_input": {"command": command, "description": "test"},
        }
        return run_hook(GUARD, payload, env)

    def assertBlocked(self, command, cwd, rule, env=None):
        code, _, err = self.guard(command, cwd, env)
        self.assertEqual(code, 2, "expected a block for %r, stderr: %r" % (command, err))
        self.assertIn("(rule: %s)" % rule, err)
        return err

    def assertAllowed(self, command, cwd, env=None):
        code, out, err = self.guard(command, cwd, env)
        self.assertEqual(code, 0, "expected %r to pass, stderr: %r" % (command, err))
        self.assertEqual(err, "")


class ProtectedBranchTest(GuardCase):
    def test_commit_on_main(self):
        err = self.assertBlocked("git commit -m 'fix typo'", self.main, "git commit")
        self.assertIn("`git commit` on main", err)

    def test_commit_with_quoted_operators(self):
        self.assertBlocked('git commit -am "fix: a && b; c | d"', self.main, "git commit")

    def test_commit_after_cd_into_the_repo(self):
        self.assertBlocked("cd %s && git add -A && git commit -m x" % self.main, self.plain, "git commit")
        self.assertBlocked("cd sub; git commit -m x", self.main, "git commit")

    def test_commit_with_git_dash_c_dir(self):
        self.assertBlocked("git -C %s commit -m x" % self.main, self.plain, "git commit")
        self.assertBlocked("git -c user.name=x --no-pager commit -m y", self.main, "git commit")

    def test_commit_behind_wrappers(self):
        self.assertBlocked("FOO=1 env BAR=2 git commit -m x", self.main, "git commit")
        self.assertBlocked("bash -c 'git commit -m x'", self.main, "git commit")
        self.assertBlocked("git status | head -3 && git commit -m x", self.main, "git commit")

    def test_commit_after_switching_branch_in_the_same_command(self):
        self.assertAllowed("git switch -c fix/typo && git commit -m x", self.main)
        self.assertAllowed("git checkout -b fix/typo origin/main; git commit -m x", self.main)
        self.assertBlocked("git switch -c fix/typo && git switch main && git commit -m x",
                           self.main, "git commit")
        self.assertBlocked("git checkout main && git merge feature/x", self.feature, "git merge")

    def test_checkout_of_a_path_keeps_the_branch(self):
        self.assertBlocked("git checkout README.md && git commit -am x", self.main, "git commit")

    def test_commit_elsewhere_is_fine(self):
        self.assertAllowed("git commit -m x", self.feature)
        self.assertAllowed("git commit -m x", self.plain)
        self.assertAllowed("cd /tmp && git commit -m x", self.main)
        self.assertAllowed("(cd %s && git commit -m x)" % self.feature, self.main)

    def test_subshell_cd_does_not_leak(self):
        self.assertBlocked("(cd %s && ls) && git commit -m x" % self.feature, self.main, "git commit")

    def test_merge_on_main(self):
        self.assertBlocked("git merge feature/x", self.main, "git merge")
        self.assertAllowed("git merge --abort", self.main)
        self.assertAllowed("git merge origin/main", self.feature)

    def test_push_from_main(self):
        err = self.assertBlocked("git push", self.main, "git push")
        self.assertIn("from main", err)
        self.assertBlocked("git push origin feature/x", self.main, "git push")
        self.assertAllowed("git push --dry-run origin main", self.main)
        self.assertAllowed("git push -n", self.main)

    def test_push_from_a_feature_branch(self):
        self.assertAllowed("git push -u origin feature/x", self.feature)
        self.assertAllowed("git push --force-with-lease origin feature/x", self.feature)
        self.assertAllowed("git push origin v1.0.0", self.feature)

    def test_direct_push_to_main_from_a_feature_branch(self):
        err = self.assertBlocked("git push origin HEAD:main", self.feature, "git push")
        self.assertIn("a push to main", err)
        self.assertBlocked("git push origin feature/x:refs/heads/master", self.feature, "git push")

    def test_read_only_git(self):
        for command in ("git status", "git log --oneline -5", "git diff HEAD~1", "git fetch origin",
                        "git pull --ff-only", "git commit --help", "git branch -a"):
            self.assertAllowed(command, self.main)

    def test_text_that_only_mentions_git(self):
        self.assertAllowed('echo "git commit -m x" && grep -r "git push" .', self.main)
        self.assertAllowed("cat > notes.md <<'EOF'\ngit commit -m x\ngit stash\nEOF", self.main)
        self.assertAllowed("git log --grep 'git stash'", self.main)

    def test_unparseable_command_passes(self):
        self.assertAllowed('git commit -m "unterminated', self.main)


class ForcePushTest(GuardCase):
    def test_force_push_to_main(self):
        cases = [
            "git push --force origin feature/x:main",
            "git push -f origin main",
            "git push -fu origin main",
            "git push --force-with-lease origin main",
            "git push origin +HEAD:main",
            "git push origin +feature/x:refs/heads/master",
            "git push --mirror origin",
            "git push --all --force origin",
        ]
        for command in cases:
            err = self.assertBlocked(command, self.feature, "git force-push")
            self.assertIn("force push", err)

    def test_force_push_on_main_without_refspec(self):
        self.assertBlocked("git push --force", self.main, "git force-push")

    def test_delete_main_on_the_remote(self):
        for command in ("git push origin :main", "git push origin --delete master", "git push -d origin main"):
            err = self.assertBlocked(command, self.feature, "git force-push")
            self.assertIn("deleting", err)

    def test_force_push_of_a_feature_branch(self):
        self.assertAllowed("git push -f origin feature/x", self.feature)
        self.assertAllowed("git push --force", self.feature)


class StashTest(GuardCase):
    def test_stash_is_blocked(self):
        for command in ("git stash", "git stash push -m wip", "git stash pop", "git stash apply",
                        "git stash drop", "git stash clear", "git -C . stash save x",
                        "cd sub && git stash -u"):
            err = self.assertBlocked(command, self.feature if "sub" not in command else self.main,
                                     "git stash")
            self.assertIn("share one stash stack", err)

    def test_read_only_stash(self):
        self.assertAllowed("git stash list", self.feature)
        self.assertAllowed("git stash show -p stash@{0}", self.feature)

    def test_stash_outside_a_repo_is_still_blocked(self):
        self.assertBlocked("git stash", self.plain, "git stash")


class DeployTest(GuardCase):
    def test_blocked(self):
        cases = {
            "helm upgrade app ./chart -f values.yaml": "helm upgrade",
            "helm --kube-context prod -n web upgrade --install app .": "helm upgrade",
            "helm install app ./chart": "helm install",
            "helm uninstall app": "helm uninstall",
            "helm delete app": "helm uninstall",
            "helm rollback app 3": "helm rollback",
            "kubectl apply -f deploy.yaml": "kubectl apply",
            "kubectl --context prod -n web delete pod x": "kubectl delete",
            "kubectl rollout restart deployment/web": "kubectl rollout restart",
            "kubectl -n web rollout restart deploy web": "kubectl rollout restart",
            "kubectl scale --replicas=0 deploy/web": "kubectl scale",
            "kubectl edit deploy web": "kubectl edit",
            "kubectl patch deploy web -p '{\"spec\":{}}'": "kubectl patch",
            "kubectl apply --dry-run=none -f x.yaml": "kubectl apply",
            "terraform apply -auto-approve": "terraform apply",
            "terraform -chdir=infra destroy": "terraform destroy",
            "tofu apply": "tofu apply",
            "k3s kubectl apply -f x.yaml": "kubectl apply",
            "sudo -E kubectl delete ns old": "kubectl delete",
            "kubectl get pods | grep web && helm upgrade app .": "helm upgrade",
            "cd deploy && KUBECONFIG=kc timeout 60 kubectl apply -k .": "kubectl apply",
        }
        for command, rule in sorted(cases.items()):
            err = self.assertBlocked(command, self.plain, rule)
            self.assertIn("go-ahead", err)

    def test_read_only_and_dry_runs(self):
        for command in (
            "helm list -A", "helm template app ./chart", "helm upgrade --dry-run app .",
            "helm upgrade app . --dry-run=server", "helm status app", "helm history app",
            "kubectl get pods -A", "kubectl describe deploy web", "kubectl logs deploy/web",
            "kubectl diff -f x.yaml", "kubectl apply --dry-run=client -f x.yaml",
            "kubectl apply view-last-applied deploy/web", "kubectl rollout status deploy/web",
            "kubectl delete --help", "terraform plan", "terraform plan -destroy",
            "terraform init", "echo 'helm upgrade app .'",
        ):
            self.assertAllowed(command, self.plain)


class ConfigTest(GuardCase):
    def test_allow_list_in_config(self):
        self.write_config(self.plain, {"allow": ["helm upgrade", "kubectl"]})
        self.assertAllowed("helm upgrade app .", self.plain)
        self.assertAllowed("kubectl apply -f x.yaml", self.plain)
        self.assertAllowed("kubectl rollout restart deploy/web", self.plain)
        self.assertBlocked("helm install app .", self.plain, "helm install")
        self.assertBlocked("terraform apply", self.plain, "terraform apply")

    def test_config_is_found_from_a_subdirectory(self):
        self.write_config(self.main, {"allow": ["git stash"]})
        self.assertAllowed("git stash", os.path.join(self.main, "sub"))

    def test_config_from_claude_project_dir(self):
        project = os.path.join(self.tmp, "project")
        self.write_config(project, {"allow": ["terraform apply"]})
        self.assertAllowed("terraform apply", self.plain, env=clean_env(CLAUDE_PROJECT_DIR=project))

    def test_allow_from_environment(self):
        env = clean_env(EXECUTOR_GUARD_ALLOW="terraform apply, helm")
        self.assertAllowed("terraform apply", self.plain, env=env)
        self.assertAllowed("helm rollback app 2", self.plain, env=env)
        self.assertBlocked("kubectl apply -f x", self.plain, "kubectl apply", env=env)

    def test_allow_git_rules(self):
        self.write_config(self.main, {"allow": ["git commit"]})
        self.assertAllowed("git commit -m x", self.main)
        self.assertBlocked("git push", self.main, "git push")

    def test_protected_branches(self):
        self.write_config(self.tmp, {"protected_branches": ["feature/*"]})
        self.assertAllowed("git commit -m x", self.main)
        self.assertBlocked("git commit -m x", self.feature, "git commit")
        self.assertBlocked("git push -f origin feature/y", self.main, "git force-push")

    def test_broken_config_still_blocks_and_says_why(self):
        self.write_config(self.plain, "{not json")
        err = self.assertBlocked("helm upgrade app .", self.plain, "helm upgrade")
        self.assertIn("could not read its config", err)


class InputTest(GuardCase):
    def test_other_tools_and_bad_input_pass(self):
        code, _, _ = self.guard("git stash", self.feature, tool="Write")
        self.assertEqual(code, 0)
        for raw in ("", "not json", "[]", '{"tool_name": "Bash", "tool_input": {}}',
                    '{"tool_name": "Bash", "tool_input": {"command": 42}}'):
            code, _, err = run_hook(GUARD, raw)
            self.assertEqual(code, 0, raw)
            self.assertEqual(err, "", raw)

    def test_missing_cwd_falls_back_to_process_cwd(self):
        payload = {"tool_name": "Bash", "tool_input": {"command": "git commit -m x"}}
        self.assertEqual(run_hook(GUARD, payload, cwd=self.main)[0], 2)
        self.assertEqual(run_hook(GUARD, payload, cwd=self.feature)[0], 0)


if __name__ == "__main__":
    unittest.main()
