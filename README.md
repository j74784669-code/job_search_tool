# Job search pipeline

A local pipeline for a targeted job search. It fetches open roles from
company career boards and from job aggregators, keeps the ones that match
your rules, remembers everything it has already seen, and can score the
remaining postings against a profile you write. You review the results in
a browser, in a desktop card window, or in a Markdown file.

Fetching and filtering are free. Scoring calls the Anthropic API and costs
money. Job text, scores, and your notes stay in SQLite on this machine.
The only outbound calls are the job sources you configure and, when you
score, Anthropic.

Run every command from the repository root.

Windows PowerShell:

```powershell
cd C:\path\to\job_search_tool
python -m app.main
```

macOS and Linux (Terminal, bash or zsh):

```bash
cd /path/to/job_search_tool
python3 -m app.main
```

Examples later in this file use `python`, which is the usual Windows
command. On macOS and Linux, use `python3` when `python` is not Python
3.10 or newer. The flags do not change.

`make` is the short form on macOS and Linux. The Makefile uses Bash. On
Windows, run `make` from Git Bash or WSL, or stay with `python -m` in
PowerShell. macOS needs the Xcode command-line tools (`xcode-select
--install`) before `make` is available. Debian and Ubuntu need `make`
from the `make` package when it is not already installed.

## What you need

- Python 3.10 or newer.
- For the browser board: Node.js and npm.
- For scoring: an Anthropic API key in `.env`.
- For Adzuna searches: a free Adzuna app id and key in `.env`. Remotive
  needs no key.

## First run

Windows PowerShell:

```powershell
python setup.py
```

macOS and Linux:

```bash
python3 setup.py
```

`setup.py` installs `requirements.txt`, creates
`data/ats_discovery.sqlite3` (table `ats_slug`) when that database is
missing, and copies these templates only when the destination is missing:

| Template | Created file | You edit it |
| --- | --- | --- |
| `.env.example` | `.env` | API keys |
| `profile.example.yaml` | `profile.yaml` | Your experience, used only when scoring |
| `filters.yaml.example` | `filters.yaml` | Which titles, locations, stacks, and ages to keep |
| `aggregators.yaml.example` | `aggregators.yaml` | Adzuna and Remotive searches |

It does not copy `gates.yaml`. It does not install the web app. It does
not overwrite a file or an `ats_slug` row you already have.

Then:

1. Put keys in `.env`. `ANTHROPIC_API_KEY` can wait until you score.
   `ADZUNA_APP_ID` and `ADZUNA_APP_KEY` can wait until you enable Adzuna.
2. Replace the placeholder text in `profile.yaml`.
   [`profile.sample.yaml`](profile.sample.yaml) is a fictional filled-in
   profile. [`profile.example.yaml`](profile.example.yaml) is only the
   shape.
3. Edit `filters.yaml` and `aggregators.yaml` for your search. The
   shipped examples target software-engineering titles in Canada, with
   Alberta cities called out. A first fetch that keeps nothing is usually
   `location_allow_patterns`. Details are in
   [docs/configuration.md](docs/configuration.md).
4. Add at least one board. `setup.py` creates an empty `ats_slug` table.
   How to insert a row is in [docs/companies.md](docs/companies.md).
5. Fetch, then look at what survived:

Windows PowerShell:

```powershell
python -m app.main
python -m app.inspect_job --rejected
```

macOS and Linux:

```bash
python3 -m app.main
python3 -m app.inspect_job --rejected
```

6. Score when the filtered set looks right.

Windows PowerShell:

```powershell
python -m app.ai_evaluate --dry-run
python -m app.ai_evaluate --limit 20
```

macOS and Linux:

```bash
python3 -m app.ai_evaluate --dry-run
python3 -m app.ai_evaluate --limit 20
```

7. Open the board.

Windows PowerShell:

```powershell
cd web
npm install
cd ..
$env:DB_PATH = (Resolve-Path .\data\seen_jobs.sqlite3)
npm --prefix web run dev
```

macOS and Linux:

```bash
cd web
npm install
cd ..
make web
```

`make web` sets `DB_PATH` to `data/seen_jobs.sqlite3` and starts the dev
server. The same start without `make`:

```bash
DB_PATH="$(pwd)/data/seen_jobs.sqlite3" npm --prefix web run dev
```

Open http://localhost:3000.

## What each step does

1. **Fetch** — `python -m app.main`. Reads boards from `ats_slug` where
   `available = 1` and the board type has a fetcher, and reads searches
   from `aggregators.yaml`. Fetchers: Greenhouse, Ashby, Workable, Lever,
   SmartRecruiters, and Workday.
2. **Filter** — `app/filters.py` applies `filters.yaml`: title, location,
   posting age, then stack. A job that fails is still stored.
3. **Dedup** — `app/dedup.py` writes `data/seen_jobs.sqlite3`. A job is
   new only when both the URL and the normalized
   `company::title::location` key are unseen. Later runs skip both.
4. **Score** — `python -m app.ai_evaluate` (optional, paid). Scores
   `passed_filters = 1` rows that have no `ai_evaluations` row yet.
5. **Check the scores** — `python -m app.fit_validate` (optional). You
   label job descriptions, then the tool compares those labels with the
   stored scores.
6. **Review** — the Next.js app in `web/`, or one card at a time with
   `python -m app.review_ui`.
7. **Digest** — `python -m app.digest` rewrites `data/digest.md`.

Guides:

- [Configuration](docs/configuration.md)
- [Fetch, filter, and inspect](docs/fetch-and-filter.md)
- [Scoring](docs/scoring.md)
- [Review board, desktop cards, and digest](docs/review.md)
- [Checking scores against your labels](docs/checking-scores.md)
- [Company boards and discovery](docs/companies.md)

## Three different score lines

These numbers are independent. Changing one file does not change the others.

| Line | Where | What it does |
| --- | --- | --- |
| **45** | Digest and the desktop cards (`app/digest.py` `MIN_MATCH_SCORE`) | Include a job when it passed filters, has a score, the score is at least 45, and your status is not applied or skipped. |
| **55** | Scorer console, and the default fit-check cutoff | The console prints a score of 55 or higher on the kept line and prints `Job Rejected` below that. The row is still saved. The fit check uses 55 unless you pass `--cutoff`. |
| none | Web board | Every `passed_filters = 1` row, including unscored jobs and jobs you marked applied or skipped. |

`Makefile` comments still mention 55 for the digest. `make digest` runs
`python -m app.digest`, which uses 45.

## Two different status words

The model recommendation and your own status are stored apart.

| | Stored values | Where you set it |
| --- | --- | --- |
| AI recommendation | `apply`, `consider`, `skip` | Scoring writes this. The board shows "Not evaluated" when the row has no score. |
| Your status | `applied`, `interview`, `rejected`, `skipped`, `silence` | Board, desktop cards, or the digest. |

`applied` means you applied. `skipped` means it is not a fit. Those two
drop a job from the digest and from the desktop cards. Interview,
rejected, and silence stay in both.

## Commands

| Command | What you get |
| --- | --- |
| `python setup.py` | Dependencies, missing config files, empty `ats_slug` table. |
| `python -m app.main` | Fetch, filter, dedup. Appends passers to `data/candidates.csv`. |
| `python -m app.refilter` | Re-applies `filters.yaml` to jobs already stored. |
| `python -m app.inspect_job <url>` | One stored job, including the description and why it was filtered out. |
| `python -m app.ai_evaluate` | Scores unscored jobs that passed filters. Rewrites `data/scored_candidates.csv`. |
| `python -m app.fit_validate` | Draws a sample if needed, then asks you to label each description. |
| `python -m app.review_ui` | Desktop cards for the same jobs the digest includes. |
| `python -m app.digest` | Rewrites `data/digest.md`. |
| `python -m pytest app/ -q` | Test suite. No live job APIs and no Anthropic calls. |

Flags, prompts, and files for each command are in the docs linked above.

### Make targets

On macOS and Linux these targets are the normal way to run each step.
`make` with no target runs `make run`. Each target calls `python`, so
`python` on your `PATH` must be Python 3.10 or newer. If only `python3`
exists, run the `python3 -m` form from the tables above.

| Target | Runs | Extra behavior |
| --- | --- | --- |
| `make setup` | `python setup.py` | |
| `make run` | `python -m app.main` | Asks whether to skip boards, aggregators, or discovery, and whether to limit the run to one slug. |
| `make evaluate` | `python -m app.ai_evaluate` | Asks whether to dry-run and whether to set `--limit`. It does not pass `--gates`. |
| `make web` | `npm --prefix web run dev` | Sets `DB_PATH` to `data/seen_jobs.sqlite3`. |
| `make digest` | `python -m app.digest` | Reads Applied and Skipped edits in an existing digest, then writes the file again. |
| `make validate` | `python -m app.fit_validate` | Sample if needed, then label. |
| `make test` | `python -m pytest app/ -q`, then three test modules as scripts | |

Some tests call the filters loaded from the `filters.yaml` in the repo
root. After you change title or location rules, those tests can fail
while the fetchers are fine.

## Layout

```text
app/                  pipeline commands (run as python -m app.<name>)
app/scripts/          one-off diagnostics; not part of a normal run
ats-expansion/        Common Crawl discovery and board vetting
web/                  Next.js review board
data/                 local databases and exports (gitignored)
```

`companies.yaml` is not read. `companies.yaml.example` only shows the old
entry shape and the Workday slug format.

## License

[MIT](LICENSE)
