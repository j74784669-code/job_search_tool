# AGENTS.md

Local job-search pipeline. Workspace: `C:\Users\seanj\projects\job_search_tool`. Run every Python command from that root (`python -m app.…`). Host is Windows PowerShell: no `&&`; `Makefile` sets `SHELL := /bin/bash` and uses `read`, so prefer the `python -m` forms. `web/AGENTS.md` is Next's generated file for `web/` only. Do not put personal identity, employers, pay, or locations in this file; it is not gitignored.

Gitignored `ai-context.md` holds the last scoring/profile decisions. Read it when the task is scoring, the digest cutoff, or `profile.yaml`. It drifts. If it disagrees with the code, trust the code.

## Pipeline

1. Fetch — `python -m app.main`. Boards: `data/ats_discovery.sqlite3` `ats_slug` where `available = 1` and `ats_board` is in `app/ats_clients.py` `FETCHERS`. Aggregators: gitignored `aggregators.yaml`. Flags: `--company SLUG`, `--skip-aggregators`, `--skip-companies`, `--skip-discovery`.
2. Filter — `app/filters.py` against gitignored `filters.yaml` (title, location, stack, posting age). `max_posting_age_days` drops a posting known to be older than that many days. A missing or unreadable `posted_at` is kept. Workday `Posted N+ Days Ago` fails only when that floor is already past the limit. Null or a missing key turns the age check off. Logic is occupation-agnostic. The shipped example and the local file are software-engineering shaped. A first run that returns nothing is usually `location_allow_patterns`.
3. Dedup — `app/dedup.py` → `data/seen_jobs.sqlite3`. A job is new only if both the URL and the normalized `company::title::location` key are unseen. Seen jobs are stored even when they fail the filter.
4. Score — `python -m app.ai_evaluate` (paid). Needs `ANTHROPIC_API_KEY` and gitignored `profile.yaml`. Default model `claude-haiku-4-5` (`ANTHROPIC_MODEL`). Scores only `passed_filters = 1` rows with no `ai_evaluations` row. `save_evaluation` is `INSERT OR REPLACE`. There is no rescore-all command; delete the row to score again. `--dry-run`, `--limit N`. `--gates` records `gates.yaml` failures and skips the model call. Without `--gates`, scoring ignores that file. Console prints `match_score >= 55` as kept and the rest as `Job Rejected`. That print is not the digest rule.
5. Fit check — `python -m app.fit_validate` (optional). See below.
6. Review — `web/` Next.js on the same SQLite file. `make web` sets `DB_PATH` to `data/seen_jobs.sqlite3`. Desktop cards: `python -m app.review_ui` (one at a time). Same inclusion as the digest: `passed_filters = 1`, `match_score >= 45`, and `my_status` is not `applied` or `skipped`. Applied and Skipped checkboxes are exclusive. Confirm writes the mark and notes, then drops that card. Clearing both clears only those two statuses.
7. Digest — `python -m app.digest` writes gitignored `data/digest.md`.

`python setup.py` installs `requirements.txt`, copies `.env` / `profile.yaml` / `filters.yaml` / `aggregators.yaml` only when missing, and creates `ats_slug` without overwriting rows. It does not copy `gates.yaml`.

## Data

| Path | Role |
| --- | --- |
| `data/ats_discovery.sqlite3` | Company registry. Table `ats_slug`. |
| `data/seen_jobs.sqlite3` | Jobs, scores, `user_status`, fit-validation tables. |
| `data/candidates.csv` | Lean append-only fetch log. Descriptions are not here. |
| `data/scored_candidates.csv` | Scored export, score descending. |
| `companies.yaml.example` | Old entry shape. The pipeline does not read `companies.yaml`. |

`ats_slug`: `slug`, `ats_board`, `available INTEGER DEFAULT 1`, `last_seen`, `discovery_time`, `name`. PK `(slug, ats_board)`. Discovery is `INSERT OR IGNORE`. Company dict is `{name, ats, slug}`; `name` falls back to `slug`.

`seen_jobs` tables the board uses: `job_details` (PK `url`; `passed_filters`, `description`, `source`), `ai_evaluations` (PK `url`; `match_score`, `recommendation` apply/consider/skip, gaps/strengths/risks), `user_status` (PK `url`; `my_status`, `notes`). Status values: `applied`, `interview`, `rejected`, `skipped`, `silence`. AI recommendation and `my_status` are different vocabularies. Fit tables (`fit_sample_sets`, `fit_samples`, `fit_labels`, `fit_label_history`, `fit_noise_runs`, `fit_score_snapshots`, `fit_disagreement_tags`, `fit_gate_results`, `fit_reports`) live in the same file. Deleting an evaluation does not delete labels or status.

Open YAML and CSV with `encoding="utf-8"`. Windows cp1252 raises on non-ASCII. Quote YAML names that are boolean tokens (`On`).

## Three different "cutoffs"

- Digest (`app/digest.py` `MIN_MATCH_SCORE`): **45**. Includes a scored job iff `passed_filters = 1`, score is not null, score `>= 45`, and `my_status` is not `applied` or `skipped`. Highest score first. Interview, rejected, and silence stay. The web board does not apply this gate.
- Scorer stdout and `fit_validate` sample default: **55**. Do not change the digest line to match the print, or the print to match the digest, unless asked.
- Web `getJobs`: every `passed_filters = 1` row, including unscored, applied, and skipped. Sort is score descending (nulls last in SQLite).

`Makefile` `digest` comment still says 55. The code is 45.

Digest status writes: edit `My status:` then rerun, or `python -m app.digest --applied/--skipped/--restore URL`. `Not a good fit` maps to skipped. `--restore` clears only applied/skipped and keeps notes. Marks live in `user_status`, so a new score does not clear them. The digest is rebuilt from the DB; it is not the source of truth.

When recounting labels, this user treats **maybe as a weak yes** (a stretch they might apply to). The report default is still `--maybe-as reject`. Do not change that default. Use `--maybe-as accept` when they ask for the apply-side count.

## Descriptions

`job_details.description` is stored as received. Greenhouse is often entity-escaped HTML (`&lt;p&gt;`), not double-escaped. `app/html_to_markdown.py` `html_to_markdown(text) -> str` is the only Markdown converter (BeautifulSoup + markdownify). Non-HTML returns unchanged, including `vector<int>` and a bare `Q&amp;A`. Real tags are cleaned and converted. If there are no real tags, unescape **once** and convert only if that reveals tags. A second full-string unescape breaks `&amp;quot;` / `&amp;amp;` inside attributes. Strip `script`/`style`/`noscript`/`svg`/`iframe`, editor attributes, tracking pixels, and embedded data images before conversion. Keep `href`/`src`/`alt`.

`filters.strip_html` stays for `looks_truncated`, `jd_stack_mismatch`, and aggregator callers. `digest` flattens to plain text, not Markdown. The fit-label card and the scorer pass descriptions through `html_to_markdown`.

## ATS

`FETCHERS`: `greenhouse`, `ashby`, `workable`, `lever`, `smartrecruiters`, `workday`. Each job is `{company, title, location, url, posted_at, description}` plus `source`. Adding a company on an existing board is an `ats_slug` row, not a new client. A new vendor is a new fetcher. SmartRecruiters has a fetcher and is **not** in the Common Crawl discovery query.

Discovery and vetting are `ats-expansion/`, not `app/`:

```text
python ats-expansion/ats_discovery.py [CRAWL]
python ats-expansion/expand_companies.py
```

Default crawl id is in `ats_discovery.py` (`CC-MAIN-2026-39` unless the source says otherwise). One parquet pass, insert-only. Per-file caches are deleted only after a successful insert. Non-ASCII slugs and board names are rejected. Vetting checks each `available = 1` slug only against its own board. Success sets `last_seen` and leaves `available = 1`. Failure sets `available = 0` and leaves `last_seen`. Network errors and HTTP 429/5xx wait 10 seconds, up to 4 tries.

`python -m app.main` does the same `available = 0` update (last_seen unchanged) when any fetcher gets HTTP 404 or 410 (`ats_clients.BoardGone`). A 429 or 5xx leaves the row available. Workable list calls wait at least 1 second apart and retry 429 up to 4 times, using `Retry-After` when it is a number of seconds (capped at 60, otherwise 10).

Slug rules: Greenhouse, Lever, and Workable lowercased. Ashby keeps the first spelling. Lever vetting is `api.lever.co`, then `api.eu.lever.co` once on 404; body is a JSON list. Workday slug is `{tenant}.{wdN}/{site}` (tenant and `wdN` lowercased, site spelling kept). List is POST size 20 to `https://{tenant}.wd{N}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs` with `{"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": ""}`, stop at `total` or offset 2000; 404 retries once on `wd{N}.myworkdaysite.com`. Stored URL is `https://{tenant}.wd{N}.myworkdayjobs.com/{site}{externalPath}`. Detail GET (`jobPostingInfo.jobDescription`, `startDate`) runs only after title and location filters pass; failure keeps the job with an empty description and list `postedOn`.

`app/discover_companies.py` can insert a board found via an Adzuna redirect. `app/aggregator_clients.py`: Adzuna (`ADZUNA_APP_ID`, `ADZUNA_APP_KEY`) forwards every params key except `max_pages`. Remotive needs no key. `aggregators.yaml` is a top-level `aggregators:` list; a nested Remotive item breaks PyYAML.

## Fit validation

`app/fit_validate.py`. Labels are ground truth and are not rewritten when the prompt, profile, or production scores change. Card shows title, location, and the markdown description. It hides company, URL, stratum, and model score. Keys: `1`/`sn` strong no, `2`/`n` no, `3`/`m` maybe, `4`/`y` yes (`y` is yes, not strong yes), `5`/`sy` strong yes. Ordinals 0–4, expected percentiles 0.1, 0.3, 0.5, 0.7, 0.9. Yes and strong yes = would apply. No and strong no = would not. `s` skip, `b` back, `q` stop. A bare 0–100 number is rejected.

No-arg run samples (if needed) then labels. Subcommands: `sample`, `label`, `report` (`--held-out`, `--maybe-as accept|reject`), `tag`, `noise` (paid, asks first; does not write `ai_evaluations`), `rescore` (snapshot only; does **not** replace production scores or the digest), `pin`, `gates`, `history`. Default sample: cutoff 55, margin 10, target 80, random 20, seed 0, split seed 0, tuning 50%. Short strata are not backfilled. The tuning/held-out split stays fixed unless `sample --redraw`. Only the random control may be called overall accuracy. Held-out text is not for prompt or profile edits. Weighted error counts a false negative as 3× a false positive. Disagreement: cutoff conflict, or score percentile more than `--rank-gap` (0.40) from the label percentile. Tag causes: profile gap, rubric weighting, hallucination, hard constraint, other (note required). Sanity: clear-high labeled no/strong no, or clear-low labeled yes/strong yes. Maybe is not a sanity failure.

`rescore` writes `fit_score_snapshots` for the tuning half unless `--held-out`. `pin` copies current production scores into snapshots. Prompt version is a 12-char hash of `SYSTEM_PROMPT`, the schema, `ANTHROPIC_MODEL`, and `build_user_prompt`. Profile version hashes `profile.yaml` bytes. Do not replace production `ai_evaluations` from a snapshot unless asked. Do not score new jobs against a profile hash that `ai-context.md` says was reverted.

`gates.yaml` is optional, gitignored, and not a second `filters.yaml`. Absent means gating is off. Do not create it before labels show hard-constraint misses. Fields: `location_allow|deny`, `title_allow|deny`, `description_allow|deny`. Case-insensitive regex. In double-quoted YAML write `\\b`. Description text is markdown. Gates run in order and stop at the first failure. Editing the file changes `gate_version`; rerun `python -m app.fit_validate gates`.

## Web

Next 16 + React 19 + `better-sqlite3`. Before editing `web/`, read the matching guide under `web/node_modules/next/dist/docs/`. `web/lib/db.ts` opens `DB_PATH` or `../data/seen_jobs.sqlite3` relative to the `web/` cwd. `GET /api/jobs` is `force-dynamic` + `noStore` + `Cache-Control: no-store`. `POST /api/status` body `{url, my_status, notes}`. Do not cache job JSON. `web/lib/formatDescription.ts` must keep the same real-HTML vs once-unescaped-HTML vs plain-text split as the Python converter.

## Tests and publish

`python -m pytest app/ -q`. `app/tests/test_fit_validate.py` does not call Anthropic. Local `filters.yaml` makes aggregator and SmartRecruiters tests fail on title/location gating (empty descriptions, wrong detail-call counts). Those failures are the personal filter file. Workday tests stub `title_is_relevant` and `location_is_allowed` for that reason. Do not "fix" them by editing `filters.yaml` or loosening production filters.

Never commit `.env`, `profile.yaml`, `filters.yaml`, `aggregators.yaml`, `gates.yaml`, `companies.yaml`, or `data/` (job history and `cover_letter.md`). `profile.example.yaml` is an empty outline. `profile.sample.yaml` is the fictional filled profile. A separate publish tree may exist at `C:\Users\seanj\projects\job-search-automation`; it is not this checkout's git repo. Do not copy `seen_jobs.sqlite3` into it.
