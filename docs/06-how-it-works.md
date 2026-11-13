# 6 · How it works, how to tune it, and how good it is

The pipeline is short and deterministic: no AI service and no network. Every decision can be traced to a rule in [`rules.py`](../opportunity_extractor/rules.py), and the *Why flagged* column shows which rules fired.

```
read (reader.py)  →  privacy filters  →  threads  →  score + scope + pitch check (classify.py)  →  deadline (dates.py)  →  Excel (workbook.py)
```

## 1. Reading (`reader.py`)

- **Formats:**
  - Takeout `.zip`, read in place
  - `.mbox` / `.mbx`
  - `.eml`
  - Thunderbird folder files without an extension, detected by their first bytes `From `
  - maildir `cur/` and `new/`
  - Apple Mail `.mbox` folders
  - `.xlsx` / `.csv` exports with Date/From/To/Subject/Body columns
- **Streaming.** The mbox is split on `From ` lines, and the mboxrd `>From` escapes are undone. Messages outside the date range, or labelled Spam/Trash/Drafts/Chat in `X-Gmail-Labels`, are rejected from their **headers alone**, so their bodies are never decoded. This made a 9,226-message mailbox take 3.5 s instead of 18 s. Thunderbird messages marked deleted (`X-Mozilla-Status` flag `0x0008`) are skipped too.
- **Body text.** The plain-text part is used when it is at least 200 characters. Otherwise the HTML part is converted to text, keeping link targets as ` (url)`. Legal disclaimers are trimmed, and the body is capped at 30,000 characters. Attachments are listed by name and never opened.
- **Duplicates.** Takeout repeats a message once per label, so messages are de-duplicated by Message-ID, or by date + sender + subject when the ID is missing.
- **Owner detection.** The most common `Delivered-To` address identifies the owner. If that header is missing, the tool uses the address that both sends and receives most, then the most common recipient. The display name comes from how others address the owner and how the owner signs sent mail.

## 2. Privacy filters (before any scoring)

| Dropped | How it's recognised |
|---|---|
| Mail you sent | The sender is you, or the message has the `Sent` label |
| Personal mail | `To` is exactly you, there is no `Cc`, there are no bulk headers (`List-Unsubscribe`, `List-Id`, `Precedence: bulk`, Gmail Promotions/Updates/Forums/Social), and the sender isn't automated (`noreply`, `notifications`, `hello`, `team`, `admissions`…). Use `--keep-direct` to include it. |
| Spam, trash, drafts, chats | Gmail labels |

The share file then goes through the redactor. It replaces your address (including URL-encoded `%40` copies), a roll-number-like local part (5+ characters with a digit), your full name and your first name with `[you]`. A first name that is also an everyday word or a festival name (*Asha*, *Kiran*, *Durga*…) is only hidden after *Dear/Hi/Hello/Hey*. The redactor also deletes `To:`/`Cc:`/`Bcc:` lines of forwarded headers, and replaces unsubscribe, tracking and token-carrying links with `[personal link removed]`. Thread keys, sender names and attachment names are redacted too.

## 3. Threads

Emails are grouped by subject after removing `Re:`, `Fwd:`, `[External]`, `Reminder:`, `Urgent:` and similar prefixes. A gap of more than 60 days starts a new thread, so a yearly "Hackathon 2026" doesn't join "Hackathon 2027". The **first email's subject and body are scored**. The deadline uses **every email** in the thread.

## 4. Score

`score = top two subject rules + body evidence (capped at +6) + negatives + sender rules + placement bonus + bulk penalty`

If no subject rule matches, the best subject rule found in the first 700 characters of the body adds half its weight.

| Subject rule | Weight | Subject rule | Weight |
|---|---|---|---|
| internship, hiring, recruitment drive | +7 | scholarship, fellowship, hackathon, competition, call for…, paid study | +7 |
| job opening, applications open, award, ambassador | +6 | challenge, programme, higher studies, selection, startup support | +5 |
| participation call, opportunity | +4 | conference | +3 |
| workshop | +2 | | |

| Body evidence (max +6 in total) | Weight |
|---|---|
| stipend/salary, prizes, application link (forms.gle, Unstop, Devfolio, "register here"…) | +2 each |
| eligibility stated, deadline stated, selection process, who can apply | +1 each |

| Negative (subject) | Weight | Negative (subject) | Weight |
|---|---|---|---|
| results / shortlist / winners / interview schedule / offer letter | −9 | social notification | −10 |
| convocation, account/system mail | −9 | scholarship paperwork (disbursal, bank details, verification) | −8 |
| coursework (classes, assignments, exams, quizzes), hostel/mess, promotions | −7 | talks/info sessions, feedback/surveys | −6 |
| admin/greetings, events/campaigns | −5 | | |

| Sender rule | Weight |
|---|---|
| social networks | −12 |
| course systems (Google Classroom, Moodle, Canvas) | −10 |
| shopping and news media | −8 |
| your placement cell (`cdc`, `tpo`, `tnp`, `placement`, `career`…, or `placement_senders` in `rules.json`) | +3 |
| bulk mail | −1 |

Thresholds:

- **≥ 7** → *Opportunities* (share file)
- **4–6** → *Review* (private file)
- below 4 → ignored

## 5. Scope

| Scope | Rule |
|---|---|
| *Campus* → private *Campus-only* sheet | The type is a club induction or selection, **or** the sender is from your institution and the subject or body uses campus words (hall, hostel, club, society, gymkhana, inter-IIT, contingent, freshers…), **or** a student body or a student (roll-number address) announces something without outside links. Outward types (internship, job, scholarship, conference, higher studies, paid study, funding) and anything "national/inter-college/open to all" stay External. |
| *Placement cell* | Your institution's placement sender plus an internship or job type |
| *External* | Everything else |

## 6. Paid-programme pitches

A thread goes to *Excluded pitches* when its pitch score is ≥ 5 and its opportunity score is ≥ 2. Pitch signals:

- "profile shortlisted" without an application (+3)
- a programme or registration fee (+3)
- an enrolment or resume-score hook (+3)
- "placement assistance" or "job guarantee" (+2)
- "certified training & internship" (+2)
- "mandatory confirmation" (+2)
- limited-seats pressure (+1)
- a sender domain from `pitch_domains`

## 7. Deadlines (`dates.py`)

- **Formats recognised:**
  - `31st October 2026`
  - `Oct 31, 2026`
  - `31-Oct-2026`
  - `31.10.2026` (day first, unless impossible)
  - `today` / `tomorrow` after a deadline word
  - Hindi `15.09.2026 तक`
- **Clean-up before reading.** Gmail's `*bold*` markers and forwarded `Date:` header lines are removed first.
- **Keyword groups.** A date counts as a deadline when a keyword sits just before it, with no event word (felicitation, result, notification, held, finale…) in between. Keywords include *last date, deadline, apply by, registrations close, on or before, extended to* and *अंतिम तिथि*. Dates directly following each other under one heading (a table of batches or rounds) join that group, and the group's last date counts.
- **Within one email:**
  - an **extension** wins
  - otherwise the **earliest upcoming** group wins, because a newcomer must meet it ("register by 8 Oct, submit by 20 Oct" → 8 Oct)
  - side deadlines (fee waiver, early bird, accommodation, award nominations) are used only if nothing else is stated
- **Across a thread** the latest email-level deadline wins, so extensions and next-stage reminders move it forward.
- **Fallbacks:** a weak cue ("by 5 Nov") → the earliest such date. Then an event date, marked `[event date - no deadline stated]`.

## 8. Tuning with `rules.json`

```json
{
  "extra_opportunity_keywords": ["research internship", "SURGE", "summer undergraduate research"],
  "extra_ignore_keywords": ["mess committee", "lost and found"],
  "pitch_domains": ["spammy-internships.example"],
  "campus_keywords": ["Spring Fest", "Kshitij"],
  "placement_senders": ["tnp@mycollege.example.edu"],
  "share_placement_cell": true
}
```

| Key | Effect |
|---|---|
| `extra_opportunity_keywords` | A subject match scores +7 |
| `extra_ignore_keywords` | A subject match scores −10 |
| `pitch_domains` | Sender domains treated as paid-programme pitches |
| `campus_keywords` | Subject words that mark a mail from your own institution as campus-only |
| `placement_senders` | Exact addresses treated as your placement cell |
| `share_placement_cell` | Set to `false` to keep placement-cell rows out of the share file |

Pass the file with `--config rules.json`, or put `rules.json` in the tool folder for the guided mode. For deeper changes, edit the tables in `rules.py`. Every rule is a `(label, regex, weight)` triple.

**How to tune.** Run on your own mailbox and read the *Review* sheet and the rows you deleted. Add a keyword or a negative for each repeated mistake, then re-run. Keep a few labelled examples, and add them to `tests/` so that fixes stay fixed.

## 9. How it was measured

The test was one student's mailbox at one institute, with hand labels on every thread from 8 Sep to 18 Oct 2026: 383 threads, of which 61 were external opportunities, 40 campus-only, 6 pitches and 276 other. Rules were tuned on that set, then frozen and checked on two hold-out sets.

| | Result |
|---|---|
| External opportunities found (tuning set) | 48/61 on the share sheet, 54/61 on some sheet |
| Share sheet purity (tuning set) | 57 rows: 48 external, 6 campus-only, 3 borderline non-opportunities |
| Hold-out, same mailbox, 12 days later | 5/6 on the share sheet, 1 on Review, 0 false alarms |
| Hold-out, a second student's unique mail | 5/5 on the share sheet, 0 false alarms |
| Deadlines on the sheets (71 hand-checked) | 60 exact, 4 within 2 days, 2 different, 5 not stated in the email |

Most misses were one university's drip-marketing series ("You're almost there", "Story of the Day") and government campaigns phrased as directives. Most borderline hits were talks *about* opportunities.

## 10. Limitations and ideas

- Keyword rules miss opportunities described only in attachments or images. Extracting PDF text would be the next step.
- Vocabulary is tuned on English and some Hindi mail from Indian colleges. Other languages need keywords.
- Duplicate detection across colleges relies on Message-IDs, which match only when the same email was received, or on identical titles. Re-typed announcements with different titles stay separate.
- A natural upgrade: once the E-Cell has a few thousand merged and checked rows, train a small local classifier on them, keeping everything offline.
