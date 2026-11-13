"""Command line: extract (students), merge (E-Cell), convert (optional full export)."""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta
from urllib.parse import unquote

from . import __version__, rules
from .classify import CAMPUS, OPPORTUNITIES, PITCHES, REVIEW, classify
from .reader import detect_owner, read_mails
from .workbook import result_row, write_all_emails, write_review, write_share

DEFAULT_DAYS = 180


def _date(value: str, end: bool = False):
    if value is None or value.lower() == "all":
        return None
    try:
        d = datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        raise SystemExit(f"Dates must look like 2026-07-01 (got {value!r}).")
    return d + timedelta(days=1) - timedelta(seconds=1) if end else d


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40]


def _say(msg: str):
    print(msg, flush=True)


def _clean_path(raw: str) -> str:
    """A path typed or dragged into a terminal: strip quotes, macOS backslash-escapes and file:// prefixes."""
    p = raw.strip().strip('"').strip("'").strip()
    if p.startswith("& "):  # PowerShell prefixes dragged paths with "& "
        p = p[2:].strip().strip("'").strip('"')
    if p.lower().startswith("file://"):
        p = unquote(p[7:])
    if os.name != "nt":
        p = re.sub(r"\\(.)", r"\1", p)
    return os.path.expanduser(p)


def _open_folder(path: str):
    try:
        if sys.platform.startswith("win"):
            os.startfile(path)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.run(["open", path], check=False)
        else:
            subprocess.run(["xdg-open", path], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass


def cmd_guided() -> int:
    """Question-and-answer mode, used when the tool is started without arguments (the launcher scripts)."""
    _say("=" * 70)
    _say(" Opportunity Mail Extractor " + __version__)
    _say(" Runs only on this computer. Nothing is uploaded; no password is asked.")
    _say("=" * 70)
    while True:
        raw = input("\n1) Drag your Google Takeout .zip (or an .mbox file, or a folder of them)\n"
                    "   into this window, then press Enter:\n> ")
        path = _clean_path(raw)
        if path and os.path.exists(path):
            break
        _say(f"   Could not find {path!r}. Try again, or type the full path." if path else "   Nothing entered.")
    college = input("\n2) Your college name (the E-Cell sees it when files are merged): ").strip()
    while True:
        since = input(f"\n3) Start date as YYYY-MM-DD, or 'all', or just press Enter for the last {DEFAULT_DAYS} days: ")
        since = since.strip() or None
        if since is None or since.lower() == "all" or re.fullmatch(r"\d{4}-\d{2}-\d{2}", since):
            break
        _say("   Please type a date like 2026-07-01, or 'all'.")
    out_dir = os.path.join(os.getcwd(), "output")
    config = "rules.json" if os.path.exists("rules.json") else None  # extra keywords shipped by the organisers
    _say("")
    args = argparse.Namespace(input=path, since=since, until=None, college=college, out_dir=out_dir, me=None,
                              name=None, keep_direct=False, no_placement=False, config=config, ask_name=True)
    code = cmd_extract(args)
    if code == 0:
        _open_folder(out_dir)
    return code


def cmd_extract(args) -> int:
    since = _date(args.since) if args.since else datetime.now() - timedelta(days=DEFAULT_DAYS)
    until = _date(args.until, end=True) if args.until else None
    cfg = rules.load_config(args.config) if args.config else {}
    start = time.time()
    shown = os.path.basename(args.input.rstrip("/").rstrip("\\"))
    span = "all dates" if since is None else "from " + since.strftime("%d %b %Y")
    span += "" if until is None else " to " + until.strftime("%d %b %Y")
    _say(f"Reading {shown} ({span}) ...")
    mails = read_mails(args.input, since=since, until=until,
                       progress=lambda n: _say(f"  scanned {n:,} emails ..."))
    if not mails:
        _say("No emails found in that date range. Try --since all, or check the file you chose.")
        return 1
    owner, name = detect_owner(mails)
    if args.me:
        owner, name = args.me.strip().lower(), ""
    name = args.name or name
    if not name and getattr(args, "ask_name", False):
        name = input("  Your name was not found in the emails. Type it as emails show it, so it can be hidden\n"
                     "  (or just press Enter to skip): ").strip()
    who = (owner or "unknown") + (f" ({name})" if name else "")
    _say(f"  {len(mails):,} emails in range. Mailbox owner: {who}.\n"
         "  Used only to hide your details and leave out personal mail; it is not written to the share file.")

    results = classify(mails, owner, name, keep_direct=args.keep_direct,
                       placement_senders=cfg.get("placement_senders", []))
    college = args.college or ""
    buckets = {b: [result_row(r, college) for r in results if r.bucket == b]
               for b in (OPPORTUNITIES, REVIEW, CAMPUS, PITCHES)}

    tag = _slug(college) or _slug(owner.split("@")[-1]) or "mailbox"
    stamp = datetime.now().strftime("%Y-%m-%d")
    out_dir = args.out_dir or os.getcwd()
    os.makedirs(out_dir, exist_ok=True)
    share = os.path.join(out_dir, f"opportunities_{tag}_{stamp}.xlsx")
    review = os.path.join(out_dir, f"DO_NOT_SHARE_review_{tag}_{stamp}.xlsx")
    meta = {"college": college, "since": since.strftime("%d %b %Y") if since else "the beginning",
            "until": until.strftime("%d %b %Y") if until else "today", "made": datetime.now().strftime("%d %b %Y")}
    shared, held = buckets[OPPORTUNITIES], []
    if getattr(args, "no_placement", False) or cfg.get("share_placement_cell") is False:
        held = [r for r in shared if r["Scope"] == "Placement cell"]
        shared = [r for r in shared if r["Scope"] != "Placement cell"]
    write_share(share, shared, meta)
    write_review(review, buckets[REVIEW], buckets[CAMPUS], buckets[PITCHES], meta, placement=held)

    _say(f"\nDone in {time.time() - start:.0f}s.")
    _say(f"  {len(shared):4d} opportunities      -> {share}")
    _say(f"  {len(buckets[REVIEW]):4d} to review           -> {review}  (sheet 'Review')")
    _say(f"  {len(buckets[CAMPUS]):4d} campus-only          -> same private file (sheet 'Campus-only')")
    _say(f"  {len(buckets[PITCHES]):4d} paid-programme pitches -> same private file (sheet 'Excluded pitches')")
    if held:
        _say(f"  {len(held):4d} placement-cell notices -> same private file (sheet 'Placement cell')")
    _say("\nNext: open the opportunities file, delete any row you don't want to share, and send ONLY that file.")
    return 0


def cmd_merge(args) -> int:
    from .merge import merge
    out = args.output or f"opportunities_ALL_{datetime.now():%Y-%m-%d}.xlsx"
    info = merge(args.inputs, out)
    _say(f"Merged {info['files']} files: {info['rows_in']} rows -> {info['unique']} unique opportunities -> {out}")
    for s in info["skipped"]:
        _say(f"  skipped {s}")
    return 0


def cmd_convert(args) -> int:
    since = _date(args.since) if args.since else None
    until = _date(args.until, end=True) if args.until else None
    mails = read_mails(args.input, since=since, until=until, progress=lambda n: _say(f"  scanned {n:,} emails ..."))
    out = args.output or "all_emails_PRIVATE.xlsx"
    write_all_emails(out, mails)
    _say(f"Wrote {len(mails):,} emails to {out}. This file contains everything - keep it private.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m opportunity_extractor",
                                description="Find opportunity emails in your own mailbox export. Runs offline.")
    p.add_argument("--version", action="version", version=__version__)
    sub = p.add_subparsers(dest="command", required=True)

    e = sub.add_parser("extract", help="find opportunities in a Takeout .zip, .mbox file, folder or spreadsheet")
    e.add_argument("input", help="Google Takeout .zip, an .mbox file, a folder of them, or an .xlsx/.csv export")
    e.add_argument("--since", help=f"first date to include, YYYY-MM-DD, or 'all' (default: last {DEFAULT_DAYS} days)")
    e.add_argument("--until", help="last date to include, YYYY-MM-DD (default: today)")
    e.add_argument("--college", help="your college name, shown to whoever merges the files")
    e.add_argument("--out-dir", help="folder for the two output files (default: current folder)")
    e.add_argument("--me", help="your email address, if the tool detects the wrong one")
    e.add_argument("--name", help="your name as emails show it, if the tool detects the wrong one (it is hidden)")
    e.add_argument("--keep-direct", action="store_true",
                   help="also look at emails written only to you (left out by default for privacy)")
    e.add_argument("--no-placement", action="store_true",
                   help="keep your college placement cell's own notices out of the share file")
    e.add_argument("--config", help="JSON file with extra keywords and senders (see examples/rules.example.json)")
    e.set_defaults(func=cmd_extract)

    m = sub.add_parser("merge", help="E-Cell: combine many students' share files into one master sheet")
    m.add_argument("inputs", nargs="+", help="share files or folders containing them")
    m.add_argument("-o", "--output", help="output file (default: opportunities_ALL_<date>.xlsx)")
    m.set_defaults(func=cmd_merge)

    c = sub.add_parser("convert", help="optional: dump every email to one spreadsheet, for your own use")
    c.add_argument("input")
    c.add_argument("-o", "--output")
    c.add_argument("--since")
    c.add_argument("--until")
    c.set_defaults(func=cmd_convert)
    return p


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    try:
        if not argv:
            return cmd_guided()
        args = build_parser().parse_args(argv)
        return args.func(args)
    except KeyboardInterrupt:
        _say("\nStopped.")
        return 130
    except EOFError:
        return 1
