"""Excel output: the shareable opportunities file, the private review file, and the E-Cell master file."""
from __future__ import annotations

import os
import re
from datetime import date, datetime
from typing import Dict, Iterable, List, Optional

from openpyxl import Workbook, load_workbook
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.workbook.properties import CalcProperties

from . import __version__
from .classify import Result, thread_key

COLUMNS = [  # (header, width, wrap)
    ("Title", 46, True), ("Type", 24, False), ("Scope", 14, False), ("Deadline", 13, False),
    ("Status", 14, False), ("Days left", 9, False), ("Key links", 42, True), ("Summary", 80, True),
    ("From", 26, False), ("Sender email", 30, False), ("First seen", 17, False), ("Last update", 17, False),
    ("Emails in thread", 9, False), ("Deadline text", 50, True), ("Attachments", 30, False),
    ("Confidence", 11, False), ("Why flagged", 40, False), ("Shared by", 22, False), ("Times shared", 9, False),
    ("Full text", 80, False), ("Message-IDs", 40, False), ("Thread key", 40, False),
]
HEADERS = [c[0] for c in COLUMNS]
COL = {name: get_column_letter(i) for i, name in enumerate(HEADERS, start=1)}

_ILLEGAL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
NAVY = "1F3864"
HEAD_FILL = PatternFill("solid", fgColor=NAVY)
HEAD_FONT = Font(name="Arial", size=10, bold=True, color="FFFFFF")
BODY_FONT = Font(name="Arial", size=10)
GREY_FONT = Font(name="Arial", size=10, color="8C8C8C")
TITLE_FONT = Font(name="Arial", size=14, bold=True, color=NAVY)
NOTE_FONT = Font(name="Arial", size=10, color="404040")
GREEN = PatternFill("solid", fgColor="D9F2E1")
AMBER = PatternFill("solid", fgColor="FFE8B3")
THIN = Border(bottom=Side(style="thin", color="D9D9D9"))


def _clean(value):
    if value is None:
        return None
    if isinstance(value, (int, float, date, datetime)):
        return value
    return _ILLEGAL.sub("", str(value))[:32000]


def result_row(r: Result, college: str = "") -> Dict:
    text = r.deadline_text
    if r.deadline and r.deadline_kind == "event date":
        text = "[event date - no deadline stated] " + text
    return {
        "Title": r.title, "Type": r.type, "Scope": r.scope, "Deadline": r.deadline,
        "Key links": "\n".join(r.links), "Summary": r.summary, "From": r.sender_name, "Sender email": r.sender,
        "First seen": r.first_seen, "Last update": r.last_update, "Emails in thread": r.n_emails,
        "Deadline text": text, "Attachments": "; ".join(r.attachments), "Confidence": r.confidence,
        "Why flagged": ", ".join(r.reasons), "Shared by": college, "Times shared": 1,
        "Full text": r.full_text, "Message-IDs": " ".join(r.message_ids), "Thread key": r.key,
    }


def _sort_key(row: Dict, today: date):
    d = row.get("Deadline")
    if isinstance(d, datetime):
        d = d.date()
    if d and d >= today:
        return (0, d.toordinal(), "")
    if not d:
        seen = row.get("First seen") or datetime.min
        return (1, -seen.toordinal() if hasattr(seen, "toordinal") else 0, "")
    return (2, -d.toordinal(), "")


def _write_table(ws, rows: List[Dict]):
    for c, (name, width, _) in enumerate(COLUMNS, start=1):
        cell = ws.cell(row=1, column=c, value=name)
        cell.font, cell.fill = HEAD_FONT, HEAD_FILL
        cell.alignment = Alignment(vertical="center", wrap_text=True)
        ws.column_dimensions[get_column_letter(c)].width = width
    ws.row_dimensions[1].height = 30
    today = date.today()
    rows = sorted(rows, key=lambda r: _sort_key(r, today))
    for i, row in enumerate(rows, start=2):
        for c, (name, _, wrap) in enumerate(COLUMNS, start=1):
            cell = ws.cell(row=i, column=c, value=_clean(row.get(name)))
            cell.font, cell.border = BODY_FONT, THIN
            cell.alignment = Alignment(vertical="top", wrap_text=wrap)
        d, s, n = COL["Deadline"], COL["Status"], COL["Days left"]
        ws[f"{s}{i}"] = (f'=IF(ISNUMBER({d}{i}),IF({d}{i}<TODAY(),"Closed",'
                         f'IF({d}{i}=TODAY(),"Closes today","Open")),"No date found")')
        ws[f"{n}{i}"] = f'=IF(ISNUMBER({d}{i}),IF({d}{i}>=TODAY(),{d}{i}-TODAY(),""),"")'
        for name, fmt in (("Deadline", "dd mmm yyyy"), ("First seen", "dd mmm yyyy hh:mm"),
                          ("Last update", "dd mmm yyyy hh:mm"), ("Days left", "0")):
            ws[f"{COL[name]}{i}"].number_format = fmt
        for name in ("Status", "Days left"):
            ws[f"{COL[name]}{i}"].font, ws[f"{COL[name]}{i}"].border = BODY_FONT, THIN
        links = (row.get("Key links") or "").split("\n")
        if links and links[0].startswith("http"):
            ws[f"{COL['Key links']}{i}"].hyperlink = links[0]
    last = max(len(rows) + 1, 2)
    status = f"{COL['Status']}2:{COL['Status']}{last}"
    first = f"${COL['Status']}2"
    ws.conditional_formatting.add(status, FormulaRule(formula=[f'{first}="Open"'], fill=GREEN))
    ws.conditional_formatting.add(status, FormulaRule(formula=[f'{first}="Closes today"'], fill=AMBER))
    ws.conditional_formatting.add(status, FormulaRule(formula=[f'{first}="Closed"'], font=GREY_FONT))
    ws.freeze_panes = "B2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(COLUMNS))}{last}"


def _about(ws, title: str, lines: Iterable[str]):
    ws.column_dimensions["A"].width = 110
    ws["A1"] = title
    ws["A1"].font = TITLE_FONT
    for i, line in enumerate(lines, start=3):
        cell = ws.cell(row=i, column=1, value=_clean(line))
        cell.font = NOTE_FONT
        cell.alignment = Alignment(wrap_text=True, vertical="top")


def _new_workbook() -> Workbook:
    wb = Workbook()
    wb.calculation = CalcProperties(fullCalcOnLoad=True)  # Status/Days left recalculate on open
    return wb


def write_share(path: str, rows: List[Dict], meta: Dict):
    wb = _new_workbook()
    about = wb.active
    about.title = "About"
    _about(about, "Opportunity emails" + (f" — shared by {meta['college']}" if meta.get("college") else ""), [
        f"Emails from {meta['since']} to {meta['until']} · {len(rows)} opportunities · "
        f"made {meta['made']} with opportunity-mail-extractor {__version__}",
        "College: " + (meta.get("college") or "(not given)"),
        "",
        "This file is meant to be shared. It contains only emails the tool judged to be opportunities.",
        "Your own email address and name were replaced with [you]. Personal emails addressed only to you, "
        "emails you sent, and spam/trash were left out.",
        "Before sending it, scroll through the Opportunities sheet once and delete any row you do not want "
        "to share (select the row number, right-click, Delete).",
        "Rows whose Scope is 'Placement cell' are your college placement cell's own notices. Many are open only "
        "to your college, and some placement cells do not allow sharing them: delete those rows if so.",
        "",
        "Status and Days left update by themselves: they compare the Deadline with today's date.",
        "Deadlines are read from the email text. Always confirm on the official page before applying.",
    ])
    _write_table(wb.create_sheet("Opportunities"), rows)
    wb.active = 1
    wb.save(path)


def write_review(path: str, review: List[Dict], campus: List[Dict], pitches: List[Dict], meta: Dict,
                 placement: Optional[List[Dict]] = None):
    wb = _new_workbook()
    about = wb.active
    about.title = "Read me"
    lines = [
        "These are emails the tool was unsure about, or that only matter inside your college.",
        f"Review ({len(review)}): might be opportunities. If a row is a real opportunity, copy the whole row and "
        "paste it at the bottom of the Opportunities sheet in the share file.",
        f"Campus-only ({len(campus)}): club inductions, hostel and fest events, inter-college team selections. "
        "Useful to you, not to students of other colleges.",
        f"Excluded pitches ({len(pitches)}): paid 'training & internship' programmes sent in bulk, often claiming "
        "your profile was shortlisted. Kept out of the share file on purpose.",
    ]
    sheets = [("Review", review), ("Campus-only", campus), ("Excluded pitches", pitches)]
    if placement:
        lines.append(f"Placement cell ({len(placement)}): your placement cell's own notices, kept out of the share "
                     "file because the tool was run with --no-placement.")
        sheets.append(("Placement cell", placement))
    _about(about, "PRIVATE — do not share this file", lines)
    for name, rows in sheets:
        _write_table(wb.create_sheet(name), rows)
    wb.active = 1
    wb.save(path)


# --------------------------------------------------------------------------- reading back (merge)
def read_opportunities(path: str) -> List[Dict]:
    wb = load_workbook(path, read_only=True, data_only=False)
    if "Opportunities" not in wb.sheetnames:
        wb.close()
        raise ValueError(f"{os.path.basename(path)} has no 'Opportunities' sheet")
    college = ""
    if "About" in wb.sheetnames:
        for (value,) in wb["About"].iter_rows(min_col=1, max_col=1, values_only=True):
            if isinstance(value, str) and value.startswith("College: "):
                college = value[len("College: "):].strip()
                college = "" if college == "(not given)" else college
    rows = []
    sheet = wb["Opportunities"].iter_rows(values_only=True)
    header = [str(h or "").strip() for h in next(sheet, [])]
    for values in sheet:
        row = dict(zip(header, values))
        if not any(v not in (None, "") for v in row.values()):
            continue
        row["Shared by"] = row.get("Shared by") or college or os.path.splitext(os.path.basename(path))[0]
        for key in ("Deadline", "First seen", "Last update"):
            if isinstance(row.get(key), str):
                try:
                    row[key] = datetime.fromisoformat(row[key])
                except ValueError:
                    row[key] = None
        if isinstance(row.get("Deadline"), datetime):
            row["Deadline"] = row["Deadline"].date()
        rows.append(row)
    wb.close()
    return rows


def write_master(path: str, rows: List[Dict], meta: Dict):
    wb = _new_workbook()
    about = wb.active
    about.title = "About"
    _about(about, "Opportunities — combined from all colleges", [
        f"{meta['files']} files · {meta['rows_in']} rows in · {len(rows)} unique opportunities after removing duplicates "
        f"· made {meta['made']}",
        "Shared by lists every college whose students found the same opportunity; Times shared counts them.",
        "Duplicates are matched by email Message-ID, or by the same title within 60 days.",
        "Status and Days left update by themselves against today's date.",
    ])
    _write_table(wb.create_sheet("Opportunities"), rows)
    wb.active = 1
    wb.save(path)


def write_all_emails(path: str, mails) -> None:
    """Plain export of every email (for your own use - never share this)."""
    wb = Workbook(write_only=True)
    ws = wb.create_sheet("Messages")
    ws.append(["Date", "From", "To", "Cc", "Subject", "Message-ID", "Attachments", "Labels", "Body"])
    for m in mails:
        sender = f"{m.sender_name} <{m.sender}>" if m.sender_name else m.sender
        ws.append([m.date, _clean(sender), _clean(", ".join(m.to)), _clean(", ".join(m.cc)), _clean(m.subject),
                   _clean(m.message_id), _clean("; ".join(m.attachments)), _clean(", ".join(m.labels)),
                   _clean(m.body)])
    wb.save(path)


def same_title_key(row: Dict) -> str:
    return row.get("Thread key") or thread_key(str(row.get("Title") or ""))
