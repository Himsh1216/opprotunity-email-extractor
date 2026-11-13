# 5 · For the E-Cell: run a collection drive

## 0. Set up once

- **Host the repository** on your organisation's GitHub, using a fork or a copy of this one, so students download from a link you control.
- **Optional `rules.json`.** Copy `examples/rules.example.json` to `rules.json` in the repository root. The guided mode loads it automatically for every student. Use it to:
  - add keywords for opportunity types you care about
  - add paid-programme domains that keep reaching students
  - set `"share_placement_cell": false` if you would rather students never share placement-cell notices
- **Decide the window.** For example, *emails since 1 July 2026*. Then all submissions cover the same period.

## 1. Announce

Use a short message and link the README. For example:

> **Share opportunities, not your inbox.** E-Cell is pooling internships, hackathons, scholarships and competitions that land in students' mailboxes across colleges, and everyone gets the combined sheet.
> 1) Export your mail with Google Takeout (5 min). 2) Run our tool on your own laptop; it works offline and never asks for a password. 3) Check the Excel file it makes and upload only that file here: <form link>.
> Guide: <repo link>. Deadline: <date>.

## 2. Collect

**Google Form** with a *File upload* question works well:

- **Settings:** allow only *Spreadsheet* files, maximum 1 file, 10 MB.
- **Respondents must sign in to Google** to upload. Files land in your Drive under the form's *File responses* folder.
- **Add a required consent checkbox:** *"I reviewed this file and agree that E-Cell <name> may redistribute its rows to students of other colleges."*
- **Add a *College* field** as a fallback. The file's *About* sheet already carries the college name.

Email or a shared Drive folder also works. **Never ask for** the `DO_NOT_SHARE_…` file, a Takeout `.zip`, or login details.

## 3. Merge

```bash
python -m opportunity_extractor merge "File responses/" -o opportunities_ALL_2026-11.xlsx
# prints, for example: Merged 37 files: 2,214 rows -> 1,106 unique opportunities -> opportunities_ALL_2026-11.xlsx
```

How the merge behaves:

- **Duplicates** are rows that share an email Message-ID, meaning the same mail reached several students, or rows with the same normalised title within 60 days.
- **For each duplicate the merge keeps** the most recently updated row, the **latest deadline**, all colleges in *Shared by*, the count in *Times shared*, and the earliest *First seen* and latest *Last update*.
- **Files skipped automatically:** Excel lock files (`~$…`), anything named `DO_NOT_SHARE…`, and files without an *Opportunities* sheet. Skipped files are listed.
- **Shared by** is read from the *College:* line of each file's *About* sheet. If that line is missing, the file name is used.

## 4. Publish

- Filter **Status = Open**, or sort by **Days left**, so closed items drop out.
- Before publishing, hide or delete the technical columns: **Full text, Message-IDs, Thread key, Confidence, Why flagged**.
- Spot-check about 10 random rows per college. Delete pitches, campus-only items and anything that identifies a student.
- Share the sheet view-only, for example as a Google Sheet. *Times shared* is a useful signal: an opportunity that reached 15 colleges is probably a national one.

## 5. Your commitments to students

- Use submissions only to build and publish the opportunities sheet.
- Delete the raw submissions after merging, and say when you will do so.
- Credit colleges in *Shared by*, never individual students.
- Fix or remove a row promptly if anyone reports it.

## Cadence and effort

Run a drive **once a month or at the start of each semester**. A student needs about 15 minutes, plus waiting for Takeout. Merging 50 files takes seconds. Expect more value from breadth (many colleges, each with a few students) than from depth (many students at one college), because students at one college receive mostly the same mail.

Next: [06-how-it-works.md](06-how-it-works.md)
