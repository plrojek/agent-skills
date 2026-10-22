# Measurements behind the transcript-review skill (2026-10-22)

Recording: 44:25, one phone microphone outdoors, ALAC 48 kHz mono, five people plus one side of a phone
call on loudspeaker; wind, walking, crosstalk. Reference: four passages (4.5 min, 530 words, 50 lines)
corrected by ear by a person who was present, using the review page. Caveat: the corrections started
from the large-v3 + filter text, which tilts the comparison slightly towards that system.

## Text: 16 system × audio combinations (WER on the reference passages)

| System | raw | light ffmpeg filter | DeepFilterNet (full) | DeepFilterNet (−18 dB limit) |
|---|---|---|---|---|
| Whisper large-v3 (whisper.cpp, beam 5, prompt) | 14.9 | **11.1** | 27.9 | 19.6 |
| Whisper large-v3-turbo | 17.4 | 19.2 | 31.5 | 19.8 |
| Parakeet-TDT-0.6B-v3 (MLX) | 20.6 | 22.6 | 33.0 | 31.5 |
| Sheptooha (w2v-BERT 2.0 + KenLM, Polish) | 42.6 | 38.5 | 48.3 | 47.0 |

- large-v3 + filter: 31 wrong + 28 missing words of 530.
- Word-by-word combination of 4 systems, tuned on 3 passages and tested on the 4th: 13.0% (single best 11.1%).
- large-v3 with the previous chunk's text appended to the prompt: 14.7%.

## Flagging doubtful words (large-v3 output, 506 words, 31 wrong)

| Rule | Flags | Flagged that are wrong | Errors caught |
|---|---|---|---|
| Whisper token confidence < 0.35 | 8% | 26% | 32% |
| Whisper confidence < 0.5 | 16% | 21% | 55% |
| No other model heard it (turbo, Parakeet) | 8% | 42% | 55% |
| **Fewer than 2 of 4 other models heard it** (used) | 10% | 39% | 61% |
| Confidence < 0.5 or fewer than 2 of 4 | 21% | 23% | 77% |

No rule is safe for replacing words with "[unintelligible]" automatically: even the strictest one
(both conditions) flags words that are right 56% of the time.

## Timings

- Whisper token offsets (no DTW; `-dtw` returned `t_dtw: -1`) vs Parakeet: 80% within ±0.6 s, 10% off by > 1 s,
  some lines off by ~6 s.
- Parakeet vs Sheptooha (two independent timers): 80% within ±0.14 s, 2% off by > 1 s.
- Chrome seeking in the FLAC (no seek table): playback position exact at 5, 15, 25, 35 and 43 min
  (constant 80 ms = capture latency, no drift).

## Speakers

- Leave-one-out on 49 checked lines (≥ 1 s): CAM++ 98%, ERes2Net 96%, ERes2NetV2 96%, WeSpeaker ResNet34 88%.
- Leave-one-out on 141 checked lines (all reviewed passages): CAM++ 96.5%, ERes2NetV2 97.2%, ERes2Net 97.2% — equivalent; let `voices` pick.
- Voice similarity between people can be high (0.49–0.70 cosine among three of the six voices); people who
  spoke once or twice must be restricted to the lines the user pinned, otherwise they absorb a minute of
  someone else's speech.
- Unsupervised clustering with k = number of people merged the two people closest to the phone.

## Building the transcript

- Removing machine words by a time window around each checked passage (passage bounds ± 0.3 s) dropped words
  nobody had checked at 3 of 30 passage edges (1, 2 and 3 words; each heard by both Whisper and Parakeet).
  Cause: Whisper's word times drift, so the first words after a passage fell inside the window. Fixed by replacing
  exactly the words the page showed.

## Effort

- Compute on an M4 Pro (48 GB): DeepFilterNet 1.5 min, Whisper large-v3 batched ≈ 5 min per 32 min of
  speech, turbo ≈ 2 min, Parakeet ≈ 1.5 min, voices ≈ 1 min, scoring ≈ 10 s.
- User time: test passages ≈ 30–40 min for 4.5 min of audio (including learning the page); 11 extra
  passages (8 min of audio) about an hour.
