# Documentation

Use these from the repository root.

| Shell | Python | Environment variable | Pipeline shortcut |
| --- | --- | --- | --- |
| Windows PowerShell | `python` | `$env:DB_PATH = (Resolve-Path .\data\seen_jobs.sqlite3)` | `python -m …` |
| macOS and Linux, bash or zsh | `python3` when `python` is not 3.10+ | `DB_PATH="$(pwd)/data/seen_jobs.sqlite3"` in front of the command | `make`, or `python3 -m …` |

A fenced `powershell` block and a fenced `bash` block are the same action
on the two families of systems. Where a page shows only PowerShell, swap
`python` for `python3`. The flags are unchanged. `make` runs in Terminal
on macOS and Linux. On Windows it needs Git Bash or WSL.

| Guide | Read it when |
| --- | --- |
| [Configuration](configuration.md) | You are editing `.env`, `filters.yaml`, `profile.yaml`, `aggregators.yaml`, or `gates.yaml`. |
| [Fetch, filter, and inspect](fetch-and-filter.md) | You are running a fetch, changing filters, or asking why a job was kept or dropped. |
| [Scoring](scoring.md) | You are about to spend an Anthropic call, or you want to score again. |
| [Review](review.md) | You are using the browser board, the desktop cards, or `data/digest.md`. |
| [Checking scores](checking-scores.md) | You want to compare the model's scores with your own yes/no labels. |
| [Companies](companies.md) | You are adding a board, discovering boards, or vetting the registry. |

The [README](../README.md) is the short map: first run, the three score
lines (45, 55, and the web board), and the two status vocabularies.
