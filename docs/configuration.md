# Configuration

Four files control a normal run. All of them are gitignored once
`python setup.py` copies them from the examples. Edit the copies. A
missing key or a bad type stops the command that loads that file.

Save YAML as UTF-8. `aggregators.yaml` is opened as UTF-8.
`filters.yaml` and `profile.yaml` are opened with the platform default
encoding. On macOS and Linux that default is UTF-8. On Windows it is
often cp1252, so a character outside that encoding can stop the load.
Quote YAML values that are boolean words (`On`, `Off`, `Yes`, `No`,
`True`, `False`), or the parser will not give you a string.

Restart the command after an edit. Filters are read when `app.filters`
is imported. The fetch command loads them at startup, so a second
`python -m app.main` in the same process is not how you reload. A new
terminal command is enough.

## `.env`

Loaded from the repo root by the fetch command and by scoring.
`.env.example` lists every variable.

| Variable | Required when | Default |
| --- | --- | --- |
| `ANTHROPIC_API_KEY` | `python -m app.ai_evaluate` actually calls the model, and the paid fit-check commands `noise` and `rescore` | none |
| `ANTHROPIC_MODEL` | You want a model other than the default | `claude-haiku-4-5` |
| `ADZUNA_APP_ID`, `ADZUNA_APP_KEY` | An Adzuna entry in `aggregators.yaml` is fetched | none |

A dry run of scoring does not need the Anthropic key. It does need
`profile.yaml` to exist and parse. Remotive needs no variable.

## `filters.yaml`

Read by `app/filters.py`. The shipped example is a software-engineering
search aimed at Canada, with Alberta cities included. The checker applies
whatever lists you put here. Empty `priority_title_keywords`,
`title_allow_keywords`, or `exclusion_keywords` is an error, because an
empty alternation would match every title.

A job passes only when every check below passes, in this order.

### 1. Title

Matching is case-insensitive. Keywords are literal text, not regular
expressions.

1. If the title contains any `priority_title_keywords` entry, it is kept
   and the exclusion list is skipped. The example uses this so
   "Software Engineer, Automated Marketing" survives the word "marketing".
2. Otherwise the title must contain some `title_allow_keywords` entry.
3. It is then dropped when it also contains an `exclusion_keywords` entry.

### 2. Location

`location_allow_patterns` is a list of regular expressions, matched
case-insensitively against the location string from the board. The job
is kept when any pattern matches. An empty location matches nothing, so
it is dropped.

The example patterns are `\bcanada\b`, `\balberta\b`, `,\s*ab\b`,
`\bedmonton\b`, `\bcalgary\b`, `\bontario\b`, and `\bvancouver\b`. There
is no pattern for a bare "Remote", so "Remote Poland" is dropped unless
another pattern hits. Replace the list with your own cities, regions, and
country names before the first real fetch.

In a double-quoted YAML string write a word boundary as `\\b`. In a
single-quoted string `\b` is already one backslash.

### 3. Posting age

`max_posting_age_days` drops a posting only when its age is known and the
youngest possible age is greater than this number. A missing, blank, or
unreadable `posted_at` is kept. `null` turns the check off. The example
uses 90. The value must be a non-negative integer or `null`.

Workday list rows often say `Posted Today`, `Posted Yesterday`,
`Posted 12 Days Ago`, or `Posted 30+ Days Ago`. The `30+` form means "at
least 31 days old". It is dropped when 31 is greater than
`max_posting_age_days`. A limit of 30 drops it. A limit of 31 keeps it,
because the board did not say it was older than 31.

### 4. Stack

`stack_dealbreakers` and `stack_core` are regular expressions, matched
case-insensitively against the description after tags are stripped. The
job is dropped when any dealbreaker matches and no core pattern matches.
An empty description is kept. The stack check never runs on title or
location.

The example dealbreakers assume you want Python and JavaScript and want
to drop Java, C#, .NET, Go, Ruby, PHP, Kotlin, Swift, Scala, and C++ when
those appear without your core stack. If you work in one of those, move
its pattern into `stack_core`.

`truncated_description_min_chars` (example: 400) is not a pass/fail rule.
Aggregator fetch uses it to decide whether a snippet is long enough to
skip a second request. Scoring uses it to tell the model the text may be
partial. A short description can still pass the filter.

After you change this file, update jobs already in the database:

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

See [Fetch, filter, and inspect](fetch-and-filter.md).

## `aggregators.yaml`

Top-level key `aggregators:`, a list. Each item has `name`, `type`, and
`params`. `type` is `adzuna` or `remotive`. A nested list under one
aggregator item breaks the load.

`name` is the label printed during the fetch. `params` is forwarded to
that source.

### Adzuna

The client always requests:

```text
https://api.adzuna.com/v1/api/jobs/us/search/{page}
```

The country segment in that path is `us`. `where` is sent as a query
parameter on that request. Other documented Adzuna parameters are
forwarded too, including `what`, `what_or`, `what_exclude`, `distance`,
`category`, `full_time`, `sort_by`, and `results_per_page`.

`max_pages` is not sent to Adzuna. It caps how many pages this pipeline
asks for (default 5). A page shorter than `results_per_page` (default 50)
stops the loop.

The example file has three Canada-oriented `where` values and one Remotive
category. Change `what` and `where`, and keep them consistent with
`filters.yaml`, or the filter will drop the hits afterward.

A full description is requested only when the title and location already
pass your filters and the Adzuna snippet looks short. When that follow-up
request lands on a Greenhouse or Lever posting, the company is remembered
for discovery. `--skip-discovery` on the fetch command throws that list
away at the end of the run.

### Remotive

`fetch_remotive` sends `params` to `https://remotive.com/api/remote-jobs`.
The example uses `category: software-dev`. Remotive lists remote roles.
Its terms ask for at most 4 requests a day and 2 a minute, and listings
are delayed 24 hours. One Remotive entry per fetch is the intended use.

## `profile.yaml`

Read when a scoring command starts. The model sees the YAML you wrote.
Organize it by what you can do. The template sections are:

- `identity` — name, headline, years, location, location constraints, education
- `core_stack` — languages, frameworks, and tools
- `competencies` — each with a `summary` and an `evidence` list of concrete outcomes
- `experience_timeline` — most recent first, with company, dates, title, domain, and stack
- `constraints` — employer, level, and location limits you want the model to weigh

`profile.example.yaml` is placeholders. `profile.sample.yaml` is fictional
and filled in, so you can see how specific an evidence bullet is.

There is no command that scores every job again. A new profile applies to
jobs that do not yet have an `ai_evaluations` row. To score one job again,
delete that row. The fit-check `rescore` command does not do this. See
[Scoring](scoring.md).

## `gates.yaml`

Optional. Copy `gates.yaml.example` to `gates.yaml` when you want
pass/fail checks in front of the fit score. Until the file exists, gating
is off.

This is a second list, separate from `filters.yaml`. Filters decide what
is stored as a candidate. Gates decide what is worth a model call, and
what the fit report treats as a hard constraint.

```yaml
gates:
  - name: location
    location_allow:
      - "remote"
      - "Your City"
  - name: seniority
    title_deny:
      - "\\bintern\\b"
      - "\\bdirector\\b"
  - name: work_authorization
    description_deny:
      - "must be a u\\.?s\\.? citizen"
```

Each item needs `name`. Any other key must be one of:

| Field | Text it searches | Passes when |
| --- | --- | --- |
| `location_allow` | Location | Any pattern matches |
| `location_deny` | Location | No pattern matches |
| `title_allow` | Title | Any pattern matches |
| `title_deny` | Title | No pattern matches |
| `description_allow` | Description, converted to Markdown | Any pattern matches |
| `description_deny` | Description, converted to Markdown | No pattern matches |

Patterns are case-insensitive regular expressions. In double quotes, a
word boundary is `\\b`. Gates run from top to bottom and stop at the first
failure. The failure is stored under the gate's `name`.

Nothing reads this file unless you ask:

Windows PowerShell:

```powershell
python -m app.ai_evaluate --gates
python -m app.fit_validate gates
```

macOS and Linux:

```bash
python3 -m app.ai_evaluate --gates
python3 -m app.fit_validate gates
```

Editing the file changes its version hash. Run `python -m app.fit_validate gates`
again so the fit report is looking at the file you just saved. The fit
check guide explains when to add a gate.
