# agent-skills

Claude Code skills and plugins from my own projects, cleaned up enough to share. The repo is a plugin marketplace, so you can install straight from it.

```
/plugin marketplace add plrojek/agent-skills
/plugin install garden-3d-viewer@plrojek
/plugin install sanalert@plrojek
/plugin install executor-guard@plrojek
/plugin install transcript-review@plrojek
/plugin install pl-genealogy-record-search@plrojek
```

From a shell it's `claude plugin marketplace add plrojek/agent-skills`, then `claude plugin install garden-3d-viewer@plrojek`. If you don't want plugins, copy `plugins/garden-3d-viewer/skills/garden-3d-viewer` into `~/.claude/skills/` and it works the same way.

## garden-3d-viewer

![The example garden in the viewer, October, year five](docs/garden-3d-viewer.jpg)

Turns a planting plan into a 3D garden you open in a browser. A month slider for the seasons, a growth slider from planting day to mature size, the sun's position for any hour, walking at eye level, a tape measure, a PNG of the plan, a shopping list with a CSV export, a map of sun hours and an irrigation layer. Static files and three.js, no build step, nothing on a server.

The plan lives in one place. You keep it as Python tables, an exporter writes `garden-scene.json`, and the viewer draws only what that file says. `templates/example/build_scene.py` is a complete exporter for a made-up plot. Run it first: if the example shows a house, plants and a working month slider, any later problem is in your data.

I built it with Claude Code for my own garden. Ask Claude something like "show my planting plan in 3D" or "how much sun does the terrace get in July" and it should pick the skill up.

A few things to know:

- The interface ships in Polish. The texts sit in three places: the `T` table at the top of `garden.js`, month names in `site.js`, labels in `index.html`. `meta.ui` in the scene overrides the title, currency and layer names.
- `scripts/fetch_three.sh` downloads three.js r180 from jsDelivr into `vendor/` and rewrites the add-on imports, so the page needs no import map and makes no third-party requests once it's deployed.
- The scene file holds your plot outline, the house and coordinates good to about a kilometer. If it's your own house, don't put it on a public URL - and don't post a plan view of it either, because the outline alone can be matched against public land-registry maps. `SKILL.md` has a note on keeping the whole folder private.

## sanalert

[SanAlert](https://sanalert.pl/en/) shows an unofficial threat level from the air for places in Poland. This plugin has no skill, only two MCP servers:

- `sanalert` runs on your computer and needs [uv](https://docs.astral.sh/uv/). Its one tool, `sanalert_level`, gives the level for a town from the website's list or for a point. It downloads the same public state the website reads and works the level out locally, so no request to SanAlert carries the place you ask about. Your assistant's provider still sees your question and the answer, as with anything you ask it. The code is in [plrojek/sanalert-mcp](https://github.com/plrojek/sanalert-mcp), and the plugin runs version 1.0.1 from [PyPI](https://pypi.org/project/sanalert-mcp/).
- `sanalert-poland` is SanAlert's remote server, `https://api.sanalert.pl/mcp`: the state for the whole country, official messages from the last 24 hours, night reports, source cards and the reliability record. It takes no place.

After installing, ask something like "what's the SanAlert level in Przemyśl?".

It is not an official warning system and doesn't replace sirens, Alert RCB or instructions from the authorities. If you show its data anywhere, keep the notice and attribution that come with every answer, including the link to NEPTUN, and never show "no data" as "quiet". The full conditions are in the [sanalert-mcp README](https://github.com/plrojek/sanalert-mcp#conditions-of-use) and [SanAlert's terms](https://sanalert.pl/en/terms/).

## executor-guard

For bigger pieces of work I split the job in two: one session investigates and writes a plan, another session, often on a cheaper model, carries out one slice of it under a page of hard rules. Some of those rules can be checked by a script instead of trusted to the model, and this plugin turns them into hooks.

A hook that runs before every Bash command blocks:

- `git commit`, `git merge` and `git push` while the current branch is `main` or `master`, and a push straight to either of them from another branch;
- force pushes to `main` or `master`, and deleting them on the remote;
- `git stash`, apart from `list` and `show`. All worktrees of a repository share one stash stack, so with agents working in parallel one of them can pop another's changes;
- `helm upgrade`, `install`, `uninstall` and `rollback`; `kubectl apply`, `delete`, `rollout restart`, `scale`, `edit` and `patch`; `terraform` or `tofu` `apply` and `destroy`. Dry runs go through.

Claude gets the reason as the command's error, so it can make a branch, or stop and ask.

When Claude is about to finish, a second hook looks at the turn. If files were changed and no test or build command ran after the last change, it sends Claude back once, to run the tests and paste the output or to say plainly that it didn't. Changes to Markdown and text files don't count, and neither do files under `~/.claude` or temp directories outside the project. pytest, `go test`, `npm test`, `cargo test`, gradle, `xcodebuild test`, `make test` and a few dozen others count as tests; the list is at the top of `hooks/require_tests.py`. A run whose output says the runner never started (`command not found`, `No module named pytest`) doesn't count.

`/executor-guard:handoff [path]` writes a note for the next session, `HANDOFF.md` by default: what was planned, what's done with the evidence, what's not, open questions and the next step.

To allow something, add `.claude/executor-guard.json` to the project:

```json
{
  "allow": ["helm upgrade", "kubectl apply"],
  "protected_branches": ["main", "master", "release/*"],
  "test_commands": ["./scripts/check.sh"],
  "ignore_paths": ["docs/*"]
}
```

or start Claude with `EXECUTOR_GUARD_ALLOW="helm upgrade,kubectl apply"`. An entry covers every rule that starts with its words, so `"kubectl"` allows all the kubectl ones. Besides the deploy commands above, the rules are `git commit`, `git merge`, `git push`, `git force-push` and `git stash`, and each block message names the rule that fired. The hook can't see the conversation, so a deploy you OK in the chat still has to be allowed here first.

It catches mistakes; it isn't a security boundary. Things to know:

- It splits the command with Python's `shlex` and follows `&&` and `;`, pipes, subshells, `$( )`, `cd`, `env`, `sudo`, a shell started with `-c`, and heredocs. It doesn't expand variables or aliases, doesn't read scripts the command runs, and misses `$( )` and backticks inside double quotes. A command it can't parse, such as one with an unterminated quote, goes through.
- A quoted argument that is exactly an operator, like `echo "&&"`, is read as an operator.
- After `git checkout <branch>` in the same command line, the branch counts as unknown, and an unknown branch isn't checked.
- `git pull`, `rebase`, `cherry-pick`, `revert` and `am` on `main` aren't checked, and neither are `kubectl create`, `replace`, `set` or `rollout undo`, `gh pr merge`, or anything run over ssh.
- Claude can still write the config file itself, or edit files through Bash (`sed -i`, a heredoc into a file). The test check doesn't see edits made through Bash or by subagents, and it only looks at the current turn.
- Only the Bash tool is checked, not PowerShell on Windows.
- It needs `python3` (3.9 or later) on PATH. If a hook can't start, Claude Code carries on without it.

The tests are plain unittest and live outside the plugin, so they aren't installed: `python3 -m unittest discover -s tests/executor-guard` from the repository root. `plugins/executor-guard/evals/` has six cases for `claude plugin eval`; their setup scripts only write inside each case's own folder. The git cases need a git that works inside Claude Code's sandbox. On a Mac where the only git is Apple's `/usr/bin/git` it doesn't (xcrun can't write its cache there), so those cases pass without the hook ever being reached.

## transcript-review

![The review page on a made-up recording: two lines assigned, one split, one word the models disagreed on](docs/transcript-review.jpg)

I needed exact words, and who said them, from a 44-minute recording made on one phone outdoors: five people, one side of a phone call on loudspeaker, wind, people talking over each other. The first transcript had invented words and no speakers. This skill gets as close as local models can, then has you listen to the passages that matter.

1. It cuts the speech into chunks of up to 28 seconds and runs four systems on them: Whisper large-v3 on lightly filtered audio for the text, and large-v3 on the raw audio, large-v3-turbo and NVIDIA Parakeet v3 as second opinions. Parakeet also gives the word timings, because Whisper's drift.
2. It opens a review page on localhost. You correct four test passages of a minute or so by ear: one line per person, Enter splits a line, Ctrl+1…8 sets who is talking, a time box moves a line.
3. `score` measures every system against your passages and says which is best on this recording.
4. `voices` learns each person's voice from the lines you checked and assigns speakers to the rest. People who spoke once or twice appear only where you put them, and a phone caller only inside the call.
5. `build` writes a Markdown transcript. Lines you checked are marked ✓, words that fewer than half of the other models heard are in italics, weak speaker matches get "(?)".

Nothing is filled in from context: every word comes from a model or from you.

On my recording, in Polish, large-v3 on filtered audio got an 11.1% word error rate on the checked passages; the other 15 combinations of model and audio got 14.9 to 48.3%. Noise removal with DeepFilterNet made every model worse, so the skill keeps it for listening only. Voting across the models was worse than the best model alone. The italics mark 10% of the words and catch about 61% of the errors. The voice models put the right person on 96 to 98% of held-out checked lines. All of it is in `references/lessons.md`, and it's one recording, so `score` measures again on yours.

I built it on my experience from Wasabi, where I worked on multilingual speech-to-text and diarization pipelines. Ask Claude something like "transcribe this recording with who said what" and it should pick the skill up, ask who was there and which moments matter, and walk you through the page.

A few things to know:

- It needs a Mac with Apple Silicon (Parakeet runs on MLX), `uv`, `ffmpeg` and whisper.cpp: `brew install uv ffmpeg whisper-cpp`. The first run downloads about 5 GB of models.
- Everything runs on your computer and the audio never leaves it. The review server listens on 127.0.0.1 and refuses requests from other sites.
- On an M4 Pro the models take about 15 minutes for 45 minutes of audio. The four test passages took me 30 to 40 minutes, including learning the page.
- It was tuned on Polish. Other languages Whisper knows should work, but I haven't measured them.

## pl-genealogy-record-search

For finding Polish ancestors: Geneteka parish indexes, the Indeks Represjonowanych (Soviet deportations), cemetery registers and scanned parish books, with the tree as a GEDCOM. It lists the brick walls on the direct line, sweeps the sources you choose, matches the results against the tree, grades every finding from confirmed to rejected, and patches a copy of the GEDCOM so it still imports.

Most of the skill is the traps I hit working through my own family's lines: Geneteka answering with thousands of rows from the wrong province, a zero that was a spelling, a marriage filed in the bride's parish because she was of the other rite, a cemetery register that hides married women from a maiden-name search, a book written off as "needs a letter to the archive" that was already free online. The scripts are Python with no dependencies, identify themselves to the sites and wait between requests. Details, and exactly what it contacts, are in [its README](plugins/pl-genealogy-record-search/README.md).

## License

MIT. three.js, which the script downloads, is MIT as well.
