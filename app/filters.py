"""Deterministic pre-filters: title allowlist + exclusion keywords +
location allowlist + posting age + JD stack dealbreakers.

These run BEFORE any AI call — the whole point is to keep the AI-scored
volume small and cheap. The actual keyword/pattern lists live in
`filters.yaml` at the repo root (loaded below) so they can be edited
without touching code.

Design note (2026-08-11 rewrite): an EXCLUSION-only approach doesn't scale
to a company like Affirm that posts hundreds of non-engineering roles
(Analyst, Compliance, Marketing, Customer Success, Talent Brand, Sales
Development...) — you can't blacklist your way out of that. So title
filtering is allowlist-first: the title must look like an engineering
role AT ALL before we even consider it, then a smaller exclusion list
catches engineering-adjacent titles that aren't a fit (sales engineer,
hardware/mechanical engineer, etc).
"""
import re
from datetime import datetime, timezone

import yaml

FILTERS_CONFIG_PATH = "filters.yaml"


def _load_config(path: str = FILTERS_CONFIG_PATH) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


_config = _load_config()

PRIORITY_TITLE_KEYWORDS = _config["priority_title_keywords"]
TITLE_ALLOW_KEYWORDS = _config["title_allow_keywords"]
EXCLUSION_KEYWORDS = _config["exclusion_keywords"]
LOCATION_ALLOW_PATTERNS = _config["location_allow_patterns"]
STACK_DEALBREAKERS = _config["stack_dealbreakers"]
STACK_CORE = _config["stack_core"]
TRUNCATED_DESCRIPTION_MIN_CHARS = _config["truncated_description_min_chars"]
# Absent or null turns the check off, so an older filters.yaml keeps working.
_max_age = _config.get("max_posting_age_days")
if _max_age is None:
    MAX_POSTING_AGE_DAYS = None
elif isinstance(_max_age, bool) or not isinstance(_max_age, int) or _max_age < 0:
    raise ValueError(
        "filters.yaml's 'max_posting_age_days' must be a non-negative integer "
        f"or null, not {_max_age!r}"
    )
else:
    MAX_POSTING_AGE_DAYS = _max_age


def _compile_keyword_alternation(keywords: list[str], config_key: str) -> re.Pattern:
    # An empty keyword list joins to "" and compiles to "()", which matches
    # the empty string at every position — .search() would then match ANY
    # title, silently turning an allowlist into "allow everything" and an
    # exclusion list into "exclude everything". Fail loudly instead.
    if not keywords:
        raise ValueError(
            f"filters.yaml's '{config_key}' is empty — this would silently "
            "match every title instead of none. Add at least one keyword."
        )
    return re.compile("(" + "|".join(re.escape(k) for k in keywords) + ")", re.IGNORECASE)


_priority_re = _compile_keyword_alternation(PRIORITY_TITLE_KEYWORDS, "priority_title_keywords")
_title_allow_re = _compile_keyword_alternation(TITLE_ALLOW_KEYWORDS, "title_allow_keywords")
_exclusion_re = _compile_keyword_alternation(EXCLUSION_KEYWORDS, "exclusion_keywords")
_location_res = [re.compile(p, re.IGNORECASE) for p in LOCATION_ALLOW_PATTERNS]
_dealbreaker_res = [re.compile(p, re.IGNORECASE) for p in STACK_DEALBREAKERS]
_core_res = [re.compile(p, re.IGNORECASE) for p in STACK_CORE]

_html_tag_re = re.compile(r"<[^>]+>")
# Workday list rows say "Posted Today" / "Posted 12 Days Ago" / "Posted 30+ Days Ago".
# The "30+" form is a capped counter: the posting is older than 30 days.
_relative_posted_re = re.compile(
    r"^posted\s+(?:today|yesterday|(?P<days>\d+)(?P<capped>\+)?\s+days?\s+ago)$",
    re.IGNORECASE,
)
# 10^10 seconds is year 2286. Current epoch millis are ~10^12.
_EPOCH_MILLIS = 10_000_000_000


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _parse_timestamp(value) -> datetime | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        stamp = float(value)
    elif isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        if text.isdigit():
            stamp = float(text)
        else:
            iso = text[:-1] + "+00:00" if text.endswith("Z") else text
            try:
                return _as_utc(datetime.fromisoformat(iso))
            except ValueError:
                return None
    else:
        return None
    if stamp > _EPOCH_MILLIS:
        stamp /= 1000.0
    if stamp < 0 or stamp > _EPOCH_MILLIS:
        return None
    try:
        return datetime.fromtimestamp(stamp, timezone.utc)
    except (OverflowError, OSError, ValueError):
        return None


def posting_age_bounds(posted_at, now: datetime | None = None) -> tuple[int, int | None] | None:
    """Youngest and oldest possible age in whole days.

    The oldest bound is None when the source only gives a floor, which is
    Workday's "Posted 30+ Days Ago". Returns None when the value is missing
    or not a date (a location string that landed in this field, for example).
    """
    now = _as_utc(now or datetime.now(timezone.utc))
    if isinstance(posted_at, str):
        match = _relative_posted_re.fullmatch(posted_at.strip())
        if match:
            if match.group("days") is None:
                days = 1 if "yesterday" in posted_at.lower() else 0
                return (days, days)
            floor = int(match.group("days"))
            if match.group("capped"):
                return (floor + 1, None)
            return (floor, floor)
    parsed = _parse_timestamp(posted_at)
    if parsed is None:
        return None
    return ((now - parsed).days, (now - parsed).days)


def posting_too_old(posted_at, max_days: int | None, now: datetime | None = None) -> bool:
    """True only when the posting is known to be older than `max_days`.

    A missing or unreadable date is kept. An open-ended "30+" label is
    dropped only when that floor is already past the limit.
    """
    if max_days is None:
        return False
    bounds = posting_age_bounds(posted_at, now)
    if bounds is None:
        return False
    youngest, _oldest = bounds
    return youngest > max_days


def strip_html(html_or_text: str) -> str:
    """Cheap HTML-to-text: good enough for keyword matching, not for display."""
    if not html_or_text:
        return ""
    return _html_tag_re.sub(" ", html_or_text)


def looks_truncated(description: str) -> bool:
    """True if `description` looks like a short aggregator teaser rather
    than a full job posting — either it visibly cuts off mid-sentence, or
    it's just too short to contain real requirements/responsibilities.

    Shared by aggregator_clients.py (decide whether it's worth the extra
    request to fetch a full JD) and ai_evaluate.py (fall back to telling
    the model the description is partial, for the cases a full-JD fetch
    still couldn't recover — blocked site, dead link, genuinely short
    posting)."""
    text = strip_html(description or "").strip()
    if not text:
        return True
    if text.endswith("…") or text.endswith("...") or text.rstrip().endswith(".."):
        return True
    return len(text) < TRUNCATED_DESCRIPTION_MIN_CHARS


def title_is_relevant(title: str) -> bool:
    title = title or ""
    if _priority_re.search(title):
        # Unambiguous engineering title — e.g. "Software Engineer, Automated
        # Marketing" — skip the exclusion list entirely so a word like
        # "marketing" elsewhere in the title can't veto it.
        return True
    if not _title_allow_re.search(title):
        return False
    if _exclusion_re.search(title):
        return False
    return True


def location_is_allowed(location: str) -> bool:
    loc = location or ""
    return any(p.search(loc) for p in _location_res)


def jd_stack_mismatch(description: str) -> bool:
    """True if the JD looks like a dealbreaker-language role with no
    mention of your own core stack. Only meaningful when `description` is
    non-empty — callers should treat an empty description as "unknown,
    don't reject on stack alone"."""
    text = strip_html(description)
    if not text:
        return False
    has_dealbreaker = any(p.search(text) for p in _dealbreaker_res)
    has_core = any(p.search(text) for p in _core_res)
    return has_dealbreaker and not has_core


def passes_filters(job: dict) -> bool:
    """job must have 'title' and 'location' keys (plain strings); may
    optionally have 'description' and 'posted_at'."""
    if not title_is_relevant(job.get("title", "")):
        return False
    if not location_is_allowed(job.get("location", "")):
        return False
    if posting_too_old(job.get("posted_at"), MAX_POSTING_AGE_DAYS):
        return False
    if jd_stack_mismatch(job.get("description", "")):
        return False
    return True
