"""Read emails from a Google Takeout .zip, .mbox file(s), a folder, or a spreadsheet export.

The reader streams the mailbox line by line, so multi-gigabyte exports do not need to fit in memory.
"""
from __future__ import annotations

import csv
import email
import io
import os
import re
import sys
import zipfile
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from email import policy
from email.parser import BytesHeaderParser
from email.utils import getaddresses, parsedate_to_datetime
from html.parser import HTMLParser
from typing import Iterable, Iterator, List, Optional, Tuple

MAX_BODY = 30000  # characters kept per email body

# "From <id> <weekday> <month> <day> hh:mm:ss <+zone> <year>" separator lines (Gmail, Thunderbird).
_SEPARATOR = re.compile(rb"^From \S+.*\d{1,2}:\d{2}(?::\d{2})?.*\d{4}\s*$")
_SKIP_LABELS = {"spam", "trash", "drafts", "draft", "chat", "chats"}
_BULK_CATEGORIES = {"category promotions", "category social", "category updates", "category forums"}


@dataclass
class Mail:
    date: Optional[datetime]
    sender_name: str
    sender: str
    to: List[str]
    cc: List[str]
    named_recipients: List[Tuple[str, str]]
    subject: str
    message_id: str
    attachments: List[str]
    body: str
    labels: List[str] = field(default_factory=list)
    delivered_to: str = ""
    bulk: bool = False

    @property
    def recipients(self) -> List[str]:
        return self.to + self.cc


# --------------------------------------------------------------------------- HTML to text
class _HTMLText(HTMLParser):
    _BLOCK = {"p", "div", "br", "li", "tr", "table", "ul", "ol", "h1", "h2", "h3", "h4", "h5", "h6",
              "section", "article", "header", "footer", "blockquote", "hr", "center"}
    _HIDDEN = {"style", "script", "head", "title"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.out: List[str] = []
        self.hidden = 0
        self.href: Optional[str] = None
        self.link_start = 0

    def handle_starttag(self, tag, attrs):
        if tag in self._HIDDEN:
            self.hidden += 1
        elif tag in self._BLOCK:
            self.out.append("\n")
        if tag == "li":
            self.out.append("- ")
        if tag == "a":
            self.href = dict(attrs).get("href") or None
            self.link_start = len(self.out)

    def handle_endtag(self, tag):
        if tag in self._HIDDEN:
            self.hidden = max(0, self.hidden - 1)
        if tag == "a" and self.href:
            text = "".join(self.out[self.link_start:]).strip()
            href = self.href.strip()
            if href.lower().startswith("http") and href not in text:
                self.out.append(f" ({href})")
            self.href = None
        if tag in self._BLOCK:
            self.out.append("\n")
        elif tag in ("td", "th"):
            self.out.append(" ")

    def handle_data(self, data):
        if not self.hidden:
            self.out.append(data)


def html_to_text(html: str) -> str:
    parser = _HTMLText()
    try:
        parser.feed(html)
        parser.close()
    except Exception:  # malformed HTML: fall back to stripping tags
        return re.sub(r"<[^>]+>", " ", html)
    return "".join(parser.out)


_DISCLAIMER = re.compile(
    r"(?is)\*?\s*disclaimer\s*:?\*?.{0,1200}?(?:prohibited|strictly prohibited|delete (?:it|this e-?mail)[^.]*)\.?"
    r"|this e-?mail and any files transmitted with it.{0,900}?(?:prohibited|delete[^.]*)\.?")


def tidy(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("​", "").replace("\xa0", " ")
    text = _DISCLAIMER.sub(" ", text)
    text = re.sub(r"[ \t\f\v]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()[:MAX_BODY]


# --------------------------------------------------------------------------- message parsing
def _header(msg, name: str) -> str:
    try:
        value = msg.get(name)
        return str(value) if value is not None else ""
    except Exception:
        try:
            return str(msg.get_all(name, [""])[0])
        except Exception:
            return ""


def _addresses(value: str) -> List[Tuple[str, str]]:
    try:
        return [(n.strip(), a.strip().lower()) for n, a in getaddresses([value]) if a and "@" in a]
    except Exception:
        return []


def parse_date(value) -> Optional[datetime]:
    if isinstance(value, datetime):
        return value.replace(tzinfo=None) if value.tzinfo is None else value.astimezone().replace(tzinfo=None)
    if value is None or str(value).strip() in ("", "nan", "None"):
        return None
    text = str(value).strip()
    try:
        dt = parsedate_to_datetime(text)
    except Exception:
        dt = None
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d",
                    "%d-%m-%Y %H:%M", "%d/%m/%Y %H:%M", "%d/%m/%Y"):
            try:
                dt = datetime.strptime(text[:19], fmt)
                break
            except ValueError:
                continue
    if dt is None:
        return None
    return dt.astimezone().replace(tzinfo=None) if dt.tzinfo else dt


def _content(part) -> str:
    try:
        content = part.get_content()
        return content.decode("utf-8", "replace") if isinstance(content, bytes) else str(content)
    except Exception:
        payload = part.get_payload(decode=True) or b""
        charset = part.get_content_charset() or "utf-8"
        try:
            return payload.decode(charset, "replace")
        except LookupError:
            return payload.decode("utf-8", "replace")


def _body(msg) -> str:
    plain = html = ""
    try:
        part = msg.get_body(preferencelist=("plain",))
        plain = _content(part) if part is not None else ""
    except Exception:
        pass
    try:
        part = msg.get_body(preferencelist=("html",))
        html = _content(part) if part is not None else ""
    except Exception:
        pass
    if not plain and not html and not msg.is_multipart():
        raw = _content(msg)
        if msg.get_content_type() == "text/html":
            html = raw
        else:
            plain = raw
    if len(plain.strip()) >= 200 or not html:
        return tidy(plain)
    return tidy(html_to_text(html))


def _attachments(msg) -> List[str]:
    names: List[str] = []
    try:
        for part in msg.iter_attachments():
            name = part.get_filename()
            if not name:
                continue
            if part.get_content_maintype() == "image" and re.match(r"(?i)image\d*\.(png|jpe?g|gif)$", name):
                continue  # inline signature images
            names.append(name)
    except Exception:
        pass
    return names


def parse_message(raw: bytes) -> Optional[Mail]:
    try:
        msg = email.message_from_bytes(raw, policy=policy.default)
    except Exception:
        return None
    sender = _addresses(_header(msg, "From"))
    to = _addresses(_header(msg, "To"))
    cc = _addresses(_header(msg, "Cc"))
    labels = [x.strip() for x in _header(msg, "X-Gmail-Labels").split(",") if x.strip()]
    precedence = _header(msg, "Precedence").lower()
    bulk = bool(_header(msg, "List-Unsubscribe") or _header(msg, "List-Id")
                or precedence in ("bulk", "list", "junk")
                or any(label.lower() in _BULK_CATEGORIES for label in labels))
    delivered = _addresses(_header(msg, "Delivered-To"))
    return Mail(
        date=parse_date(_header(msg, "Date")),
        sender_name=sender[0][0] if sender else "",
        sender=sender[0][1] if sender else "",
        to=[a for _, a in to],
        cc=[a for _, a in cc],
        named_recipients=to + cc,
        subject=re.sub(r"\s+", " ", _header(msg, "Subject")).strip(),
        message_id=_header(msg, "Message-ID").strip(),
        attachments=_attachments(msg),
        body=_body(msg),
        labels=labels,
        delivered_to=delivered[0][1] if delivered else "",
        bulk=bulk,
    )


# --------------------------------------------------------------------------- mbox streaming
def split_mbox(stream: Iterable[bytes]) -> Iterator[bytes]:
    """Yield raw messages from an mbox byte stream (handles mboxo and mboxrd escaping)."""
    chunk: List[bytes] = []
    started = False
    for line in stream:
        if line.startswith(b"From ") and _SEPARATOR.match(line.rstrip(b"\r\n")):
            if started and chunk:
                yield b"".join(chunk)
            chunk, started = [], True
            continue
        if not started:
            continue
        if line[:1] == b">" and line.lstrip(b">").startswith(b"From "):
            line = line[1:]
        chunk.append(line)
    if started and chunk:
        yield b"".join(chunk)


def _looks_like_mbox(path: str) -> bool:
    """Thunderbird keeps each folder as an mbox file without an extension (Inbox, Sent, ...)."""
    try:
        with open(path, "rb") as fh:
            return fh.read(5) == b"From "
    except OSError:
        return False


def _mbox_sources(path: str, top: bool = True) -> Iterator[Tuple[str, object]]:
    """Yield (name, binary stream factory) for every mailbox inside path."""
    lower = path.lower()
    if os.path.isdir(path):
        for root, dirs, files in os.walk(path):
            dirs[:] = sorted(d for d in dirs if not d.startswith("."))
            for name in sorted(files):
                full, low = os.path.join(root, name), name.lower()
                if low.endswith((".mbox", ".mbx", ".zip")):
                    yield from _mbox_sources(full, top=False)
                elif low.endswith(".eml"):
                    yield full, lambda f=full: _single(f)
                elif name.startswith(".") or low.endswith(_NOT_MAIL):
                    continue
                elif _looks_like_mbox(full):
                    yield full, lambda f=full: open(f, "rb", buffering=1 << 20)
                elif os.path.basename(root) in ("cur", "new"):  # maildir: one message per file
                    yield full, lambda f=full: _single(f)
        return
    if lower.endswith(".zip"):
        archive = zipfile.ZipFile(path)
        try:
            members = [m for m in archive.namelist() if m.lower().endswith((".mbox", ".mbx"))]
            if not members and top:
                raise SystemExit(f"No .mbox file found inside {os.path.basename(path)}. "
                                 "Make sure you exported Mail from Google Takeout.")
            for member in members:
                yield f"{os.path.basename(path)}:{member}", (
                    lambda m=member: io.BufferedReader(archive.open(m), buffer_size=1 << 20))
        finally:
            archive.close()
        return
    yield path, lambda: open(path, "rb", buffering=1 << 20)


_NOT_MAIL = (".msf", ".dat", ".json", ".html", ".htm", ".sqlite", ".xlsx", ".csv", ".pdf", ".py", ".md", ".txt")


def _single(path: str):
    with open(path, "rb") as fh:
        data = fh.read()
    return [b"From MAILER-DAEMON Thu Jan 01 00:00:00 +0000 1970\n"] + data.splitlines(keepends=True)


# --------------------------------------------------------------------------- spreadsheet input
_COLUMN_ALIASES = {
    "date": ("date", "sent", "received", "datetime"),
    "from": ("from", "sender"),
    "to": ("to", "recipients"),
    "cc": ("cc",),
    "subject": ("subject", "title"),
    "message-id": ("message-id", "message id", "messageid", "id"),
    "attachments": ("attachments", "attachment"),
    "body": ("body", "text", "content", "message"),
    "labels": ("labels", "x-gmail-labels", "folder"),
}


def _table_rows(path: str) -> Iterator[dict]:
    if path.lower().endswith(".csv"):
        with open(path, newline="", encoding="utf-8-sig", errors="replace") as fh:
            csv.field_size_limit(min(sys.maxsize, 2 ** 31 - 1))
            yield from csv.DictReader(fh)
        return
    from openpyxl import load_workbook
    wb = load_workbook(path, read_only=True, data_only=True)
    ws = wb.worksheets[0]
    rows = ws.iter_rows(values_only=True)
    header = [str(h or "").strip() for h in next(rows)]
    for values in rows:
        yield dict(zip(header, values))
    wb.close()


def _read_table(path: str) -> Iterator[Mail]:
    mapping = None
    for row in _table_rows(path):
        if mapping is None:
            keys = {k.lower().strip(): k for k in row.keys() if k}
            mapping = {field_: next((keys[a] for a in aliases if a in keys), None)
                       for field_, aliases in _COLUMN_ALIASES.items()}
            if not mapping["subject"] or not mapping["body"]:
                raise SystemExit("The spreadsheet needs at least 'Subject' and 'Body' columns.")

        def get(name):
            col = mapping.get(name)
            value = row.get(col) if col else None
            return "" if value is None else value

        sender = _addresses(str(get("from")))
        to, cc = _addresses(str(get("to"))), _addresses(str(get("cc")))
        attachments = [a.strip() for a in re.split(r"[;\n]", str(get("attachments"))) if a.strip()]
        yield Mail(
            date=parse_date(get("date")),
            sender_name=sender[0][0] if sender else "",
            sender=sender[0][1] if sender else str(get("from")).strip().lower(),
            to=[a for _, a in to], cc=[a for _, a in cc], named_recipients=to + cc,
            subject=re.sub(r"\s+", " ", str(get("subject"))).strip(),
            message_id=str(get("message-id")).strip(),
            attachments=[a for a in attachments if a.lower() != "nan"],
            body=tidy(str(get("body"))),
            labels=[x.strip() for x in str(get("labels")).split(",") if x.strip()],
        )


_HEADERS_ONLY = BytesHeaderParser(policy=policy.default)


def _skip_quickly(raw: bytes, since: Optional[datetime], until: Optional[datetime]) -> bool:
    """True when the headers alone show the message is spam/trash/draft or outside the date range."""
    try:
        head = _HEADERS_ONLY.parsebytes(raw[:65536])
        labels = [x.strip().lower() for x in str(head.get("X-Gmail-Labels", "") or "").split(",")]
        if any(label in _SKIP_LABELS for label in labels):
            return True
        status = str(head.get("X-Mozilla-Status", "") or "").strip()
        if status and int(status, 16) & 0x0008:
            return True  # deleted in Thunderbird but not yet compacted out of the file
        when = parse_date(str(head.get("Date", "") or ""))
    except Exception:
        return False
    return bool(when and ((since and when < since) or (until and when > until)))


# --------------------------------------------------------------------------- public API
def read_mails(path: str, since: Optional[datetime] = None, until: Optional[datetime] = None,
               progress=None) -> List[Mail]:
    """Read every email at path, dropping spam/trash/drafts, duplicates and out-of-range dates."""
    if not os.path.exists(path):
        raise SystemExit(f"File or folder not found: {path}")
    counter = [0]
    if path.lower().endswith((".xlsx", ".xlsm", ".csv")):
        source = _read_table(path)
    else:
        def from_mbox():
            for _, factory in _mbox_sources(path):
                stream = factory()
                try:
                    for raw in split_mbox(stream):
                        counter[0] += 1
                        if progress and counter[0] % 5000 == 0:
                            progress(counter[0])
                        if _skip_quickly(raw, since, until):
                            continue  # decided from headers alone, body never decoded
                        mail = parse_message(raw)
                        if mail is not None:
                            yield mail
                finally:
                    if hasattr(stream, "close"):
                        stream.close()
        source = from_mbox()

    mails: List[Mail] = []
    seen = set()
    for mail in source:
        if any(label.lower() in _SKIP_LABELS for label in mail.labels):
            continue
        if since and mail.date and mail.date < since:
            continue
        if until and mail.date and mail.date > until:
            continue
        key = mail.message_id or f"{mail.date}|{mail.sender}|{mail.subject}"
        if key in seen:
            continue
        seen.add(key)
        mails.append(mail)
    return mails


def detect_owner(mails: List[Mail]) -> Tuple[str, str]:
    """Guess the mailbox owner's address and display name."""
    delivered = Counter(m.delivered_to for m in mails if m.delivered_to)
    if delivered:
        owner = delivered.most_common(1)[0][0]
    else:
        sent = Counter(m.sender for m in mails if m.sender)
        received = Counter(a for m in mails for a in set(m.recipients))
        scores = {a: min(sent[a], received[a]) for a in sent if received.get(a)}
        if scores and max(scores.values()) >= 3:
            owner = max(scores, key=scores.get)
        else:
            owner = received.most_common(1)[0][0] if received else ""
    names = Counter(n for m in mails for n, a in m.named_recipients if a == owner and n and "@" not in n)
    names.update(m.sender_name for m in mails if m.sender == owner and m.sender_name and "@" not in m.sender_name)
    return owner, (names.most_common(1)[0][0] if names else "")
