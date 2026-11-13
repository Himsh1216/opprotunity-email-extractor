"""Deadline extraction on wording seen in real college mail (names and links changed)."""
import unittest
from datetime import date, datetime

from opportunity_extractor.dates import deadline, find_dates

REF = datetime(2026, 9, 30, 10, 0)

CASES = [
    # (email text, expected deadline or None, expected kind)
    ("Deadline: 13th September 2026", "2026-09-13", "deadline"),
    ("*Deadline: 13**th** September 2026*", "2026-09-13", "deadline"),  # Gmail's *bold* markers
    ("The last date of receipt of application is extended upto 30-Sep-2026 as per the corrigendum.",
     "2026-09-30", "deadline"),
    ("Fill the form by 31.10.2026", "2026-10-31", "deadline"),
    ("Applications close on Oct 31, 2026. Results: 30 November 2026", "2026-10-31", "deadline"),
    ("Registration for the Innovation Challenge 2026-27 closes 25 September 2026, 11:59 PM IST.",
     "2026-09-25", "deadline"),
    ("Abstract submission deadline: 25 November 2026 - Notification of acceptance: 30 November 2026",
     "2026-11-25", "deadline"),
    ("The event will be held on 15th November. Please register by 5 Nov.", "2026-11-05", "deadline"),
    ("Apply by 20 Oct 2026 and join us on 5 Nov 2026", "2026-10-20", "deadline"),
    # an event date after the deadline must not win
    ("- Last date to submit: 20 October 2026\n- Registration deadline: 8 October 2026\n"
     "Winners will be felicitated at a grand event on *24\nOctober 2026*.", "2026-10-08", "deadline"),
    ("Registration Deadline: 20 October 2026 Online Qualification: 20-28 October 2026 "
     "Grand Finale: 4-6 December 2026", "2026-10-20", "deadline"),
    # several stages: the first one a newcomer must meet; side deadlines do not count
    ("Last Date for Submission of Full Papers\n10 October 2026\n\nNotification of Acceptance\n15 October 2026\n\n"
     "Last Date for Award Nominations\n25 October 2026\n\nLast Date for Registration\n25 October 2026",
     "2026-10-10", "deadline"),
    ("The last date to apply: October 25, 2026 (Sunday, 11 PM) Deadline for Fee waiver: October 11, 2026",
     "2026-10-25", "deadline"),
    # a table under one heading: the last batch is the last chance
    ("*Registration End Date*\nBatch - 1 1 September 2026 22 October 2026\n"
     "Batch - 2 1 September 2026 18 December 2026", "2026-12-18", "deadline"),
    ("Deadline: 20 Oct 2026 (Round 1), 15 Nov 2026 (Round 2)", "2026-11-15", "deadline"),
    ("The last date (15 September 2026) has been extended to 5 October 2026.", "2026-10-05", "deadline"),
    # relative dates
    ("Hello Everyone,\nThe deadline is Today 23:59. No further extension.", "2026-09-30", "deadline"),
    ("Registrations close tomorrow!", "2026-10-01", "deadline"),
    ("Last Day to Complete Your Application | Online Degree\nHi", "2026-09-30", "deadline"),
    ("Classes are cancelled due to heavy rain today.", None, ""),
    ("Fwd: Hackathon\n---------- Forwarded message ---------\nThe deadline is today, so hurry.", None, ""),
    # a forwarded header is not a date of the opportunity
    ("Fwd: Training\n---------- Forwarded message ---------\nFrom: X <x@example.com>\n"
     "Date: Mon, Sep 28, 2026 at 12:42 PM\nSubject: Training", None, ""),
    # Hindi circulars: "15.09.2026 तक" means "by 15.09.2026"
    ("रचनाएँ *15.09.2026 तक* Google Form के माध्यम से भेजें", "2026-09-15", "deadline"),
    # only an event date
    ("Workshop on 7th November 2026 (Saturday) from 10:00 AM", "2026-11-07", "event date"),
    ("Applications for September 2026 intake are open.", None, ""),
]


class DeadlineTests(unittest.TestCase):
    def test_cases(self):
        for text, want, kind in CASES:
            with self.subTest(text=text[:60]):
                got, got_kind, _ = deadline([(text, REF)])
                self.assertEqual(got.isoformat() if got else None, want)
                self.assertEqual(got_kind, kind)

    def test_extension_in_a_later_email_wins(self):
        thread = [("Last date: 15 October 2026", datetime(2026, 10, 1)),
                  ("Deadline extended to 25 October 2026", datetime(2026, 10, 14))]
        self.assertEqual(deadline(thread)[0], date(2026, 10, 25))

    def test_reminder_for_the_next_stage_moves_the_deadline(self):
        thread = [("Register by 8 Oct 2026. Last date to submit: 20 October 2026", datetime(2026, 10, 1)),
                  ("Reminder: last date to submit is 20 October 2026", datetime(2026, 10, 12))]
        self.assertEqual(deadline(thread)[0], date(2026, 10, 20))

    def test_year_rolls_over(self):
        found = find_dates("Apply by 15 January", datetime(2026, 11, 20))
        self.assertEqual(found[0][2], date(2027, 1, 15))

    def test_month_and_year_alone_is_not_a_date(self):
        self.assertEqual(find_dates("the September 2026 intake", REF), [])

    def test_numeric_dates_are_day_first(self):
        self.assertEqual(find_dates("on 05/10/2026", REF)[0][2], date(2026, 10, 5))
        self.assertEqual(find_dates("on 10/25/2026", REF)[0][2], date(2026, 10, 25))  # impossible as dd/mm


if __name__ == "__main__":
    unittest.main()
