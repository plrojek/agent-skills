---
name: transcript-review
description: "Make the most accurate possible transcript, with named speakers, of a noisy multi-speaker recording (meeting, interview, conversation outdoors, phone call on speaker): local models only (free, the audio never leaves the Mac), a local review page where the user corrects a few test passages by ear, measurement of which model is really best on THIS recording, speaker matching from the user's corrections, words the machine is unsure of marked in italics, checked lines marked ✓. Use when the user has a recording (m4a/mp3/wav, any language Whisper supports, tuned on Polish) and says the transcript has made-up words, wrong speakers, wants who-said-what, wants to fix a transcript by listening, or needs exact quotes for a dispute. Trigger phrases: 'popraw transkrypcję', 'transkrypcja z podziałem na osoby', 'kto co powiedział', 'wymyślone słowa w transkrypcji', 'strona do poprawiania transkrypcji', 'fix the transcript', 'speaker labels', 'transcript review page', 'diarization', 'nagranie ze spotkania'."
metadata:
  version: 1.0.2
---

# Transcript review — noisy recording → checked transcript with speakers

Built and measured on 2026-10-22 on a 44-minute outdoor phone recording (5 people + a phone call on
loudspeaker, wind, crosstalk). Everything runs locally and is free. Paths below (`scripts/`,
`references/`) are relative to this folder. Measured numbers: [references/lessons.md](references/lessons.md).

**Needs:** a Mac with Apple Silicon (Parakeet runs on MLX), `uv`, `ffmpeg` and whisper.cpp
(`brew install uv ffmpeg whisper-cpp`), Chrome for the review page, and ~5 GB of disk for models
(downloaded on the first run to `~/whisper-models` and `~/asr-models`; override with `WHISPER_MODELS` /
`ASR_MODELS`).

**Core idea:** the person who was there is the only one who can make a line correct. Machines get the
text close, show where they are unsure, and shrink what the user has to listen to. Never "fix" a word
by guessing from context — in a dispute that is inventing evidence.

## Models that worked (use these)

| Role | Model / tool | Why |
|---|---|---|
| **Text** | Whisper **large-v3** (`ggml-large-v3.bin`, whisper.cpp ≥ 1.9.5, `brew install whisper-cpp`) on **lightly filtered** audio, chunks ≤ 28 s, beam 5, `--suppress-nst`, vocabulary `--prompt` | best of 16 combinations: 11.1% WER vs 15–48% for the rest |
| **Word timings** | NVIDIA **Parakeet-TDT-0.6B-v3**, MLX build (`parakeet-mlx==0.5.3`, `mlx-community/parakeet-tdt-0.6b-v3`) | Whisper's word times drift (10% off by > 1 s); Parakeet agrees with an independent timer within ±0.14 s |
| **Unsure-word flags** | Whisper large-v3 on raw audio, Whisper **large-v3-turbo** (raw), Parakeet (raw) | a word fewer than half of them heard is italic: flags 10% of words, catches ~61% of errors (Whisper's own confidence catches 32%) |
| **Speech regions** | pyannote **segmentation 3.0** via sherpa-onnx | finds where speech is; chunks are cut only there |
| **Voices** | 3D-Speaker **CAM++**, **ERes2NetV2** or **ERes2Net** via sherpa-onnx (the `voices` step tests all three on the checked lines and picks the best), averaged over the user's checked lines | 96–98% correct on held-out checked lines (49 lines: CAM++ 98%; 141 lines: all three 96.5–97.2%); WeSpeaker ResNet34 only 88% |
| **Audio filter** | ffmpeg `highpass=f=80,afftdn=nf=-25,dynaudnorm=f=150:g=15` | helps Whisper (14.9% raw → 11.1% filtered) |
| Listening only | DeepFilterNet `deep-filter` binary (optional, "cleaned audio" toggle on the page) | easier to hear for a person, but it **hurts every ASR model** — never feed it to ASR |

## Do not use (measured, all worse)

- DeepFilterNet audio for ASR: +10 to +17 points WER at full strength, +2 to +11 even with an 18 dB attenuation limit, for every model.
- Sheptooha (Polish w2v-BERT 2.0): best on its own benchmark, 38–48% WER here — drops far-field words.
- Combining models word by word (ROVER-style voting): 13.0% held-out vs 11.1% for large-v3 alone.
- Previous chunk's text added to the prompt: 14.7% vs 11.1%.
- `whisper-cli -mc 0` with `--prompt` (the prompt is silently ignored); whisper.cpp `--vad` (token times stay on the compressed timeline); large-v3 on a whole long file without chunking (invents YouTube outros on silence).
- Unsupervised diarization clusters as speakers (k = number of people merged two voices) — speakers come from the user's checked lines instead.

## Workflow

0. **Check where you are running first.** This only works in Claude Code on a Mac with Apple Silicon
   (`uname -sm` = `Darwin arm64`) with a shell you can run commands in. In claude.ai chat, Cowork, on Linux,
   Windows or an Intel Mac, tell the user that in one sentence and stop; don't start downloads.

Run each step from `scripts/`: `uv run --python 3.13 --with num2words==0.5.14 python tr.py <step> <workdir>`.
Use a **bash script file** for several steps in a row (zsh does not word-split `$CMD` variables).
Keep the workdir **outside any synced folder or git repository** (audio is ~100 MB per 45 min), e.g.
`~/asr-work/<name>/`.

1. **Ask the user** (one message): who was present (names as they should appear, up to 8), anyone who
   spoke only once or twice (→ `rare`, placed only where the user pins them), a phone call on speaker
   (→ `only_in` with its time windows), names/places/numbers likely to be said (→ `prompt`), and which
   moments matter most (→ `extra_passages`).
2. `init <workdir> --audio FILE`, then edit `project.json` (`language`, `prompt`, `speakers` with `key`/`name`,
   `rare`, `only_in`, `pins` `[s, e, key]` for lines the user already identified in chat).
3. `prepare` → `speech` → `chunks` → `asr` (≈ 15 min per 45 min of audio on an M4 Pro; first run downloads
   ~5 GB of models).
4. **Choose test passages**: 4 passages of ~60–90 s, about 4–5 min in total, covering the conditions —
   two people clearly, an argument/overlap, the phone call, and one key passage. Put them in
   `test_passages`; then `review`, and start `serve` **in the background** (it must keep running while the
   user works; the page autosaves to `corrections.json`). Open `http://127.0.0.1:8765/` in Chrome for the user.
5. **Explain the page in one short message** (see "Review page" below) and answer questions; expect them.
6. When the user says the test passages are done: back up `corrections.json`, run `score`. If another
   system beats `main`, set `"main"` in `project.json`. Report WER per system in plain words.
7. `voices` (compares voice models on the checked lines, writes `voices.json`), then `review` again —
   the extra passages now show predicted speakers. The user reviews as much as they want.
8. `build --out <notes folder>/<name>.md` (default `<workdir>/transcript.md`). Then compare any quotes
   already used elsewhere (notes, letters) with the checked text and report differences — do not silently
   edit those notes.

## Review page (what to tell the user)

One passage per tab, one player, one person per line.
- ▶ Play / `Esc` plays from the passage start; the line being played lights up; click a line's ▶ to play from it.
- Fix the words; `[?]` for what cannot be made out; reader notes in brackets, e.g. `[on the phone]`.
- New person mid-line: cursor there + `Enter` (rest moves to a new line), then click the coloured name
  or `Ctrl+1…8`. Join two lines: `Backspace` at the start of the lower one.
- `＋` adds a line below, 🗑 deletes, the time box takes `mm:ss.s`; "＋ line at current time" adds a line
  exactly where playback is paused. "Passage finished ✓" when the passage is right.

## Foot-guns (all hit on 2026-10-22)

- **The first page design was unusable** (✓ per line, alternatives under every line, "+ line below" with
  cut-and-paste). Keep the editor model: one person per line, Enter/Backspace, one finish button.
- **Timings**: re-time lines from Parakeet (monotonic match of the line's words; accept a move up to 12 s
  only with ≥ 2 matching words); never let a line's end run past the next line's start; highlight the
  line that started most recently. Play from 1 s before the first line to 3 s after the last.
- Chrome cannot play ALAC → the page uses FLAC. FLAC seeking in Chrome was measured exact (no drift).
- Never edit `corrections.json` while the page is open (the page overwrites it on the next save); change
  page code instead and ask the user to wait for "saved" and press ⌘R. The server refuses saves from an
  older page version. Copy `corrections.json` before every rebuild.
- large-v3 drops repeated phrases and short asides (a phrase said three times came out once; a two-word
  remark vanished) — exact counts and short remarks must be checked by ear.
- A checked passage replaces exactly the machine words the page showed for it (the page saves that span when it
  opens the passage; `data.json` lines carry `w0`/`w1`, the main model's own word times). The first version cut
  a time window around each passage and silently dropped words nobody had checked at 3 of 30 passage edges,
  because Whisper's word times drift. Machine words just outside a passage that the user typed anyway are
  dropped as repeats.
- Recordings of people are private by default: never publish the page, the transcript or the audio (no
  Artifact, no public URL). The server binds to 127.0.0.1 and refuses requests from other sites.

## Files

`scripts/tr.py` (all steps) · `scripts/speech.py` · `scripts/parakeet_asr.py` · `scripts/voices.py` ·
`scripts/review/review.html` + `review_server.py` · `references/lessons.md` (measurements) ·
`references/project.example.json`.
