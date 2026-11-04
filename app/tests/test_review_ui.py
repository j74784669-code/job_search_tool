"""Desktop listing viewer: load order, Applied checkbox, and the card window."""
import tkinter as tk

from unittest.mock import patch

from app import dedup
from app.review_ui import ReviewApp, card_body, confirm_status, load_listings, open_url


def _job(url, company, title, description="Build things.", location="Remote"):
    return {
        "url": url,
        "company": company,
        "title": title,
        "location": location,
        "description": description,
        "posted_at": None,
        "source": "test",
    }


def test_load_listings_is_passed_filter_highest_score_first(tmp_path):
    db = str(tmp_path / "jobs.sqlite3")
    low = _job("https://example.com/low", "LowCo", "Backend Engineer")
    high = _job("https://example.com/high", "HighCo", "Staff Engineer", description="<p>Ship it</p>")
    unscored = _job("https://example.com/new", "NewCo", "Software Engineer")
    rejected = _job("https://example.com/nope", "NoCo", "Software Engineer")
    with dedup.connect(db) as conn:
        for job, passed in ((low, True), (high, True), (unscored, True), (rejected, False)):
            dedup.save_details(conn, job, passed_filters=passed)
        dedup.save_evaluation(conn, low["url"], {
            "match_score": 60, "recommendation": "consider",
            "genuine_gaps": "", "transferable_strengths": "SQL", "risk_factors": "",
        }, model="test")
        dedup.save_evaluation(conn, high["url"], {
            "match_score": 90, "recommendation": "apply",
            "genuine_gaps": "Staff scope", "transferable_strengths": "", "risk_factors": "",
        }, model="test")
        dedup.save_user_status(conn, high["url"], "interview", "referred")
        applied = _job("https://example.com/applied", "SentCo", "Sent role")
        skipped = _job("https://example.com/skipped", "SkipCo", "Skipped role")
        dedup.save_details(conn, applied, passed_filters=True)
        dedup.save_details(conn, skipped, passed_filters=True)
        dedup.save_user_status(conn, applied["url"], "applied", "sent")
        dedup.save_user_status(conn, skipped["url"], "skipped", "not a fit")
        low_score = _job("https://example.com/44", "LowScore", "Below the line")
        on_line = _job("https://example.com/45", "OnLine", "On the line")
        dedup.save_details(conn, low_score, passed_filters=True)
        dedup.save_details(conn, on_line, passed_filters=True)
        dedup.save_evaluation(conn, low_score["url"], {
            "match_score": 44, "recommendation": "skip",
            "genuine_gaps": "", "transferable_strengths": "", "risk_factors": "",
        }, model="test")
        dedup.save_evaluation(conn, on_line["url"], {
            "match_score": 45, "recommendation": "consider",
            "genuine_gaps": "", "transferable_strengths": "", "risk_factors": "",
        }, model="test")
        rows = load_listings(conn)
    assert [row["url"] for row in rows] == [high["url"], low["url"], on_line["url"]]
    assert rows[0]["my_status"] == "interview"
    assert rows[0]["notes"] == "referred"
    assert unscored["url"] not in [row["url"] for row in rows]


def test_confirm_status_sets_applied_or_skipped():
    assert confirm_status(True, False, None) == "applied"
    assert confirm_status(True, False, "interview") == "applied"
    assert confirm_status(False, True, "interview") == "skipped"
    assert confirm_status(True, True, None) == "applied"
    assert confirm_status(False, False, "applied") is None
    assert confirm_status(False, False, "skipped") is None
    assert confirm_status(False, False, "interview") == "interview"
    assert confirm_status(False, False, None) is None


def test_card_body_flattens_html_and_skips_empty_sections():
    text = card_body({
        "description": "<p>We use <b>Java</b>.</p>",
        "transferable_strengths": "",
        "genuine_gaps": "No staff title",
        "risk_factors": None,
    })
    assert text.startswith("GAPS\nNo staff title")
    assert "STRENGTHS" not in text
    assert "RISKS" not in text
    assert "We use Java." in text


def test_open_url_strips_trailing_punctuation():
    with patch("app.review_ui.os.startfile") as start:
        open_url("https://example.com/a).")
        open_url("  ")
    start.assert_called_once_with("https://example.com/a")


def test_description_url_opens_on_click():
    job = _job(
        "https://example.com/posting",
        "Acme",
        "Engineer",
        description="Apply at https://example.com/apply).",
    )
    root = tk.Tk()
    root.withdraw()
    try:
        app = ReviewApp(root, [{
            **job,
            "match_score": 80,
            "recommendation": "apply",
            "genuine_gaps": "",
            "transferable_strengths": "",
            "risk_factors": "",
            "my_status": None,
            "notes": None,
        }], lambda *_args: None)
        root.geometry("980x740")
        root.deiconify()
        root.update()
        ranges = app.text.tag_ranges("url")
        assert len(ranges) == 2
        assert app.text.get(ranges[0], ranges[1]) == "https://example.com/apply"
        box = app.text.bbox(str(ranges[0]))
        assert box is not None
        with patch("app.review_ui.os.startfile") as start:
            app.text.event_generate("<ButtonRelease-1>", x=box[0] + 4, y=box[1] + 4)
            root.update()
        start.assert_called_once_with("https://example.com/apply")
    finally:
        root.destroy()


def test_window_navigates_and_confirm_writes_applied(tmp_path):
    db = str(tmp_path / "jobs.sqlite3")
    first = _job("https://example.com/a", "A", "First role")
    second = _job("https://example.com/b", "B", "Second role")
    with dedup.connect(db) as conn:
        dedup.save_details(conn, first, passed_filters=True)
        dedup.save_details(conn, second, passed_filters=True)
        dedup.save_evaluation(conn, first["url"], {
            "match_score": 80, "recommendation": "apply",
            "genuine_gaps": "", "transferable_strengths": "", "risk_factors": "",
        }, model="test")
        dedup.save_evaluation(conn, second["url"], {
            "match_score": 70, "recommendation": "consider",
            "genuine_gaps": "", "transferable_strengths": "", "risk_factors": "",
        }, model="test")
        dedup.save_user_status(conn, second["url"], "silence", "wait")
        jobs = load_listings(conn)

    saved = []

    def persist(url, status, notes):
        saved.append((url, status, notes))
        with dedup.connect(db) as conn:
            dedup.save_user_status(conn, url, status, notes)

    root = tk.Tk()
    root.withdraw()
    try:
        app = ReviewApp(root, jobs, persist)
        root.geometry("980x740")
        root.deiconify()
        root.update()
        assert app.bottom.winfo_height() > 30
        assert app.bottom.winfo_y() + app.bottom.winfo_height() <= root.winfo_height()
        assert app.box.winfo_width() > 10
        assert app.skip_box.winfo_width() > 10
        assert app.notes_entry.winfo_width() > 40
        assert app.confirm_btn.winfo_width() > 20
        assert app.title.cget("text") == "First role"
        assert app.box.cget("text") == "[ ]"
        with patch("app.review_ui.os.startfile") as start:
            app.link.event_generate("<ButtonRelease-1>", x=8, y=8)
            root.update()
        start.assert_called_once_with(first["url"])
        app.next()
        assert app.index == 1
        assert app.title.cget("text") == "Second role"
        assert "SILENCE" in app.meta.cget("text")
        app.notes_var.set("called them")
        app.toggle_applied()
        assert app.box.cget("text") == "[X]"
        app.previous()
        assert app.notes_var.get() == ""
        app.last()
        assert app.notes_var.get() == "called them"
        assert app.box.cget("text") == "[X]"
        app.confirm()
        assert saved == [("https://example.com/b", "applied", "called them")]
        assert "SAVED" == app.saved.cget("text")
        assert [job["url"] for job in app.jobs] == [first["url"]]
        assert app.title.cget("text") == "First role"
        with dedup.connect(db) as conn:
            row = dedup.get_user_status(conn, second["url"])
        assert row["my_status"] == "applied"
        assert row["notes"] == "called them"
        app.first()
        app.confirm()
        with dedup.connect(db) as conn:
            kept = dedup.get_user_status(conn, first["url"])
        assert kept["my_status"] is None
        app.toggle_skipped()
        assert app.skip_box.cget("text") == "[X]"
        assert app.box.cget("text") == "[ ]"
        app.confirm()
        assert app.jobs == []
        assert app.title.cget("text") == "NO LISTINGS"
        with dedup.connect(db) as conn:
            skipped = dedup.get_user_status(conn, first["url"])
        assert skipped["my_status"] == "skipped"
    finally:
        root.destroy()
