"""Group emails into threads and decide which threads are opportunities."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Callable, Dict, List, Optional, Sequence

from . import rules
from .dates import deadline
from .reader import Mail

OPPORTUNITIES, REVIEW, CAMPUS, PITCHES = "Opportunities", "Review", "Campus-only", "Excluded pitches"

_PREFIX = re.compile(
    r"^\s*(?:(?:re|fwd?|fw|aw|sv|wg|tr|rv)\s*(?:\[\d+\])?\s*:\s*|\[(?:external|ext|important|reminder)\]\s*|"
    r"(?:gentle |final |last |friendly )?reminder\s*[:\-|]\s*|(?:urgent|important)\s*[:\-|]\s*)+", re.I)
_URL = re.compile(r"https?://[^\s<>()\"'\]\[|]+")
# Links that act for the recipient (unsubscribe, tracking redirects, links carrying an email or token).
_PERSONAL_LINK = re.compile(
    r"(?:https?://|www\.)[^\s<>\"')\]]*?(?:unsubscribe|optout|opt-out|/preferences|manage[-_]?subscription|"
    r"list-manage|mailchi\.mp|/track|/wf/click|//click\.|sendgrid\.net|mandrillapp|"
    r"[?&](?:e|u|uid|email|mail|token|sig|hash|key|recipient|subscriber(?:_?id)?|user(?:_?id)?)=)"
    r"[^\s<>\"')\]]*", re.I)
# First names that are also everyday words or festival names; hiding them would garble other text.
_COMMON_WORD_NAMES = {"will", "bill", "hope", "grace", "faith", "rose", "summer", "june", "april", "august", "mark",
                      "frank", "sunny", "happy", "prince", "king", "dawn", "star", "angel", "jean", "joy", "may",
                      "durga", "ganesh", "ganesha", "krishna", "lakshmi", "laxmi", "shiva", "saraswati", "rama",
                      "kali", "ganga", "diwali", "deepak", "jyoti", "kiran", "vijay", "vikas", "pragati", "unnati",
                      "shakti", "seva", "asha", "disha", "kalpana", "pratibha", "pratiksha", "sakshi"}
# "To:" and "Cc:" lines of forwarded headers list who else received the mail.
_RECIPIENT_LINES = re.compile(r"^[> \t]*(?:to|cc|bcc)\s*:[^\n]*(?:\n[> \t]+[^\n]*@[^\n]*)*", re.I | re.M)


@dataclass
class Result:
    key: str
    title: str
    bucket: Optional[str]
    type: str
    scope: str
    score: int
    confidence: str
    reasons: List[str]
    deadline: Optional[date]
    deadline_kind: str
    deadline_text: str
    links: List[str]
    summary: str
    full_text: str
    sender_name: str
    sender: str
    first_seen: Optional[datetime]
    last_update: Optional[datetime]
    n_emails: int
    attachments: List[str]
    message_ids: List[str]
    college: str = ""
    extra: Dict = field(default_factory=dict)


def thread_key(subject: str) -> str:
    return re.sub(r"\s+", " ", _PREFIX.sub("", subject or "")).strip(" .-:|").lower()


def clean_title(subject: str) -> str:
    return re.sub(r"\s+", " ", _PREFIX.sub("", subject or "")).strip() or "(no subject)"


def _search(pattern: str, text: str) -> bool:
    return bool(re.search(pattern, text, re.I))


# --------------------------------------------------------------------------- text helpers
def summarize(body: str, limit: int = 700) -> str:
    """Announcement text without forwarding headers, quoted replies and blank runs."""
    out, skipping_header = [], False
    for line in body.splitlines():
        s = line.strip()
        if re.match(r"-{2,}\s*forwarded message\s*-{2,}", s, re.I) or re.match(r"(?i)^begin forwarded message", s):
            skipping_header = True
            continue
        if skipping_header:
            if re.match(r"(?i)^(from|date|sent|subject|to|cc)\s*:", s) or not s:
                continue
            skipping_header = False
        if s.startswith(">") or re.match(r"(?i)^on .{5,150}wrote:\s*$", s):
            continue
        out.append(s)
    text = re.sub(r"\n{2,}", "\n", "\n".join(out)).strip()
    return text[:limit] + ("…" if len(text) > limit else "")


def make_redactor(owner: str, owner_name: str) -> Callable[[str], str]:
    """Hide the mailbox owner's address, roll number and name, recipient lists and personal links."""
    patterns = []
    if owner:
        patterns += [re.escape(owner), re.escape(owner.replace("@", "%40"))]
        local = owner.split("@")[0]
        if len(local) >= 5 and re.search(r"\d", local):
            patterns.append(r"\b" + re.escape(local) + r"\b")  # roll-number style IDs
    name = re.sub(r"\s+", " ", owner_name or "").strip()
    if len(name) >= 5:
        patterns.append(r"\s+".join(re.escape(part) for part in name.split()))
        first = name.split()[0]
        if len(first) >= 3:
            if first.lower() in _COMMON_WORD_NAMES:  # only where it is clearly a greeting
                patterns.append(r"(?:(?<=\bdear )|(?<=\bhi )|(?<=\bhello )|(?<=\bhey ))" + re.escape(first) + r"\b")
            else:
                patterns.append(r"\b" + re.escape(first) + r"\b")  # "Riya, click to know more"
    rx = re.compile("|".join(patterns), re.I) if patterns else None

    def redact(s: str) -> str:
        if not s:
            return s
        s = _RECIPIENT_LINES.sub("", s)
        s = _PERSONAL_LINK.sub("[personal link removed]", s)
        return rx.sub("[you]", s) if rx else s
    return redact


def key_links(texts: Sequence[str], owner: str) -> List[str]:
    seen, good, other = set(), [], []
    for text in texts:
        for url in _URL.findall(text or ""):
            url = url.rstrip(".,;:*>)]}\"'")
            if url in seen:
                continue
            seen.add(url)
            if _search(rules.BAD_LINK, url) or _PERSONAL_LINK.match(url) or \
                    (owner and (owner.lower() in url.lower() or owner.lower().replace("@", "%40") in url.lower())):
                continue
            (good if _search(rules.GOOD_LINK, url) else other).append(url)
    return good[:3] if good else other[:2]


# --------------------------------------------------------------------------- scoring
def score_thread(subject: str, body: str, sender: str, bulk: bool, placement_senders: Sequence[str]):
    reasons, score = [], 0
    hits = sorted(((w, label) for label, p, w in rules.SUBJECT_RULES if _search(p, subject)), reverse=True)
    for w, label in hits[:2]:
        score += w
        reasons.append(label)
    if not hits:  # nothing in the subject: let the opening lines of the body speak, at half weight
        lead = body[:700]
        lead_hits = sorted(((w, label) for label, p, w in rules.SUBJECT_RULES if _search(p, lead)), reverse=True)
        if lead_hits:
            score += lead_hits[0][0] // 2
            reasons.append(lead_hits[0][1] + " (in text)")
    body_points = 0
    for label, p, w in rules.BODY_RULES:
        if _search(p, body[:6000]):
            body_points += w
            reasons.append(label)
    score += min(body_points, rules.BODY_CAP)
    for label, p, w in rules.NEGATIVE_RULES:
        if _search(p, subject):
            score += w
            reasons.append("not: " + label)
    for label, p, w in rules.SENDER_RULES:
        if _search(p, sender):
            score += w
            reasons.append("not: " + label)
    if sender and (re.match(rules.PLACEMENT_SENDER, sender, re.I) or sender in placement_senders):
        score += rules.PLACEMENT_BONUS
        reasons.append("placement/career cell sender")
    if bulk:
        score += rules.BULK_PENALTY
    return score, reasons


def pitch_score(subject: str, body: str, sender: str):
    score, reasons = 0, []
    domain = sender.split("@")[-1] if "@" in sender else ""
    if any(d and d in domain for d in rules.PITCH_DOMAINS):
        score += 6
        reasons.append("known paid-programme sender")
    text = subject + "\n" + body[:4000]
    for label, p, w in rules.PITCH_RULES:
        if _search(p, text):
            score += w
            reasons.append(label)
    return score, reasons


def opportunity_type(subject: str, body: str) -> str:
    for text in (subject, body[:1500]):
        for name, pattern in rules.TYPE_RULES:
            if _search(pattern, text):
                return name
    return "Other Opportunity"


def _is_internal(address: str, institution: str) -> bool:
    domain = address.split("@")[-1] if "@" in address else ""
    return bool(institution) and (domain == institution or domain.endswith("." + institution))


def _student_body_or_student(sender: str) -> bool:
    local = sender.split("@")[0].lower()
    tokens = re.split(r"[._\-+]", local)
    if any(t in rules.STUDENT_BODY_TOKENS or t.startswith(("gsec", "messsec", "secy")) for t in tokens):
        return True
    return len(re.findall(r"\d", local)) >= 3  # roll-number style personal address


def _points_outside(body: str, institution: str) -> bool:
    """True if the email forwards an outside sender or links to an outside website."""
    for m in re.finditer(r"(?im)^\s*from:.*?@([\w.-]+)", body):
        if not _is_internal("x@" + m.group(1), institution):
            return True
    for url in _URL.findall(body):
        host = re.sub(r"^https?://", "", url).split("/")[0].split(":")[0].lower()
        if not host or _is_internal("x@" + host, institution):
            continue
        if not any(host == d or host.endswith("." + d) for d in rules.NEUTRAL_LINK_DOMAINS):
            return True
    return False


def scope_of(kind: str, subject: str, body: str, sender: str, institution: str, placement: bool) -> str:
    internal = _is_internal(sender, institution)
    if kind == "Campus Selection / Induction":
        return "Campus"
    if internal and _search(rules.CAMPUS_SUBJECT, subject):
        return "Campus"
    if internal and len(set(m.lower() for m in re.findall(rules.CAMPUS_BODY, body[:3000], re.I))) >= 2:
        return "Campus"
    if internal and placement and kind in ("Internship", "Job / Recruitment"):
        return "Placement cell"
    if (internal and kind not in rules.OUTWARD_TYPES and _student_body_or_student(sender)
            and not _points_outside(body, institution) and not _search(rules.OPEN_TO_OTHERS, subject + " " + body[:3000])):
        return "Campus"  # a club, council, hall or student announcing its own event
    return "External"


# --------------------------------------------------------------------------- threads
def group_threads(mails: List[Mail], gap_days: int = 60) -> List[List[Mail]]:
    by_key: Dict[str, List[Mail]] = {}
    for m in mails:
        key = thread_key(m.subject) or ("id:" + (m.message_id or str(id(m))))
        by_key.setdefault(key, []).append(m)
    threads = []
    for items in by_key.values():
        items.sort(key=lambda m: m.date or datetime.min)
        current = [items[0]]
        for m in items[1:]:
            prev = current[-1].date
            if m.date and prev and (m.date - prev) > timedelta(days=gap_days):
                threads.append(current)
                current = [m]
            else:
                current.append(m)
        threads.append(current)
    return threads


def classify(mails: List[Mail], owner: str, owner_name: str = "", keep_direct: bool = False,
             placement_senders: Sequence[str] = ()) -> List[Result]:
    institution = owner.split("@")[-1] if "@" in owner else ""
    placement_senders = [s.lower() for s in placement_senders]
    redact = make_redactor(owner, owner_name)

    def is_direct(m: Mail) -> bool:
        """Written to you personally (not a list, not an automated sender) - kept private by default."""
        if not owner or m.to != [owner] or m.cc or m.bulk:
            return False
        return not re.match(rules.AUTOMATED_SENDER, m.sender.split("@")[0], re.I)

    usable = [m for m in mails
              if m.sender != owner and not any(l.lower() == "sent" for l in m.labels)
              and (keep_direct or not is_direct(m))]

    results: List[Result] = []
    for thread in group_threads(usable):
        first = thread[0]
        subject, body, sender = first.subject, first.body, first.sender
        score, reasons = score_thread(subject, body, sender, first.bulk, placement_senders)
        p_score, p_reasons = pitch_score(subject, body, sender)
        placement = bool(sender) and (bool(re.match(rules.PLACEMENT_SENDER, sender, re.I)) or sender in placement_senders)
        kind = opportunity_type(subject, body)
        scope = scope_of(kind, subject, body, sender, institution, placement)

        if p_score >= rules.PITCH and score >= rules.MEDIUM - 2:
            bucket = PITCHES
            reasons = p_reasons
        elif score >= rules.HIGH:
            bucket = CAMPUS if scope == "Campus" else OPPORTUNITIES
        elif score >= rules.MEDIUM:
            bucket = CAMPUS if scope == "Campus" else REVIEW
        else:
            bucket = None
        if bucket is None:
            results.append(Result(thread_key(subject), clean_title(subject), None, kind, scope, score, "", reasons,
                                  None, "", "", [], "", "", first.sender_name, sender, first.date,
                                  thread[-1].date, len(thread), [], [m.message_id for m in thread]))
            continue

        d, d_kind, d_text = deadline([(m.subject + "\n" + m.body, m.date) for m in thread])
        attachments = sorted({redact(a) for m in thread for a in m.attachments})
        results.append(Result(
            key=thread_key(redact(subject)), title=redact(clean_title(subject)), bucket=bucket, type=kind, scope=scope,
            score=score, confidence="High" if score >= rules.HIGH else "Medium", reasons=reasons,
            deadline=d, deadline_kind=d_kind, deadline_text=redact(d_text),
            links=key_links([m.body for m in thread], owner),
            summary=redact(summarize(body)), full_text=redact(body),
            sender_name=redact(first.sender_name), sender=sender,
            first_seen=first.date, last_update=thread[-1].date, n_emails=len(thread),
            attachments=attachments, message_ids=[m.message_id for m in thread if m.message_id],
        ))
    return results
