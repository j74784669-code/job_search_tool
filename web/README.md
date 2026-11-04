# Job search board

A local Next.js app on the pipeline database `data/seen_jobs.sqlite3`.
It reads and writes that file. There is no export step.

The board lists every job with `passed_filters = 1`, including unscored
jobs and jobs you have marked applied or skipped. The Markdown digest and
the desktop cards use a narrower rule (score at least 45, and not applied
or skipped). That rule is documented in the root
[README](../README.md) and in [docs/review.md](../docs/review.md).

## Setup

Install dependencies once, from the repository root. This is the same on
Windows, macOS, and Linux:

```bash
cd web
npm install
cd ..
```

Windows PowerShell, from the repository root:

```powershell
$env:DB_PATH = (Resolve-Path .\data\seen_jobs.sqlite3)
npm --prefix web run dev
```

macOS and Linux, from the repository root:

```bash
make web
```

`make web` sets `DB_PATH` to `data/seen_jobs.sqlite3` and starts the dev
server. Without `make`:

```bash
DB_PATH="$(pwd)/data/seen_jobs.sqlite3" npm --prefix web run dev
```

`npm --prefix web` leaves the working directory at the repo root, so set
`DB_PATH` in that case. The app's own default is
`../data/seen_jobs.sqlite3` relative to the process working directory,
which is correct when you start npm from `web/`.

Windows PowerShell:

```powershell
cd web
$env:DB_PATH = (Resolve-Path ..\data\seen_jobs.sqlite3)
npm run dev
```

macOS and Linux:

```bash
cd web
DB_PATH="$(pwd)/../data/seen_jobs.sqlite3" npm run dev
```

Open http://localhost:3000. Fetch and score with the Python pipeline
first if you want rows to look at. A missing database still starts: the
app creates empty tables and the board has no jobs.

## Using the board

The toolbar filters by AI status and by your status, and it searches
company and title. The badge shows visible rows over total rows. Refresh
reloads SQLite. The page does not poll, so run Refresh after a fetch or a
scoring run.

Click a column header to sort. Click a row to open the posting, the model
notes (strengths, gaps, risks), and the description. Edit **My status**
and **Notes**, then press Save. The status menu on the row itself saves
immediately and keeps the current notes.

Your status is `applied`, `interview`, `rejected`, `skipped`, or
`silence`. The model recommendation is `apply`, `consider`, or `skip`,
shown as Apply, Consider, Skip, or Not evaluated. They are stored in
different tables.

Applied and skipped jobs stay on this board. They drop out of
`data/digest.md` the next time you run `python -m app.digest`.

`GET /api/jobs` and `POST /api/status` talk to SQLite on each call.
`POST /api/status` expects JSON `{ "url", "my_status", "notes" }`.

## Production build

From `web/`. Set `DB_PATH` when the database is not at the default
relative path.

Windows PowerShell:

```powershell
cd web
$env:DB_PATH = (Resolve-Path ..\data\seen_jobs.sqlite3)
npm run build
npm run start
```

macOS and Linux:

```bash
cd web
DB_PATH="$(pwd)/../data/seen_jobs.sqlite3" npm run build
DB_PATH="$(pwd)/../data/seen_jobs.sqlite3" npm run start
```
