"""Desktop listing viewer. One card at a time, amber on black.

    python -m app.review_ui

Same jobs as the digest: passed filters, score at or above the digest
line, and not marked applied or skipped. Applied and Skipped are
separate checkboxes. Confirm writes the checked mark and the notes,
then drops that card. Clearing both clears only those two statuses.
Interview, rejected, and silence stay in the list.
"""
import os
import re
import sys
import tkinter as tk
import tkinter.font as tkfont
import webbrowser

from app import dedup
from app.digest import MIN_MATCH_SCORE, MY_STATUS_LABEL, description_to_text, listings_for_review

BG = "#100c02"
AMBER = "#ffb000"
AMBER_DIM = "#a86b00"
AMBER_FAINT = "#5c3d08"
BRIGHT = "#ffe08a"
PANEL = "#1a1404"

# Trailing punctuation is sentence markup, not part of the URL.
_URL_RE = re.compile(r"https?://[^\s<>\"']+")


def open_url(url: str) -> None:
    """Open a job link in the default browser.

    Call this after the mouse button is up. On Windows, ShellExecute
    (what webbrowser.open uses) is cancelled while the button is still
    down, so a press handler returns without a tab.
    """
    url = (url or "").strip().rstrip(".,);]")
    if not url:
        return
    if sys.platform == "win32":
        os.startfile(url)
        return
    webbrowser.open(url, new=2)


def _text_index(content: str, offset: int) -> str:
    line = content.count("\n", 0, offset) + 1
    last_break = content.rfind("\n", 0, offset)
    column = offset if last_break < 0 else offset - last_break - 1
    return f"{line}.{column}"


AI_LABEL = {
    "apply": "APPLY",
    "consider": "CONSIDER",
    "skip": "SKIP",
    "not_evaluated": "NOT EVALUATED",
}


def load_listings(conn) -> list[dict]:
    """Same jobs as the digest. The cutoff and status rule live in listings_for_review."""
    jobs, _excluded = listings_for_review(list(dedup.iter_board_jobs(conn)))
    return jobs


def confirm_status(applied: bool, skipped: bool, current: str | None) -> str | None:
    """Applied wins if both are set. Neither clears only those two marks."""
    if applied:
        return "applied"
    if skipped:
        return "skipped"
    if current in ("applied", "skipped"):
        return None
    return current or None


def card_body(job: dict) -> str:
    """Scrollable card text: score notes, then the description as plain text."""
    blocks = []
    strengths = (job.get("transferable_strengths") or "").strip()
    gaps = (job.get("genuine_gaps") or "").strip()
    risks = (job.get("risk_factors") or "").strip()
    if strengths:
        blocks.append("STRENGTHS\n" + strengths)
    if gaps:
        blocks.append("GAPS\n" + gaps)
    if risks:
        blocks.append("RISKS\n" + risks)
    text = description_to_text(job.get("description") or "")
    blocks.append(text or "NO DESCRIPTION.")
    return "\n\n".join(blocks)


def _mono(size: int, weight: str = "normal") -> tuple:
    return ("Consolas", size, weight)


class ReviewApp:
    def __init__(self, root: tk.Tk, jobs: list[dict], on_confirm) -> None:
        self.root = root
        self.jobs = jobs
        self.on_confirm = on_confirm
        self.index = 0
        self.drafts: dict[str, tuple[bool, bool, str]] = {}
        self.applied_on = False
        self.skipped_on = False
        self._loading = False
        self._flash_after = None

        root.title("Listings")
        root.configure(bg=BG)
        root.geometry("980x740")
        root.minsize(680, 520)

        top = tk.Frame(root, bg=BG)
        top.pack(side=tk.TOP, fill=tk.X, padx=18, pady=(14, 0))
        tk.Label(
            top, text="LISTINGS", font=_mono(14, "bold"), fg=AMBER_DIM, bg=BG,
        ).pack(side=tk.LEFT)
        nav = tk.Frame(top, bg=BG)
        nav.pack(side=tk.RIGHT)
        self.first_btn = self._nav(nav, "◀◀", self.first)
        self.prev_btn = self._nav(nav, "◀", self.previous)
        self.position = tk.Label(nav, text="", font=_mono(12), fg=AMBER, bg=BG, padx=10)
        self.position.pack(side=tk.LEFT)
        self.next_btn = self._nav(nav, "▶", self.next)
        self.last_btn = self._nav(nav, "▶▶", self.last)

        self.card = tk.Frame(root, bg=PANEL, highlightbackground=AMBER, highlightthickness=1)

        self.title = tk.Label(
            self.card, text="", font=_mono(18, "bold"), fg=BRIGHT, bg=PANEL,
            anchor="w", justify=tk.LEFT, wraplength=860,
        )
        self.title.pack(fill=tk.X, padx=16, pady=(14, 2))
        self.meta = tk.Label(
            self.card, text="", font=_mono(11), fg=AMBER, bg=PANEL,
            anchor="w", justify=tk.LEFT, wraplength=860,
        )
        self.meta.pack(fill=tk.X, padx=16)
        self.link = tk.Label(
            self.card, text="", font=("Consolas", 10, "underline"), fg=BRIGHT, bg=PANEL,
            anchor="w", justify=tk.LEFT, wraplength=860, cursor="hand2",
        )
        self.link.pack(fill=tk.X, padx=16, pady=(2, 8))
        self.link.bind("<ButtonRelease-1>", self._open_link)

        body = tk.Frame(self.card, bg=PANEL)
        body.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))
        self.text = tk.Text(
            body, wrap=tk.WORD, font=_mono(11), fg=AMBER, bg=PANEL,
            insertbackground=AMBER, relief=tk.FLAT, highlightthickness=0,
            padx=6, pady=4, cursor="arrow",
        )
        scroll = tk.Scrollbar(
            body, command=self.text.yview, troughcolor=BG, bg=AMBER_DIM,
            activebackground=AMBER, relief=tk.FLAT,
        )
        self.text.configure(yscrollcommand=scroll.set)
        self.text.tag_configure("url", foreground=BRIGHT, underline=True)
        self.text.bind("<ButtonRelease-1>", self._click_text)
        self.text.bind("<Motion>", self._hover_text)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.text.configure(state=tk.DISABLED)

        # Pack the bar before the expanding card. Packing the card first
        # lets it take the whole window, and the controls never appear.
        self.bottom = tk.Frame(root, bg=BG, highlightbackground=AMBER_DIM, highlightthickness=1)
        self.bottom.pack(side=tk.BOTTOM, fill=tk.X, padx=18, pady=(0, 14))

        self.saved = tk.Label(self.bottom, text="", font=_mono(11), fg=BRIGHT, bg=BG, width=6)
        self.saved.pack(side=tk.RIGHT, padx=(0, 10))
        self.confirm_btn = tk.Label(
            self.bottom, text=" CONFIRM ", font=_mono(12, "bold"), fg=BG, bg=AMBER, cursor="hand2",
        )
        self.confirm_btn.pack(side=tk.RIGHT, padx=(8, 4), pady=10)
        self.confirm_btn.bind("<Button-1>", lambda _e: self.confirm())

        box_row = tk.Frame(self.bottom, bg=BG)
        box_row.pack(side=tk.LEFT, padx=(10, 8), pady=10)
        self.box = self._check(box_row, " APPLIED", self.toggle_applied)
        self.skip_box = self._check(box_row, " SKIPPED", self.toggle_skipped)

        tk.Label(self.bottom, text="NOTES", font=_mono(11), fg=AMBER_DIM, bg=BG).pack(
            side=tk.LEFT, pady=10,
        )
        self.notes_var = tk.StringVar()
        self.notes_var.trace_add("write", self._on_notes)
        self.notes_entry = tk.Entry(
            self.bottom, textvariable=self.notes_var, font=_mono(12),
            fg=AMBER, bg=PANEL, insertbackground=BRIGHT, relief=tk.FLAT,
            highlightthickness=1, highlightbackground=AMBER_DIM, highlightcolor=AMBER,
        )
        self.notes_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10, pady=10, ipady=4)

        self.card.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=18, pady=12)

        root.bind("<Left>", self._key_prev)
        root.bind("<Right>", self._key_next)
        root.bind("<Home>", self._key_first)
        root.bind("<End>", self._key_last)
        root.bind("<Return>", self._key_confirm)
        self.card.bind("<Configure>", self._rewrap)
        self.show()

    def _check(self, parent, caption: str, command) -> tk.Label:
        box = tk.Label(
            parent, text="[ ]", font=_mono(14, "bold"), fg=AMBER, bg=BG, cursor="hand2",
        )
        box.pack(side=tk.LEFT)
        label = tk.Label(
            parent, text=caption, font=_mono(12), fg=AMBER, bg=BG, cursor="hand2",
        )
        label.pack(side=tk.LEFT, padx=(0, 14))
        box.bind("<Button-1>", lambda _e: command())
        label.bind("<Button-1>", lambda _e: command())
        return box

    def _nav(self, parent, text: str, command) -> tk.Label:
        glyph = "Segoe UI Symbol" if "Segoe UI Symbol" in tkfont.families() else "Consolas"
        label = tk.Label(
            parent, text=text, font=(glyph, 16), fg=AMBER, bg=BG,
            padx=6, cursor="hand2",
        )
        label.pack(side=tk.LEFT)
        label.bind("<Button-1>", lambda _e: command())
        return label

    def _rewrap(self, event) -> None:
        if event.widget is not self.card:
            return
        width = max(event.width - 36, 200)
        self.title.configure(wraplength=width)
        self.meta.configure(wraplength=width)
        self.link.configure(wraplength=width)

    def _typing(self, event) -> bool:
        return isinstance(event.widget, (tk.Entry, tk.Text))

    def _key_prev(self, event) -> None:
        if self._typing(event):
            return
        self.previous()

    def _key_next(self, event) -> None:
        if self._typing(event):
            return
        self.next()

    def _key_first(self, event) -> None:
        if self._typing(event):
            return
        self.first()

    def _key_last(self, event) -> None:
        if self._typing(event):
            return
        self.last()

    def _key_confirm(self, event) -> None:
        if isinstance(event.widget, tk.Text):
            return
        self.confirm()

    def _remember(self) -> None:
        if self._loading or not self.jobs:
            return
        job = self.jobs[self.index]
        self.drafts[job["url"]] = (self.applied_on, self.skipped_on, self.notes_var.get())

    def _on_notes(self, *_args) -> None:
        self._remember()

    def toggle_applied(self) -> None:
        if not self.jobs:
            return
        self.applied_on = not self.applied_on
        if self.applied_on:
            self.skipped_on = False
        self._draw_box()
        self._remember()

    def toggle_skipped(self) -> None:
        if not self.jobs:
            return
        self.skipped_on = not self.skipped_on
        if self.skipped_on:
            self.applied_on = False
        self._draw_box()
        self._remember()

    def _draw_box(self) -> None:
        self.box.configure(text="[X]" if self.applied_on else "[ ]")
        self.skip_box.configure(text="[X]" if self.skipped_on else "[ ]")

    def _dim(self, label: tk.Label, enabled: bool) -> None:
        label.configure(fg=AMBER if enabled else AMBER_FAINT, cursor="hand2" if enabled else "arrow")

    def show(self) -> None:
        self._loading = True
        try:
            count = len(self.jobs)
            if count == 0:
                self.position.configure(text="0 / 0")
                self.title.configure(text="NO LISTINGS")
                self.meta.configure(
                    text=f"Nothing scored {MIN_MATCH_SCORE} or above is left. Applied and skipped jobs are hidden."
                )
                self.link.configure(text="")
                self._set_text("")
                self.applied_on = False
                self.skipped_on = False
                self._draw_box()
                self.notes_var.set("")
            else:
                self.index = max(0, min(self.index, count - 1))
                job = self.jobs[self.index]
                self.position.configure(text=f"{self.index + 1} / {count}")
                self.title.configure(text=job.get("title") or "Untitled")
                self.meta.configure(text=self._meta(job))
                self.link.configure(text=job.get("url") or "")
                self._set_text(card_body(job))
                draft = self.drafts.get(job["url"])
                if draft is None:
                    self.applied_on = job.get("my_status") == "applied"
                    self.skipped_on = job.get("my_status") == "skipped"
                    notes = job.get("notes") or ""
                else:
                    self.applied_on, self.skipped_on, notes = draft
                self._draw_box()
                self.notes_var.set(notes)
            at_start = self.index <= 0 or count == 0
            at_end = count == 0 or self.index >= count - 1
            self._dim(self.first_btn, not at_start)
            self._dim(self.prev_btn, not at_start)
            self._dim(self.next_btn, not at_end)
            self._dim(self.last_btn, not at_end)
        finally:
            self._loading = False

    def _meta(self, job: dict) -> str:
        place = "  ·  ".join(
            part for part in (
                (job.get("company") or "").strip(),
                (job.get("location") or "").strip(),
                (job.get("posted_at") or "").strip(),
            ) if part
        )
        score = job.get("match_score")
        score_text = "—" if score is None else str(score)
        ai = AI_LABEL.get(job.get("recommendation") or "", "NOT EVALUATED")
        status = job.get("my_status") or ""
        status_text = MY_STATUS_LABEL.get(status, status).upper() if status else "NOT SET"
        line = f"SCORE {score_text}    AI {ai}    STATUS {status_text}"
        return f"{place}\n{line}" if place else line

    def _set_text(self, value: str) -> None:
        self.text.configure(state=tk.NORMAL)
        self.text.delete("1.0", tk.END)
        self.text.insert("1.0", value)
        self.text.tag_remove("url", "1.0", tk.END)
        for match in _URL_RE.finditer(value):
            url = match.group(0).rstrip(".,);]")
            if not url:
                continue
            start = _text_index(value, match.start())
            end = _text_index(value, match.start() + len(url))
            self.text.tag_add("url", start, end)
        self.text.configure(state=tk.DISABLED)
        self.text.yview_moveto(0)

    def _open_link(self, _event) -> None:
        if not self.jobs:
            return
        self._open_later(self.jobs[self.index].get("url") or "")

    def _click_text(self, event) -> None:
        self._open_later(self._url_at(f"@{event.x},{event.y}") or "")

    def _open_later(self, url: str) -> None:
        if url:
            self.root.after(0, lambda: open_url(url))

    def _hover_text(self, event) -> None:
        over = self._url_at(f"@{event.x},{event.y}")
        self.text.configure(cursor="hand2" if over else "arrow")

    def _url_at(self, index: str) -> str | None:
        try:
            point = self.text.index(index)
        except tk.TclError:
            return None
        if "url" not in self.text.tag_names(point):
            return None
        ranges = self.text.tag_ranges("url")
        for start, end in zip(ranges[0::2], ranges[1::2]):
            if self.text.compare(start, "<=", point) and self.text.compare(point, "<", end):
                return self.text.get(start, end)
        return None

    def first(self) -> None:
        self.go(0)

    def last(self) -> None:
        self.go(max(len(self.jobs) - 1, 0))

    def previous(self) -> None:
        self.go(self.index - 1)

    def next(self) -> None:
        self.go(self.index + 1)

    def go(self, index: int) -> None:
        if not self.jobs:
            return
        index = max(0, min(index, len(self.jobs) - 1))
        if index == self.index:
            return
        self.index = index
        self.saved.configure(text="")
        self.show()

    def confirm(self) -> None:
        if not self.jobs:
            return
        job = self.jobs[self.index]
        notes = self.notes_var.get().strip() or None
        status = confirm_status(self.applied_on, self.skipped_on, job.get("my_status"))
        self.on_confirm(job["url"], status, notes)
        job["my_status"] = status
        job["notes"] = notes
        self.drafts.pop(job["url"], None)
        if status in ("applied", "skipped"):
            self.jobs.pop(self.index)
            if self.index >= len(self.jobs):
                self.index = max(len(self.jobs) - 1, 0)
        self.saved.configure(text="SAVED")
        if self._flash_after is not None:
            self.root.after_cancel(self._flash_after)
        self._flash_after = self.root.after(1200, lambda: self.saved.configure(text=""))
        self.show()

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    with dedup.connect() as conn:
        jobs = load_listings(conn)

    def persist(url: str, status: str | None, notes: str | None) -> None:
        with dedup.connect() as conn:
            dedup.save_user_status(conn, url, status, notes)

    root = tk.Tk()
    ReviewApp(root, jobs, persist).run()


if __name__ == "__main__":
    main()
