# Checking scores

`python -m app.fit_validate` compares stored fit scores with labels you
enter. Labels are the ground truth for this tool. A later change to the
prompt, the profile, or the production scores does not rewrite them.

You can skip this entirely and still fetch, score, and review.

The default sample cutoff is **55**, with a margin of 10. That cutoff is
the fit-check cutoff. The digest line stays 45.

## Label

From the repo root, with scored jobs already in the database.

Windows PowerShell:

```powershell
python -m app.fit_validate
```

macOS and Linux:

```bash
python3 -m app.fit_validate
make validate
```

`make validate` runs in Terminal on macOS and Linux, and from Git Bash or
WSL on Windows. A run with no subcommand is the `label` command. It draws
a sample the first time, then opens each description.
Later runs resume the unlabeled rows for the same sample settings.

While you label, the card shows the title, the location, and the
description in Markdown. It hides the company, the URL, the sample
stratum, and the model score.

| Input | Meaning |
| --- | --- |
| `1` or `strong no` | Strong no. Would not apply. |
| `2` or `n` | No. Would not apply. |
| `3` or `m` | Maybe. A stretch you might still apply to. |
| `4` or `y` | Yes. Would apply. `y` is yes, not strong yes. |
| `5` or `sy` | Strong yes. Would apply. |

A note can follow the label: `4 the domain matches`. A bare 0–100 number
is rejected, so a score is not stored as a label.

`s` skips the card for now. `b` goes back. `q` stops. Progress is saved
as you go.

Windows PowerShell:

```powershell
python -m app.fit_validate label --revise
```

macOS and Linux:

```bash
python3 -m app.fit_validate label --revise
```

`--revise` walks labels you already saved so you can change them.

Yes and strong yes count as would apply. No and strong no count as would
not. Maybe is the swing label. The report's default is to count maybe as
would not (`--maybe-as reject`). When you want the apply-side count,
including maybes you might apply to, pass `--maybe-as accept`.

## How the sample is drawn

Windows PowerShell:

```powershell
python -m app.fit_validate sample
python -m app.fit_validate sample --redraw
```

macOS and Linux:

```bash
python3 -m app.fit_validate sample
python3 -m app.fit_validate sample --redraw
```

The default draw is:

| Setting | Default | Flag |
| --- | --- | --- |
| Cutoff | 55 | `--cutoff` |
| Margin around the cutoff | 10 | `--margin` |
| Stratified sample size | 80 | `--target` |
| Random controls | 20 | `--random-size` |
| Draw seed | 0 | `--seed` |
| Split seed | 0 | `--split-seed` |
| Tuning fraction | 50% | `--tuning-percent` |
| Share of the low stratum that is above the floor | 50% | `--low-not-floor-percent` |

Scores within 10 points of 55 are the near band (45 through 65). Above
that is high. Below that is low. The 80 stratified rows are about 60%
near, 20% high, and 20% low. A short stratum is not filled from another
stratum. The 20 random rows are a separate control, drawn from whatever
scored jobs remain.

The stratified rows and the random rows are split in half with
`--split-seed`. One half is tuning. The other is held out. The split stays
fixed until you pass `sample --redraw`, which draws again and resets it.

Only the random control is an overall accuracy figure. Near, high, and
low numbers describe those bands. Held-out results are for a final look.
Do not edit the prompt or the profile from the held-out text.

These flags are accepted by every subcommand. The sample id is derived
from them, so a different `--cutoff` or `--seed` is a different sample.

`--db` defaults to `data/seen_jobs.sqlite3`. `--profile` defaults to
`profile.yaml`. `--gates-file` defaults to `gates.yaml`.

## Report

Windows PowerShell:

```powershell
python -m app.fit_validate report
python -m app.fit_validate report --held-out
python -m app.fit_validate report --maybe-as accept
python -m app.fit_validate history
```

macOS and Linux:

```bash
python3 -m app.fit_validate report
python3 -m app.fit_validate report --held-out
python3 -m app.fit_validate report --maybe-as accept
python3 -m app.fit_validate history
```

`report` prints the tuning half and saves that report. `--held-out`
prints the other half. The report includes agreement, a weighted error,
noise when you have measured it, and sanity checks.

Weighted error counts a false negative as 3 times a false positive. The
default weight is `--fn-weight 3`.

A disagreement is either a cutoff conflict (you would apply and the score
is under the cutoff, or you would not and the score is at least the
cutoff) or a rank gap: the score's percentile and the label's percentile
differ by more than `--rank-gap` (default 0.40). Label percentiles are
0.1, 0.3, 0.5, 0.7, and 0.9 for strong no through strong yes.

Sanity checks:

- A clear-high score (above cutoff + margin) labeled no or strong no is a failure.
- A clear-low score (below cutoff − margin) labeled yes or strong yes is a failure.
- Maybe is never a sanity failure.

`history` lists reports saved for this sample.

## Tag a disagreement

Windows PowerShell:

```powershell
python -m app.fit_validate tag
python -m app.fit_validate tag --revise
python -m app.fit_validate tag --held-out
```

macOS and Linux:

```bash
python3 -m app.fit_validate tag
python3 -m app.fit_validate tag --revise
python3 -m app.fit_validate tag --held-out
```

One cause per disagreement on the tuning half:

| Input | Cause |
| --- | --- |
| `1` | Profile gap |
| `2` | Rubric weighting |
| `3` | Hallucination |
| `4` | Hard constraint |
| `5` | Other, and a note is required |

`s` skips, `b` goes back, `q` quits. `--held-out` prints a banner reminding
you not to edit the prompt or the profile from those rows.

Use the tag counts to decide what to change. Profile gaps point at
`profile.yaml`. Rubric weighting and hallucination point at the scoring
prompt. Hard constraints point at `gates.yaml`. Add a gate after labels
show a constraint the score missed. An empty `gates.yaml` means gating is
off.

## Gates on the sample

Windows PowerShell:

```powershell
python -m app.fit_validate gates
```

macOS and Linux:

```bash
python3 -m app.fit_validate gates
```

This records pass/fail for every job in the sample against the current
`gates.yaml`. The next report can show the metrics with those results.
If you edit the file and skip this command, the report tells you the
checks are not recorded for the current gate version. Gate fields are
documented in [Configuration](configuration.md).

## Noise

Noise is a paid repeat of scoring. It does not write `ai_evaluations`.

Windows PowerShell:

```powershell
python -m app.fit_validate noise
python -m app.fit_validate noise --yes
python -m app.fit_validate noise --force
```

macOS and Linux:

```bash
python3 -m app.fit_validate noise
python3 -m app.fit_validate noise --yes
python3 -m app.fit_validate noise --force
```

The default measures 12 scored descriptions, 5 times each, with no score
cache: 60 model calls. `--noise-count` and `--noise-runs` change the
size. The command prints the call count and asks before spending the
money. `--yes` skips the question. `--force` discards repeats already
stored for this prompt and profile version.

A large spread relative to the margin means a score near 55 can flip
sides without any change to the prompt. Read that before treating a small
accuracy change as real.

## Pin and rescore

Both update fit-check snapshots. Neither replaces production scores, the
digest, or the web board.

Windows PowerShell:

```powershell
python -m app.fit_validate pin
python -m app.fit_validate rescore
python -m app.fit_validate rescore --held-out
python -m app.fit_validate rescore --yes
```

macOS and Linux:

```bash
python3 -m app.fit_validate pin
python3 -m app.fit_validate rescore
python3 -m app.fit_validate rescore --held-out
python3 -m app.fit_validate rescore --yes
```

`pin` copies the current production scores into snapshots for this sample,
bound to the current prompt version and profile version.

`rescore` calls the model again and stores the new scores in
`fit_score_snapshots`. The default is the tuning half. `--held-out`
includes the held-out half as well. It asks before spending money unless
you pass `--yes`.

Prompt version is a 12-character hash of the system prompt, the response
schema, `ANTHROPIC_MODEL`, and the user-prompt builder. Profile version is
a hash of the `profile.yaml` bytes. A report is tied to those versions so
you can tell which prompt and profile the numbers came from.

## Suggested order

1. `python -m app.fit_validate` (or `python3 -m app.fit_validate`) and label the sample.
2. `report`, adding `--maybe-as accept` when you want maybes counted as would apply.
3. `noise` once, so you know the spread.
4. `tag` on the disagreements you care about.
5. Change the profile, the prompt, or `gates.yaml` from the tuning tags.
6. `pin` or `rescore` the tuning half, then run `report` again.
7. Look at `--held-out` after the tuning report is one you would keep.
