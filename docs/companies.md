# Company boards

The fetch reads `data/ats_discovery.sqlite3`, table `ats_slug`. It does
not read `companies.yaml`. `companies.yaml.example` shows the fields and
a Workday slug, and it includes a sample list of boards.

Columns:

| Column | Role |
| --- | --- |
| `slug` | Board token. Part of the primary key. |
| `ats_board` | `greenhouse`, `ashby`, `workable`, `lever`, `smartrecruiters`, or `workday`. Part of the primary key. |
| `available` | `1` means the next fetch will try it. `0` means skip. |
| `name` | Display name. When this is null, the fetch prints the slug. |
| `last_seen` | Unix time of the last successful vetting check. A dead board leaves this unchanged. |
| `discovery_time` | Unix time when the row was first inserted. |

`python setup.py` creates the table if the database is missing and adds
`name` if an older table lacks it. Existing rows are kept.

## Add one board

Find the token in the public careers URL, then insert it. Greenhouse,
Lever, and Workable slugs should be lowercase. Ashby keeps the spelling
from the board URL. Workday is `{tenant}.{wdN}/{site}` with tenant and
`wdN` lowercase and the site spelling kept.

Windows PowerShell:

```powershell
python -c "import sqlite3; c=sqlite3.connect(r'data/ats_discovery.sqlite3'); c.execute('INSERT OR IGNORE INTO ats_slug (slug, ats_board, available, name) VALUES (?, ?, 1, ?)', ('affirm', 'greenhouse', 'Affirm')); c.commit()"
```

macOS and Linux:

```bash
python3 -c "import sqlite3; c=sqlite3.connect('data/ats_discovery.sqlite3'); c.execute('INSERT OR IGNORE INTO ats_slug (slug, ats_board, available, name) VALUES (?, ?, 1, ?)', ('affirm', 'greenhouse', 'Affirm')); c.commit()"
```

`INSERT OR IGNORE` leaves an existing `(slug, ats_board)` row alone.

Workday example, for a site at
`https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite`:

Windows PowerShell:

```powershell
python -c "import sqlite3; c=sqlite3.connect(r'data/ats_discovery.sqlite3'); c.execute('INSERT OR IGNORE INTO ats_slug (slug, ats_board, available, name) VALUES (?, ?, 1, ?)', ('nvidia.wd5/NVIDIAExternalCareerSite', 'workday', 'NVIDIA')); c.commit()"
```

macOS and Linux:

```bash
python3 -c "import sqlite3; c=sqlite3.connect('data/ats_discovery.sqlite3'); c.execute('INSERT OR IGNORE INTO ats_slug (slug, ats_board, available, name) VALUES (?, ?, 1, ?)', ('nvidia.wd5/NVIDIAExternalCareerSite', 'workday', 'NVIDIA')); c.commit()"
```

A `myworkdaysite.com` URL of the form
`https://{wdN}.myworkdaysite.com/recruiting/{tenant}/{site}` is the same
board. Store the same `{tenant}.{wdN}/{site}` slug.

List what will be fetched:

Windows PowerShell:

```powershell
python -c "import sqlite3; c=sqlite3.connect(r'data/ats_discovery.sqlite3'); rows=c.execute('SELECT ats_board, slug, available, COALESCE(name, slug) FROM ats_slug ORDER BY ats_board, slug');
[print(f'{a:16} {av}  {n}  ({s})') for a,s,av,n in rows]"
```

macOS and Linux:

```bash
python3 -c "import sqlite3; c=sqlite3.connect('data/ats_discovery.sqlite3'); rows=c.execute('SELECT ats_board, slug, available, COALESCE(name, slug) FROM ats_slug ORDER BY ats_board, slug'); [print(f'{a:16} {av}  {n}  ({s})') for a,s,av,n in rows]"
```

Try one board before a full run.

Windows PowerShell:

```powershell
python -m app.main --company affirm
```

macOS and Linux:

```bash
python3 -m app.main --company affirm
```

`--company` matches `slug`, and only among rows that are available and
have a fetcher. A 404 or 410 sets `available` to 0. Put it back with an
update if the URL was wrong and you have corrected the slug:

Windows PowerShell:

```powershell
python -c "import sqlite3; c=sqlite3.connect(r'data/ats_discovery.sqlite3'); c.execute('UPDATE ats_slug SET available = 1 WHERE slug = ? AND ats_board = ?', ('affirm', 'greenhouse')); c.commit()"
```

macOS and Linux:

```bash
python3 -c "import sqlite3; c=sqlite3.connect('data/ats_discovery.sqlite3'); c.execute('UPDATE ats_slug SET available = 1 WHERE slug = ? AND ats_board = ?', ('affirm', 'greenhouse')); c.commit()"
```

Non-ASCII slugs and board names are rejected by discovery. Stick to the
characters the slug patterns allow.

## Discovery during a fetch

When an Adzuna result already passes the title and location filters, and
the snippet looks short, the fetcher follows `redirect_url`. If that page
is a Greenhouse or Lever job and the single-job API returns a description,
the company is queued. At the end of `python -m app.main` those pairs are
inserted with `available = 1` and both timestamps set to now.

`--skip-discovery` skips that insert. The jobs themselves are still
filtered and stored.

This path only records Greenhouse and Lever. A redirect that stays on
Adzuna records nothing.

## Common Crawl discovery

Windows PowerShell:

```powershell
python ats-expansion/ats_discovery.py
python ats-expansion/ats_discovery.py CC-MAIN-2026-39
```

macOS and Linux:

```bash
python3 ats-expansion/ats_discovery.py
python3 ats-expansion/ats_discovery.py CC-MAIN-2026-39
```

The optional argument is a Common Crawl id. The default in the script is
`CC-MAIN-2026-39`. The script reads that crawl's columnar index once,
collects Greenhouse, Ashby, Lever, Workable, and Workday boards, and
inserts new `(slug, ats_board)` pairs. Existing pairs are left as they
are, including rows you marked unavailable.

It needs the `duckdb` Python package and network access to
`data.commoncrawl.org`. `duckdb` is not in `requirements.txt`. Install it
in the same environment before this command.

Windows PowerShell:

```powershell
python -m pip install duckdb
```

macOS and Linux:

```bash
python3 -m pip install duckdb
```

Per-file caches live under `ats-expansion/`. They are deleted after a
successful insert. On an error the script stops, tells you to rerun, and
leaves finished files cached so the next run skips them. There is a pause
between index files.

SmartRecruiters is not part of this query.

Ashby and Workday keep the first spelling seen for a case-insensitive
key. Greenhouse, Lever, and Workable are stored lowercase. Workday slugs
use the `{tenant}.{wdN}/{site}` form.

## Vet the registry

Windows PowerShell:

```powershell
python ats-expansion/expand_companies.py
```

macOS and Linux:

```bash
python3 ats-expansion/expand_companies.py
```

This checks every `available = 1` row, each against its own board. It is
a network scan of the whole registry.

- Success sets `last_seen` to now and leaves `available = 1`.
- A definite miss sets `available = 0` and leaves `last_seen` unchanged.
- A network error or HTTP 429 or 5xx waits 10 seconds and retries, up to
  four tries.

Run it when you want dead boards turned off after a discovery insert.
Review the `unavailable` lines before you assume a company is gone. A
wrong slug fails the same way a closed board does.

## One-off scripts

These live in `app/scripts/`. A normal week does not need them.

### Guess a board from a company name

Windows PowerShell:

```powershell
python -m app.scripts.try_companies_across_ats
python -m app.scripts.try_companies_across_ats --limit 100
python -m app.scripts.try_companies_across_ats --company "Example Inc"
```

macOS and Linux:

```bash
python3 -m app.scripts.try_companies_across_ats
python3 -m app.scripts.try_companies_across_ats --limit 100
python3 -m app.scripts.try_companies_across_ats --company "Example Inc"
```

This looks at company names already stored in `seen_jobs.sqlite3` that are
not in `ats_slug`, guesses slugs, and tries Greenhouse, Ashby, Workable,
Lever, and SmartRecruiters. The default limit is 30 names. It does not
insert anything. A live response can be a test board, so read the sample
titles, then insert the rows you trust with the SQL above.

Workday is not guessed here. The slug has a tenant, a `wdN` host, and a
site name, which a company name does not determine.

### Where Adzuna redirects go

Windows PowerShell:

```powershell
python -m app.scripts.diagnoze_adzuna_redirecta
python -m app.scripts.diagnoze_adzuna_redirecta --sample 50
```

macOS and Linux:

```bash
python3 -m app.scripts.diagnoze_adzuna_redirecta
python3 -m app.scripts.diagnoze_adzuna_redirecta --sample 50
```

The module name is spelled `diagnoze_adzuna_redirecta`. It samples Adzuna
results and reports the final host of `redirect_url`. It needs the Adzuna
keys. It does not write the jobs database or `candidates.csv`. The default
sample size is 25.

### One Adzuna details page

Windows PowerShell:

```powershell
python -m app.scripts.check_adzuna_details_page "https://www.adzuna.ca/details/123"
```

macOS and Linux:

```bash
python3 -m app.scripts.check_adzuna_details_page "https://www.adzuna.ca/details/123"
```

Prints what a plain HTTP GET returns and what a headless Chromium load
returns. The browser path imports Playwright. Playwright is not in
`requirements.txt`. Without it, the browser half reports that it cannot
run. The script does not need Adzuna keys and does not write the database.

Windows PowerShell:

```powershell
python -m pip install playwright
python -m playwright install chromium
```

macOS and Linux:

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
```

### Clean stored plain-text descriptions

Windows PowerShell:

```powershell
python -m app.scripts.clean_scraped_descriptions --dry-run
python -m app.scripts.clean_scraped_descriptions
```

macOS and Linux:

```bash
python3 -m app.scripts.clean_scraped_descriptions --dry-run
python3 -m app.scripts.clean_scraped_descriptions
```

Copy the database before the real run.

Windows PowerShell:

```powershell
Copy-Item data\seen_jobs.sqlite3 data\seen_jobs.sqlite3.bak
```

macOS and Linux:

```bash
cp data/seen_jobs.sqlite3 data/seen_jobs.sqlite3.bak
```

The command rewrites `job_details.description` for rows that are plain
text with large runs of blank lines from an old page scrape. Rows that
contain real HTML tags are skipped.

### A fixed insert list

`app/scripts/add_new_companies.py` is a one-off list of specific boards
passed to the same insert helper discovery uses. Running the file inserts
those rows when they are not already present. It is not a general "add my
companies" command. Insert your own rows with the statement at the top of
this page.
