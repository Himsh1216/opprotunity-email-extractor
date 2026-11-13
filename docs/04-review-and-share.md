# 4 · Review and share

You now have two files in `output/`:

| File | Share? | What's inside |
|---|---|---|
| `opportunities_<college>_<date>.xlsx` | **Yes, this one only** | *About* sheet, plus the *Opportunities* sheet with one row per opportunity |
| `DO_NOT_SHARE_review_<college>_<date>.xlsx` | **No** | The *Review*, *Campus-only* and *Excluded pitches* sheets (plus *Placement cell* if you used `--no-placement`) |

## Five-minute check before sending

1. **Scroll the Titles.** Delete any row you don't want to share. Click the row number, then right-click → **Delete**.
2. **Look at the *Scope* column.**
   - *External* means outside opportunities: hackathons, scholarships, conferences, internships that are open to anyone.
   - *Placement cell* means your own placement cell's notices: campus drives, internal registration forms. These are often open only to your college, and some placement cells forbid forwarding them. Delete those rows if that applies.
3. **Search for yourself.** Press Ctrl+F (Cmd+F on Mac) and search for your phone number, any nickname and any personal email address. The tool already hides your college email address, roll-number ID and name as `[you]`, but it cannot know your phone number. It also cannot know other ways you are named in mail that someone else quoted.
4. **Check the *Review* sheet in the private file.** If a row there is a real opportunity, copy the **whole row** and paste it below the last row of the *Opportunities* sheet in the share file. Its Status formula keeps working.
5. **Save it as `.xlsx`, then send only the share file** the way your organisers asked: a Google Form upload, email or a shared folder. You may rename the file. The college name inside the *About* sheet is what the merge uses.

## What the share file does and doesn't contain

Every row comes from an email thread the tool judged to be an opportunity. A row has:

- the title
- the type
- the deadline and the sentence it came from
- up to three key links
- a short summary and the email text, with you hidden
- the sender's name and address, usually an organisation, office or club
- dates, the number of emails in the thread and attachment names (not the attachments themselves)
- why the tool flagged it, and the Message-IDs used to merge duplicates

These are never included:

- emails you sent
- emails written only to you by a person
- spam, trash, drafts and chats
- *To:* and *Cc:* recipient lists of forwarded mail
- unsubscribe and tracking links
- your address, ID and name, which become `[you]`

## Understanding the columns

| Column | Notes |
|---|---|
| **Deadline** | Taken from the email text. When a thread contains an extension, the later date is used. When an email lists stages ("register by 8 Oct, submit by 20 Oct"), the first stage a newcomer must meet is used. Side deadlines such as fee waivers or early-bird offers are ignored. If only an event date was found, *Deadline text* starts with `[event date - no deadline stated]`. |
| **Status / Days left** | Formulas: *Open*, *Closes today*, *Closed* or *No date found*. They update every time the file is opened. |
| **Confidence** | *High* means the score reached the main threshold. |
| **Why flagged** | The rules that fired, for example `hackathon, prizes, application link`. |
| **Shared by / Times shared** | Filled in during merging. Times shared is 1 in your own file. |

Always confirm details on the official page before applying. The tool reads emails, and emails can be out of date.

Next for organisers: [05-for-the-e-cell.md](05-for-the-e-cell.md)
