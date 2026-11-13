"""Find the deadline an email states ("Last date: 31st October 2026", "apply by 31.10.2026", ...)."""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import List, Optional, Tuple

_MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}
_MON = (r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?"
        r"|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)")
_ORD = r"\s?(?:st|nd|rd|th)?"
# 31st October 2026 / 31 Oct, 2026 / 31st of October / 30-Sep-2026
_DAY_FIRST = re.compile(r"(?<![\d.])(\d{1,2})" + _ORD + r"[\s\-./]*(?:of\s+)?" + _MON + r"\b\.?(?:[\s\-./,]*(\d{4}))?",
                        re.I)
# October 31, 2026 / Oct 31st  (the day must not be the start of a year: "September 2026" is not a date)
_MONTH_FIRST = re.compile(_MON + r"\b\.?\s+(\d{1,2})(?!\d)" + _ORD + r"(?:,?\s*(\d{4}))?", re.I)
# 31.10.2026 / 31/10/26 / 31-10-2026
_NUMERIC = re.compile(r"(?<![\d.])(\d{1,2})[./-](\d{1,2})[./-](\d{4}|\d{2})(?![\d])")

_STRONG = re.compile(
    r"last\s+date|deadline|due\s+(?:date|by|on)|apply\s+(?:by|before|latest|on\s+or\s+before)|"
    r"register\s+(?:by|before|latest)|registrations?\s+(?:close|closes|closing|end|ends|open\s+till|"
    r"open\s+until|till|until)|\bcloses\b|\bclosing\b|\b(?:applications?|forms?|portal|window|submissions?)\s+"
    r"(?:will\s+)?close\b|submi\w*\s+(?:by|before|on\s+or\s+before|"
    r"deadline|latest)|extended\s+(?:to|till|until|up\s?to)|on\s+or\s+before|last\s+day|latest\s+by|"
    r"nominations?\s+(?:by|before|close)|form\s+(?:by|before|closes)|fill\s+(?:the|this)?\s*form\s+by|"
    r"अंतिम\s+तिथि", re.I)
_WEAK = re.compile(r"\b(?:by|before|till|until|upto|up\s+to)\s*:?\s*(?:\w+day,?\s*)?$", re.I)
# Words that mean the date that follows is an event, not a closing date.
_EVENT_WORDS = re.compile(r"felicitat|ceremony|\bevent\b|\bheld\b|result|announc|winner|notification|acceptance|"
                          r"\bstart|commenc|\bbegin|inaugurat|interview|\bexam|\btest\b|\bsession|\bmeet\b|\bperiod\b|"
                          r"\bschedule|finale|qualifi", re.I)
# "deadline is today", "registrations close tomorrow", and subjects like "Last day to apply"
_RELATIVE = re.compile(r"(?:last\s+date|deadline|last\s+day|\bclos(?:es?|ing)\b|\bends?\b|\bdue\b(?!\s+to\b))[^.\n]{0,25}?"
                       r"\b(today|tonight|tomorrow)\b", re.I)
_LAST_DAY = re.compile(r"\b(?:last|final)\s+day\b|\b(?:closes?|ends?|closing)\s+(?:today|tonight)\b|"
                       r"\btoday\s+is\s+the\s+last\b", re.I)
# Header lines of forwarded or quoted mail ("Date: Mon, Sep 28, 2026 at 12:42 PM") are not deadlines.
_HEADER_LINE = re.compile(r"^[> \t]*(?:date|sent)\s*:\s*(?:mon|tue|wed|thu|fri|sat|sun)[a-z]*,?\s[^\n]*$|"
                          r"^[> \t]*on\s+(?:mon|tue|wed|thu|fri|sat|sun)[a-z]*,?\s[^\n]*(?:\n[^\n]*)?\bwrote:[ \t]*$",
                          re.I | re.M)
# Where the quoted or forwarded part of an email starts; "today" there refers to an older date.
_QUOTED = re.compile(r"^-{2,}\s*forwarded message|^[> \t]*on\s.{0,200}wrote:|^>|^from:\s", re.I | re.M)
_HINDI_BY = re.compile(r"\s*(?:तक|से\s+पहले)")  # "15.09.2026 तक" = by 15.09.2026
_EXTENDED = re.compile(r"extend|extension|postpone|revised|new\s+(?:last\s+date|deadline)", re.I)
# Side deadlines that are not the main way in.
_SIDE = re.compile(r"waiver|early[\s-]*bird|accommodation|travel\s+(?:grant|support)|refund|camera[\s-]*ready|"
                   r"award\s+nominations?|hard\s*copy|withdraw|fee\s+payment|payment\s+of", re.I)


def _year(day: int, month: int, year: Optional[str], ref: datetime) -> Optional[date]:
    if year:
        y = int(year)
        y = y + 2000 if y < 100 else y
    else:
        y = ref.year
        try:
            if date(y, month, day) < ref.date() - timedelta(days=75):
                y += 1  # "15 January" written in November means next January
        except ValueError:
            return None
    try:
        return date(y, month, day)
    except ValueError:
        return None


def find_dates(text: str, ref: datetime) -> List[Tuple[int, int, date]]:
    """All dates in text as (start, end, date), ordered by position."""
    found = []
    for m in _DAY_FIRST.finditer(text):
        d = _year(int(m.group(1)), _MONTHS[m.group(2)[:3].lower()], m.group(3), ref)
        if d:
            found.append((m.start(), m.end(), d))
    for m in _MONTH_FIRST.finditer(text):
        d = _year(int(m.group(2)), _MONTHS[m.group(1)[:3].lower()], m.group(3), ref)
        if d:
            found.append((m.start(), m.end(), d))
    for m in _NUMERIC.finditer(text):
        a, b = int(m.group(1)), int(m.group(2))
        day, month = (b, a) if (b > 12 and a <= 12) else (a, b)  # Indian dd/mm unless impossible
        if 1 <= month <= 12:
            d = _year(day, month, m.group(3), ref)
            if d:
                found.append((m.start(), m.end(), d))
    found.sort()
    kept, last_end = [], -1
    for start, end, d in found:  # drop overlapping matches of the same date text
        if start >= last_end:
            kept.append((start, end, d))
            last_end = end
    return kept


def _email_deadline(groups: List[Tuple[str, List[Tuple[date, str]]]], sent: date) -> Optional[Tuple[date, str]]:
    """One email's deadline from its groups of strong dates.

    A group is one keyword and the dates under it ("Last date: Batch 1 - 22 Oct, Batch 2 - 18 Dec"); its
    latest date is the last chance. Across groups the earliest upcoming one is what a newcomer must meet
    ("register by 8 Oct, submit by 20 Oct" -> 8 Oct). An announced extension overrides that, and side
    deadlines (fee waiver, early bird, accommodation) are used only when nothing else is stated.
    """
    if not groups:
        return None
    pick = ([g for kind, g in groups if kind == "extended"]
            or [g for kind, g in groups if kind == "main"] or [g for _, g in groups])
    best = [max(g, key=lambda x: x[0]) for g in pick]
    if groups and any(kind == "extended" for kind, _ in groups):
        return max(best, key=lambda x: x[0])
    upcoming = [b for b in best if b[0] >= sent]
    return min(upcoming, key=lambda x: x[0]) if upcoming else max(best, key=lambda x: x[0])


def deadline(texts: List[Tuple[str, datetime]]) -> Tuple[Optional[date], str, str]:
    """Pick the deadline from (text, email date) pairs of one thread.

    Returns (date, kind, snippet). kind is "deadline" for a stated closing date or "event date" when only
    an event date was found. Each email gives its own deadline; the latest email-level deadline wins, so a
    later extension or a reminder for the next stage replaces an earlier date.
    """
    per_email, weak, event = [], [], []
    for text, ref in texts:
        if not text or ref is None:
            continue
        text = _HEADER_LINE.sub(" ", re.sub(r"[*_]+", "", text))  # Gmail plain text marks bold as *...*
        flat = re.sub(r"\s+", " ", text)
        groups: List[Tuple[str, List[Tuple[date, str]]]] = []
        prev_end, prev_strong = 0, False
        for start, end, d in find_dates(flat, ref):
            if not (ref.date() - timedelta(days=30) <= d <= ref.date() + timedelta(days=550)):
                prev_end, prev_strong = end, False
                continue
            lb_start = max(prev_end, start - 70)
            lookback = flat[lb_start:start]
            keyword = None
            for keyword in _STRONG.finditer(lookback):
                pass  # keep the keyword closest to the date
            fresh_keyword = bool(keyword) and not _EVENT_WORDS.search(lookback[keyword.end():])
            gap = flat[prev_end:start]
            continues = (not fresh_keyword and prev_strong and len(gap) <= 40 and ":" not in gap
                         and len(re.findall(r"[^\W\d_]{2,}", gap)) <= 2 and not _EVENT_WORDS.search(gap))
            snippet = flat[max(0, start - 80):min(len(flat), end + 40)].strip()
            if fresh_keyword:
                label = flat[max(prev_end, lb_start + keyword.start() - 40):start]
                kind = "extended" if _EXTENDED.search(label) else "side" if _SIDE.search(label) else "main"
                groups.append((kind, [(d, snippet)]))
            elif continues:
                groups[-1][1].append((d, snippet))  # a table row under the same heading
            elif _WEAK.search(lookback[-30:]) or _HINDI_BY.match(flat, end):
                weak.append((d, snippet))
            elif d >= ref.date():
                event.append((d, snippet))
            prev_end, prev_strong = end, fresh_keyword or continues
        # Relative deadlines count only in the new part of an email, not in quoted or forwarded text.
        cut = _QUOTED.search(text)
        fresh = re.sub(r"\s+", " ", text[:cut.start()] if cut else text)
        for m in _RELATIVE.finditer(fresh):
            when = ref.date() + timedelta(days=1 if m.group(1).lower() == "tomorrow" else 0)
            groups.append(("main", [(when, fresh[max(0, m.start() - 60):m.end() + 40].strip())]))
        subject = text.split("\n", 1)[0]
        if _LAST_DAY.search(subject) and not find_dates(subject, ref):
            groups.append(("main", [(ref.date(), subject.strip())]))
        found = _email_deadline(groups, ref.date())
        if found:
            per_email.append(found)
    if per_email:
        d, s = max(per_email, key=lambda x: x[0])
        return d, "deadline", s
    if weak:
        d, s = min(weak, key=lambda x: x[0])
        return d, "deadline", s
    if event:
        d, s = min(event, key=lambda x: x[0])
        return d, "event date", s
    return None, "", ""
