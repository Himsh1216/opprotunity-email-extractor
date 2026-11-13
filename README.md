# Opportunity Mail Extractor

Find the **internships, jobs, hackathons, competitions, scholarships, fellowships, calls for papers and programmes** in your own mailbox, and share just those as one Excel file. You never hand over your password or your mailbox.

Built for E-Cells and student bodies that want to pool opportunities across colleges. Each student runs the tool on their own computer and sends back one spreadsheet. The organisers merge the spreadsheets into a single de-duplicated master sheet.

```
Your mailbox ──export──▶ Takeout .zip / .mbox ──this tool, offline──▶ opportunities_<college>_<date>.xlsx ──▶ E-Cell
   (Gmail, Outlook…)       (stays on your PC)      (reads, filters, hides you)       (the only file you send)        │
                                                                                                                  ▼
                                                                         merge ──▶ opportunities_ALL_<date>.xlsx
```

## Privacy, in plain terms

- **Your password is never asked for, stored or seen.** You export your own mail with Google's or Thunderbird's own tools.
- **Everything runs on your computer, offline.** The tool makes no network connections; Python's standard library and `openpyxl` are its only dependencies. The code is about 1,700 lines in [`opportunity_extractor/`](opportunity_extractor/) if you want to check.
- **Before anything is analysed, the tool drops:** spam, trash, drafts and chats; every email you sent; and personal emails addressed only to you (unless they come from an automated sender such as `noreply@`).
- **The share file hides you.** Your email address (including URL-encoded copies), roll-number-style ID, full name and first name become `[you]`. *To:* and *Cc:* lists of forwarded mails are deleted. Unsubscribe, tracking and token links become `[personal link removed]`.
- **You decide what leaves.** You get two files. `opportunities_….xlsx` is the only file meant for sharing, and you can delete any row before sending it. `DO_NOT_SHARE_review_….xlsx` stays with you.

## Quick start for students (about 15 minutes of your time)

| Step | What to do | Details |
|---|---|---|
| 1 | Export your mail. For Gmail: open [takeout.google.com](https://takeout.google.com) → **Deselect all** → tick **Mail** → **Next step** → **Create export**. Google emails you a download link, usually within hours. | [docs/01-export-gmail-takeout.md](docs/01-export-gmail-takeout.md). For Outlook, a college account with Takeout blocked, Apple Mail or Thunderbird, see [docs/02-export-other-mail.md](docs/02-export-other-mail.md) |
| 2 | Download this tool: green **Code** button → **Download ZIP**, then unzip it. | |
| 3 | Install Python 3.9 or newer, once. Get it from [python.org/downloads](https://www.python.org/downloads/). On Windows, tick **"Add python.exe to PATH"**. | [docs/03-run-the-tool.md](docs/03-run-the-tool.md) |
| 4 | Run it. **Windows:** double-click `run_windows.bat`. **Mac/Linux:** open Terminal, type `bash ` (with a space), drag `run_mac_linux.sh` in and press Enter. Then drag your Takeout `.zip` into the window and answer two questions. | The first run needs internet once, to install `openpyxl`. |
| 5 | Open `output/opportunities_<college>_<date>.xlsx`, delete any row you don't want to share, and send **only that file** to the organisers. | [docs/04-review-and-share.md](docs/04-review-and-share.md) |

You don't need to unzip the Takeout file; the tool reads the `.zip` directly. To see what the output looks like first, drag in the made-up sample mailbox [`examples/sample_mailbox.mbox`](examples/sample_mailbox.mbox).

## What you get

| File | Sheet | Contents |
|---|---|---|
| `opportunities_<college>_<date>.xlsx`, **to share** | About | Date range, counts, college, and what was hidden |
| | Opportunities | One row per opportunity. Email threads (replies, forwards, reminders, extensions) are merged into one row. |
| `DO_NOT_SHARE_review_<college>_<date>.xlsx`, **private** | Review | Likely opportunities the tool was unsure about. Copy real ones into the share file. |
| | Campus-only | Club inductions, fests, inter-college team selections: useful to you, not to other colleges |
| | Excluded pitches | Paid "training & internship" programmes sent in bulk, often claiming "your profile was shortlisted" |

Main columns in the Opportunities sheet:

- **Title, Type, Scope:** Scope is *External*, or *Placement cell* for your placement cell's own notices.
- **Deadline:** read from the email text. Extensions are followed.
- **Status and Days left:** live formulas against today's date: *Open*, *Closes today*, *Closed* or *No date found*.
- **Key links:** the application link is clickable.
- **Summary, From, First seen, Last update, Emails in thread, Deadline text** (the sentence the deadline came from), **Attachments**.
- **Confidence, Why flagged:** the rules that fired.
- **Shared by, Times shared**, plus the full text and the Message-IDs used for de-duplication.

## For the E-Cell: collect and merge

```bash
python -m opportunity_extractor merge submissions/ -o opportunities_ALL.xlsx
```

`merge` takes files or folders, and skips `DO_NOT_SHARE_*` files if someone sends one by mistake. Rows are treated as duplicates when they share an email Message-ID, which happens when the same bulk mail reached several students, or when they have the same normalised title within 60 days. For each duplicate the merge keeps the latest deadline and lists every college under **Shared by**, so **Times shared** shows how widely an opportunity circulated. You can find a full playbook in [docs/05-for-the-e-cell.md](docs/05-for-the-e-cell.md): announcement text, a Google Form for uploads, how often to run it, and a `rules.json` that adds keywords for everyone.

## How well it works (measured, not promised)

The tool was checked against hand-labelled data from real student mailboxes at one institute. The rules were tuned on the first set and then frozen before the hold-out sets.

| Set | Size | Result |
|---|---|---|
| Tuning set: one student, 8 Sep – 18 Oct 2026 | 542 emails → 383 threads; 61 external opportunities | **48 of 61 (79 %)** on the share sheet; **54 of 61 (89 %)** on some sheet. Of the 57 share-sheet rows, 48 were external opportunities, 6 were campus-only items, and 3 were borderline (e.g. a talk about scholarships). |
| Hold-out: same student, 18 – 30 Oct | 97 emails | 5 of 6 on the share sheet, 1 on Review; no false alarms; both paid pitches caught |
| Hold-out: another student's emails not in the first mailbox, 1 Sep – 30 Oct | 208 threads | 5 of 5 on the share sheet; no false alarms on the share or Review sheet |
| Deadlines on the sheets | 71 hand-checked | 60 exact; 4 within 2 days; 2 different (one extension arrived as a separate thread); 5 not stated in the email |

Speed: a 9,226-email Takeout `.zip` takes about 30 s for the whole mailbox and about 4 s for the default last 180 days.

Known gaps:

- It is keyword-based, so it misses opportunities written with no opportunity vocabulary, such as a bare "Please find attached" with a PDF.
- It reads email text, not attachments.
- Results from other institutes will differ. Mailing-list names and campus vocabulary vary, so start with the Review sheet and tune `rules.json`.

[docs/06-how-it-works.md](docs/06-how-it-works.md) explains every rule and threshold.

## FAQ

**Takeout says Mail isn't available, or Takeout is blocked for my college account.** Your admin has turned it off; Google lets Workspace admins do that. Use Thunderbird instead: [docs/02-export-other-mail.md](docs/02-export-other-mail.md).

**My mailbox is huge.** That's fine. The tool streams the file and never loads it all into memory. In Takeout, choose a 50 GB file size so you get a single `.zip`. If you already have several parts, drag in the folder that contains them.

**It detected the wrong email address or name.** Use the command line: `python -m opportunity_extractor extract takeout.zip --me you@college.edu --name "Your Name"`.

**I want older emails too.** In the guided mode, answer `all` or give a start date such as `2026-01-01`, or pass `--since all` on the command line.

**Windows says "Windows protected your PC" or "publisher could not be verified".** Click **More info → Run anyway**. The launcher is a 40-line text file you can open in Notepad first.

## Command line

```bash
python -m opportunity_extractor                    # guided mode (what the launchers run)
python -m opportunity_extractor extract INPUT [--since YYYY-MM-DD|all] [--until YYYY-MM-DD]
        [--college NAME] [--out-dir DIR] [--me EMAIL] [--name NAME]
        [--keep-direct] [--no-placement] [--config rules.json]
python -m opportunity_extractor merge FILES_OR_FOLDERS... [-o OUTPUT.xlsx]
python -m opportunity_extractor convert INPUT [-o all_emails_PRIVATE.xlsx]   # every email to one sheet, for you only
```

`INPUT` can be any of these:

- a Google Takeout `.zip`
- an `.mbox` file
- an `.eml` file
- a folder containing any of the above
- a Thunderbird profile or Apple Mail export folder (also maildir)
- an `.xlsx` or `.csv` with Date/From/To/Subject/Body columns

Run the tests with `python -m unittest discover -s tests -t .`; they use only made-up mail.

## Repository layout

```
opportunity_extractor/   reader.py (mbox/zip/eml/Thunderbird/xlsx) · classify.py (threads, scoring, scope, redaction)
                         rules.py (all keywords & weights) · dates.py (deadlines) · workbook.py (Excel) · merge.py · cli.py
run_windows.bat, run_mac_linux.sh   one-click launchers (create a private .venv, install openpyxl, start guided mode)
examples/                sample_mailbox.mbox (made-up), make_sample_mailbox.py, rules.example.json
docs/                    step-by-step guides 01–06
tests/                   unittest suite on synthetic mail
```

## License

MIT; see [LICENSE](LICENSE). Contributions are welcome: new keywords, fixes for mis-sorted mail and support for other export formats. Please never commit real emails; use `examples/make_sample_mailbox.py` to build test mail.
