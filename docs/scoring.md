# Scoring

`python -m app.ai_evaluate` sends each unscored candidate and your
`profile.yaml` to Claude. The model returns a fit score from 0 to 100, a
recommendation of `apply`, `consider`, or `skip`, and three text fields:
transferable strengths, genuine gaps, and risk factors.

This costs money. The default model is `claude-haiku-4-5`. Set
`ANTHROPIC_MODEL` in `.env` to use another Claude model id.

On macOS and Linux, use `python3` in place of `python` below. `make
evaluate` is the interactive form of a score run. It calls `python` from
`PATH`.

## What gets scored

A job is queued when all of these are true:

- `job_details.passed_filters = 1`
- there is no `ai_evaluations` row for that URL

The queue has no sort. `--limit` keeps the first N rows the query returns.
A job you later demote with `python -m app.refilter` keeps its score.
A rescued job with no score joins the next queue.

Descriptions are converted to Markdown before they are sent. A description
that looks truncated (very short, or ending in an ellipsis) is sent with a
note that tells the model not to invent gaps from missing sections.

## Commands

Windows PowerShell:

```powershell
python -m app.ai_evaluate --dry-run
python -m app.ai_evaluate --limit 20
python -m app.ai_evaluate --limit 20 --gates
python -m app.ai_evaluate
```

macOS and Linux:

```bash
python3 -m app.ai_evaluate --dry-run
python3 -m app.ai_evaluate --limit 20
python3 -m app.ai_evaluate --limit 20 --gates
python3 -m app.ai_evaluate
```

| Flag | Effect |
| --- | --- |
| `--dry-run` | Print the queue. No API call, no key required, no database write. |
| `--limit N` | Score at most N queued jobs this run. |
| `--gates` | Load `gates.yaml`, record each failure, and skip the model for that job. |

`make evaluate` asks whether you want a dry run (yes unless you answer
`n`) and an optional limit. It never passes `--gates`. On macOS and Linux,
run it in Terminal. On Windows, run it from Git Bash or WSL.

`--dry-run` still loads `profile.yaml`. With `--gates`, a missing
`gates.yaml` exits before the preview when the queue is not empty. An
empty queue exits immediately, before the gates file is checked.

Dry-run lines:

```text
WOULD EVALUATE | Acme                 | Backend Engineer
WOULD GATE | seniority | Intern
```

A real run prints one line per job and commits that row before the next
call, so a crash keeps the scores already paid for. A score of 55 or
higher is printed as:

```text
[1/20]  72 consider   | Acme                 | Backend Engineer
```

A lower score is printed as `Job Rejected` plus the title, company, and
score. That word is console output. The row is saved either way. The
digest includes scores from 45 up. The web board includes every filtered
job. See the table in the [README](../README.md).

A model error prints `[WARN]` and continues with the next job. That job
stays unscored, so the next run tries it again.

At the end the command rewrites `data/scored_candidates.csv` with every
stored evaluation, highest score first. Columns: `match_score`,
`recommendation`, `company`, `title`, `location`, `transferable_strengths`,
`genuine_gaps`, `risk_factors`, `url`, `posted_at`.

## Gates during scoring

Copy `gates.yaml.example` to `gates.yaml` and edit it. Field rules are in
[Configuration](configuration.md).

Windows PowerShell:

```powershell
python -m app.ai_evaluate --gates
```

macOS and Linux:

```bash
python3 -m app.ai_evaluate --gates
```

A failed gate prints `Gated out | <gate name> | <title>` and does not call
the model. The result is stored in `fit_gate_results`. The job remains
unscored, so a later run without `--gates` will send it to the model.
A later run with `--gates` evaluates the gates again.

`make evaluate` will not apply gates. Pass `--gates` yourself.

## Score a job again

`save_evaluation` replaces an existing row, but the queue only selects
URLs that have no row. There is no rescore-all command.

To score one URL again, delete its `ai_evaluations` row, then run the
scorer:

Windows PowerShell:

```powershell
python -c "import sqlite3; c=sqlite3.connect(r'data/seen_jobs.sqlite3'); c.execute('DELETE FROM ai_evaluations WHERE url = ?', ('https://example.com/jobs/123',)); c.commit()"
python -m app.ai_evaluate --limit 1
```

macOS and Linux:

```bash
python3 -c "import sqlite3; c=sqlite3.connect('data/seen_jobs.sqlite3'); c.execute('DELETE FROM ai_evaluations WHERE url = ?', ('https://example.com/jobs/123',)); c.commit()"
python3 -m app.ai_evaluate --limit 1
```

Deleting the evaluation does not delete your status, your notes, or any
fit-check label.

`python -m app.fit_validate rescore` writes a snapshot for the fit report.
It does not replace `ai_evaluations` and it does not change the digest.
Use it when you are measuring a prompt or profile change, which is
covered in [Checking scores](checking-scores.md).

## What the model is asked

The system prompt asks for functional fit against the profile, not a
keyword match on past job titles. The reply has to include `match_score`,
`recommendation`, `genuine_gaps`, `transferable_strengths`, and
`risk_factors`. Recommendation is one of `apply`, `consider`, and `skip`.

That recommendation answers "does this look worth an application". Your
own status answers "what did I do". Set your status in the review tools,
not by editing the score.
