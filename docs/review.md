# Review

Three views read the same database, `data/seen_jobs.sqlite3`. They do not
show the same rows.

| View | Which jobs |
| --- | --- |
| Web board | `passed_filters = 1`. Unscored, applied, and skipped rows are included. Sorted by score descending, with missing scores last. |
| Desktop cards | Passed filters, score present and at least 45, and your status is not applied or skipped. |
| Digest | Same inclusion rule as the desktop cards. |

Your status values are `applied`, `interview`, `rejected`, `skipped`, and
`silence`. Applied means you applied. Skipped means it is not a fit.
Marks stay in `user_status` when a job is scored again.

AI recommendation values are `apply`, `consider`, and `skip`. The board
shows "Not evaluated" when there is no score.

## Web board

One-time setup from the repo root. `npm install` is the same on every
system:

```bash
cd web
npm install
cd ..
```

Start it with the database path set.

Windows PowerShell:

```powershell
$env:DB_PATH = (Resolve-Path .\data\seen_jobs.sqlite3)
npm --prefix web run dev
```

macOS and Linux:

```bash
make web
```

`make web` sets `DB_PATH` for you. Without `make`:

```bash
DB_PATH="$(pwd)/data/seen_jobs.sqlite3" npm --prefix web run dev
```

Open http://localhost:3000. The default path, when `DB_PATH` is unset, is
`../data/seen_jobs.sqlite3` relative to the process working directory. Run
the npm script with the working directory set to `web/`, or set `DB_PATH`
as above. `npm --prefix web` keeps the working directory at the repo root,
so set `DB_PATH` in that case.

If the database file is missing, the app creates empty `job_details`,
`ai_evaluations`, and `user_status` tables and shows an empty board. Fetch
first when you want jobs.

A production build from `web/`. The default database path is the parent
`data/` folder when you start npm from `web/`.

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

### What you can do

The toolbar has:

- **AI status** — All, Apply, Consider, Skip, or Not evaluated.
- **My status** — All, No status, or one of the five statuses.
- **Search** — case-insensitive match on company and title together.
  Location is not searched.
- A count of visible rows over total rows.
- **Refresh** — reload from SQLite. The page does not poll. Run this after
  a fetch, a refilter, or a scoring run.

Click a column header to sort. Click the same header again to reverse the
direction. The score column starts high to low. A new text column starts
A to Z.

Click a row to open the detail panel. It shows title, company, location,
AI badge, score, your status, notes, strengths, gaps, risk factors, and
the description. Change the status or the notes, then press **Save**. The
panel shows Saving, then Saved, or Error. **Open job** opens the posting
in a new tab. Click the dark backdrop or the close control to dismiss the
panel. Closing without Save drops the unsaved draft.

The status dropdown in the table saves immediately and keeps the notes
already stored. It posts `{url, my_status, notes}` to `POST /api/status`.
An unknown status is rejected. An unknown URL is rejected.

`GET /api/jobs` is uncached. Job JSON is loaded when the page opens and
when you press Refresh.

Descriptions that contain real HTML are rendered as HTML. Entity-escaped
HTML is unescaped once and rendered when that reveals tags. Other text is
shown as plain text.

The board does not hide jobs under 45, and it does not hide applied or
skipped jobs. Filter those with the toolbar when you want the digest's
subset.

## Desktop cards

Windows PowerShell:

```powershell
python -m app.review_ui
```

macOS and Linux:

```bash
python3 -m app.review_ui
```

This opens a local window, one job at a time, amber text on a dark
background. It needs Tk. The official Windows Python installer and the
python.org macOS installer include it. Homebrew Python on macOS usually
needs `brew install python-tk`. Debian and Ubuntu need the `python3-tk`
package. Fedora and RHEL need `python3-tkinter`. The window lists the
same jobs as the digest:
passed filters, score at least 45, status not applied or skipped. Highest
score first.

The card shows the score, the AI recommendation, strengths, gaps, risks,
and the description as plain text. The company and the posting link are
on the card too. Click the link and release the mouse button to open it
in the default browser.

The bottom bar has:

- **APPLIED** and **SKIPPED** checkboxes. Turning one on turns the other
  off.
- A notes field.
- **CONFIRM**.

Confirm writes the checkbox and the notes, then shows SAVED.

- Applied removes that card.
- Skipped removes that card.
- Both boxes off leaves interview, rejected, and silence as they are.
- Both boxes off on a card that was applied or skipped clears that status.
  Those cards are not in the list to begin with, so this matters when you
  had checked a box and then cleared it before confirm.

Keys, when the notes field is not focused:

| Key | Action |
| --- | --- |
| Left / Right | Previous / next card |
| Home / End | First / last card |
| Enter | Confirm |

Enter still confirms while the notes field is focused. Arrow keys do not
change cards while you are typing notes.

Drafts for cards you have not confirmed are kept in memory while the
window is open. They are written when you press Confirm.

## Digest

Windows PowerShell:

```powershell
python -m app.digest
python -m app.digest --output data\digest.md
python -m app.digest --db data\seen_jobs.sqlite3
```

macOS and Linux:

```bash
python3 -m app.digest
python3 -m app.digest --output data/digest.md
python3 -m app.digest --db data/seen_jobs.sqlite3
```

`make digest` is the same command with the default paths.

The file is `data/digest.md`. It is rewritten from the database every
time. Edits to the description, the score, or the notes in the file are
not kept, except for the status marks described below.

Each included job is one section:

- Heading: `## {score} · {company} — {title}`
- Company, location, AI status, score
- `**My status:**` and `**Link:**` on their own lines
- Notes, transferable strengths, genuine gaps, risk factors
- The description as plain text, not Markdown

The header counts the jobs in the file and how many scored jobs were left
out because they are applied, skipped, or under 45.

### Mark a job from the file

1. Set that section's `**My status:**` line to `Applied` or `Skipped`.
2. Run `python -m app.digest` again.

The mark is saved on the job, and the new file omits it. These status
lines also count as skipped: `skip`, `pass`, `not a fit`, and
`not a good fit`. `Interview`, `Rejected`, `Silence`, and `To consider`
are left as stored. An unknown line prints a warning and is not saved.
Only the lines before the first `###` heading of that section are read,
so the same words inside the job description do not count.

### Mark a job from the command

Windows PowerShell:

```powershell
python -m app.digest --applied https://example.com/jobs/1 https://example.com/jobs/2
python -m app.digest --skipped https://example.com/jobs/3
python -m app.digest --restore https://example.com/jobs/1
```

macOS and Linux:

```bash
python3 -m app.digest --applied https://example.com/jobs/1 https://example.com/jobs/2
python3 -m app.digest --skipped https://example.com/jobs/3
python3 -m app.digest --restore https://example.com/jobs/1
```

Each flag takes one or more URLs. The digest is regenerated afterward.

`--restore` clears applied and skipped and keeps notes. A URL that is
interview, rejected, silence, or empty is left as it is and reported as
not excluded.

File marks are applied first. Command-line URLs are then checked. If any
command-line URL is not in the database, none of the command-line marks
are written, the missing URLs are printed, and the process exits with
status 1. Marks already read from the file stay saved.

The same applied and skipped values, set from the web board or the
desktop cards, drop the job the next time you generate the digest.
