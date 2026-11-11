"""Accessibility reviewer (advise). Static HTML checks only - a PoC stand-in for axe/pa11y in CI."""

from __future__ import annotations

from html.parser import HTMLParser

from .base import Context, Hit

HTML_GLOBS = ["*.html", "*.htm"]
UNNAMED_OK_INPUT_TYPES = {"hidden", "submit", "reset", "button", "image"}
VAGUE_LINK_TEXT = {"click here", "here", "read more", "more", "link", "this link", "learn more"}


class _Parser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.hits: list[tuple[str, int, str]] = []  # (rule, line, evidence)
        self.html_line: int | None = None
        self.html_lang = ""
        self.has_title = False
        self._in_title = False
        self._title_text = ""
        self._label_depth = 0
        self._label_for: set[str] = set()
        self._controls: list[tuple[int, dict[str, str | None], bool]] = []
        self._link: dict | None = None
        self._button: dict | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = {k.lower(): v for k, v in attrs}
        line = self.getpos()[0]
        if tag == "html":
            self.html_line = line
            self.html_lang = (a.get("lang") or "").strip()
        elif tag == "title":
            self._in_title = True
        elif tag == "img":
            if "alt" not in a:
                self.hits.append(("A11Y-001", line, "<img> without an alt attribute"))
            alt = (a.get("alt") or "").strip()
            for holder in (self._link, self._button):
                if holder is not None and alt:
                    holder["text"] += alt
        elif tag == "label":
            self._label_depth += 1
            if a.get("for"):
                self._label_for.add(a["for"] or "")
        elif tag in ("input", "select", "textarea"):
            if not (tag == "input" and (a.get("type") or "text").lower() in UNNAMED_OK_INPUT_TYPES):
                self._controls.append((line, a, self._label_depth > 0))
        elif tag == "a":
            self._link = {"line": line, "attrs": a, "text": ""}
        elif tag == "button":
            self._button = {"line": line, "attrs": a, "text": ""}

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
            self.has_title = bool(self._title_text.strip())
        elif tag == "label" and self._label_depth:
            self._label_depth -= 1
        elif tag == "a" and self._link is not None:
            link, self._link = self._link, None
            has_name = bool((link["attrs"].get("aria-label") or "").strip())
            text = " ".join(link["text"].split()).lower()
            if not has_name and text in VAGUE_LINK_TEXT:
                self.hits.append(("A11Y-004", link["line"], f'link text "{text}" does not describe the destination'))
        elif tag == "button" and self._button is not None:
            btn, self._button = self._button, None
            attrs = btn["attrs"]
            named = any((attrs.get(k) or "").strip() for k in ("aria-label", "aria-labelledby", "title"))
            if not named and not btn["text"].strip():
                self.hits.append(("A11Y-006", btn["line"], "<button> with no text or accessible name"))

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self._title_text += data
        for holder in (self._link, self._button):
            if holder is not None:
                holder["text"] += data

    def finish(self) -> list[tuple[str, int, str]]:
        for line, a, in_label in self._controls:
            named = any((a.get(k) or "").strip() for k in ("aria-label", "aria-labelledby", "title"))
            if not (named or in_label or (a.get("id") and a["id"] in self._label_for)):
                self.hits.append(("A11Y-003", line, "form control with no label or accessible name"))
        if self.html_line is not None:  # full documents only; fragments have no lang or title
            if not self.html_lang:
                self.hits.append(("A11Y-002", self.html_line, "<html> without a lang attribute"))
            if not self.has_title:
                self.hits.append(("A11Y-005", self.html_line, "document has no non-empty <title>"))
        return self.hits


async def run_checks(ctx: Context) -> list[Hit]:
    hits: list[Hit] = []
    for f in ctx.live_files(HTML_GLOBS):
        text = ctx.read(f)
        if text is None:
            continue
        parser = _Parser()
        parser.feed(text)
        parser.close()
        for rule, line, evidence in parser.finish():
            hits.append(Hit(rule, f.path, line, evidence=evidence))
    return hits
