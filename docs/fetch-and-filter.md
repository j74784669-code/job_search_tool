# Fetch, filter, and inspect

Run these from the repository root after `python setup.py` and after
`filters.yaml` matches the search you want. Company boards have to be in
`data/ats_discovery.sqlite3` first. An empty registry fetches only the
aggregators. See [Companies](companies.md).

On macOS and Linux, `python3` replaces `python` in the blocks below, or
you can use the `make` target when one is listed.

## Fetch

Windows PowerShell:

```powershell
python -m app.main
python -m app.main --company affirm
python -m app.main --skip-aggregators
python -m app.main --skip-companies
python -m app.main --skip-discovery
```

macOS and Linux:

```bash
python3 -m app.main
python3 -m app.main --company affirm
python3 -m app.main --skip-aggregators
python3 -m app.main --skip-companies
python3 -m app.main --skip-discovery
```

| Flag | Effect |
| --- | --- |
| `--company SLUG` | One `ats_slug` slug. Aggregators are skipped. The slug must already be `available = 1` and use a supported board type. Any other slug exits with `No company with slug '…'`. |
| `--skip-aggregators` | Do not read `aggregators.yaml`. |
| `--skip-companies` | Do not read `ats_slug`. |
| `--skip-discovery` | Still fetch. Do not insert Greenhouse or Lever boards discovered from Adzuna redirects. |

`make run` asks four questions and then runs the same command: fetch
boards, fetch aggregators, discover companies, and an optional single
slug. Answering `n` sets the matching skip flag. On macOS and Linux, run
it in Terminal. On Windows, run it from Git Bash or WSL.

Each board is fetched on its own. One failure prints `[WARN]` and the run
continues.

- HTTP 404 or 410 marks that row `available = 0`. `last_seen` stays as it
  was. The next run skips it.
- HTTP 429 or 5xx leaves the row available.
- Workable list calls wait at least one second apart. A 429 is retried up
  to four times. A numeric `Retry-After` is honored up to 60 seconds.
  Anything else waits 10 seconds.

For each new job the command stores the full record, including the
description, and sets `passed_filters` to 1 or 0. Jobs that pass are also
appended to `data/candidates.csv`. That CSV has `company`, `title`,
`location`, `url`, and `posted_at`. Descriptions stay in SQLite. The file
is append-only, so a later run adds rows under the same header.

The console line for a source looks like:

```text
Affirm                                   fetched=  42  new_candidates=  3
```

`fetched` is how many postings the board returned. `new_candidates` is how
many of those were both unseen and passed the filters. A rerun of the same
board prints `new_candidates=0` because the URL and the
`company::title::location` key are already stored. Seen jobs are stored
even when they fail the filter, so they are not reconsidered on the next
fetch.

At the end, unless you passed `--skip-discovery`, new Greenhouse or Lever
boards found via Adzuna are inserted into `ats_slug` with `available = 1`.
An existing `(slug, ats_board)` pair is left as it is.

### What each board returns

The slug is the path token, not the company display name. Display name
lives in the `name` column and is what you see in the board and the digest.

| `ats_board` | Slug | List call |
| --- | --- | --- |
| `greenhouse` | Lowercase board token | `GET https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true`. Description is HTML. |
| `ashby` | Board token, original spelling | `GET https://api.ashbyhq.com/posting-api/job-board/{slug}`. |
| `workable` | Lowercase account token | `GET https://apply.workable.com/api/v1/widget/accounts/{slug}?details=true`. Description may be empty. |
| `lever` | Lowercase site token | `GET https://api.lever.co/v0/postings/{slug}?mode=json`. A 404 is tried once on `api.eu.lever.co`. The body is a JSON list. |
| `smartrecruiters` | Company identifier | `GET https://api.smartrecruiters.com/v1/companies/{slug}/postings`, 100 per page. A second GET per posting loads the description. A detail failure keeps the job with an empty description. |
| `workday` | `{tenant}.{wdN}/{site}` | POST 20 jobs at a time. See below. |

Workday tenant and `wdN` are lowercase. Site spelling is kept. The list
URL is `https://{tenant}.wd{N}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs`
with body `{"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": ""}`.
Paging stops at `total` or at offset 2000. A 404 is tried once on
`https://{wdN}.myworkdaysite.com`. The description and start date are
loaded only after the list title and list location already pass
`filters.yaml`. A detail failure keeps the job with an empty description
and the list's `postedOn`. The stored job URL is always
`https://{tenant}.wd{N}.myworkdayjobs.com/{site}{externalPath}`.

SmartRecruiters is a fetcher. The Common Crawl discovery script does not
search for it. Add those boards yourself.

A board type outside this table is ignored by the fetch, even when
`available = 1`.

### Aggregators

Adzuna and Remotive are searched after the company boards. Adzuna needs
`ADZUNA_APP_ID` and `ADZUNA_APP_KEY`. The request URL and the `params`
keys are documented in [Configuration](configuration.md).

Remotive returns HTML descriptions and a candidate location string. Adzuna
returns a short snippet, then sometimes replaces it with a longer page.
`source` on the stored row is the board type or `adzuna` or `remotive`.

## Re-apply filters

Fetching will not revisit a job it has seen. After you edit `filters.yaml`,
re-check the stored rows:

Windows PowerShell:

```powershell
python -m app.refilter --dry-run
python -m app.refilter
```

macOS and Linux:

```bash
python3 -m app.refilter --dry-run
python3 -m app.refilter
```

`--dry-run` prints the same lines and writes nothing. A real run only
flips `job_details.passed_filters`.

- `RESCUED` — was filtered out, now passes. The web board shows it on
  refresh. The next score run can pick it up if it has no evaluation yet.
- `DEMOTED` — used to pass, and the tighter rules drop it. It leaves the
  web board. The evaluation row, if any, stays in the database.

Nothing is deleted and nothing is downloaded.

## Inspect one job

Windows PowerShell:

```powershell
python -m app.inspect_job "https://example.com/jobs/123"
python -m app.inspect_job --rejected
python -m app.inspect_job --rejected 50
```

macOS and Linux:

```bash
python3 -m app.inspect_job "https://example.com/jobs/123"
python3 -m app.inspect_job --rejected
python3 -m app.inspect_job --rejected 50
```

The URL form prints the stored columns and the description. When
`passed_filters` is 0 it also prints `filtered out by:` with any of
`title`, `location`, `stack`, and `age` that fail against the filters
loaded right now. `?` means none of those four checks fail, which can
happen if the rules changed after the job was stored.

`--rejected` lists the most recently fetched failures, 20 by default.
The columns are the current reason, company, title, and location.

The reason is computed live. It can differ from the flag stored at fetch
time when `filters.yaml` has changed since then. Run `python -m app.refilter`
when you want the stored flag to match the file.
