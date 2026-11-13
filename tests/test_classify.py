"""Scoring, scope, pitch detection, threading and redaction on hand-made emails."""
import unittest
from datetime import datetime

from opportunity_extractor import classify as C
from opportunity_extractor.reader import Mail

OWNER = "23cs01042@example.edu"


def mail(subject, body="", sender="news@events.example.org", to=("list@example.edu",), when=(2026, 9, 21),
         labels=("Inbox",), bulk=False, name="", mid=None):
    return Mail(date=datetime(*when, 10, 0), sender_name=name, sender=sender, to=list(to), cc=[],
                named_recipients=[], subject=subject, message_id=mid or f"<{abs(hash((subject, when)))}@x>",
                attachments=[], body=body, labels=list(labels), delivered_to=OWNER, bulk=bulk)


def bucket_of(*mails, owner=OWNER, name="Riya Kapoor"):
    results = C.classify(list(mails), owner, name)
    return results[0].bucket if results else "dropped"


class BucketTests(unittest.TestCase):
    def test_external_opportunities(self):
        cases = [
            mail("Summer Internship 2027 at Acme Robotics", "Stipend Rs 40,000. Apply: https://forms.gle/x"),
            mail("HackNova 2026 - National Hackathon", "Prizes worth Rs 5 lakh. Register at https://unstop.com/x"),
            mail("Call for Papers: ICSE 2026", "Full paper submission deadline: 10 October 2026"),
            mail("National Merit Scholarship 2026-27", "Eligibility: UG students. Last date: 31.10.2026"),
            mail("Applications open: Summer Research Fellowship 2027", "A fellowship of Rs 12,500 per month"),
        ]
        for m in cases:
            with self.subTest(m.subject):
                self.assertEqual(bucket_of(m), C.OPPORTUNITIES)

    def test_not_opportunities(self):
        cases = [
            mail("Results of Mid-Semester Examinations", sender="academic.office@example.edu"),
            mail("Revised mess menu for October", sender="hostel.office@example.edu"),
            mail("New assignment: Lab 4", sender="no-reply@classroom.google.com"),
            mail("Great Festival Sale: up to 80% off", sender="store-news@amazon.in", bulk=True),
            mail("Shortlisted candidates for the internship interview", sender="hr@acme.example.com"),
            mail("Talk on Higher Studies in Germany - 7 October", sender="career.cell@example.edu"),
        ]
        for m in cases:
            with self.subTest(m.subject):
                self.assertIn(bucket_of(m), (None, "dropped"))

    def test_club_induction_is_campus_only(self):
        m = mail("Coding Club Inductions 2026", "Fill the form by 5 October: https://forms.gle/y",
                 sender="codingclub.secy@example.edu")
        self.assertEqual(bucket_of(m), C.CAMPUS)

    def test_outside_scholarship_relayed_by_college_stays_external(self):
        m = mail("Fwd: National Merit Scholarship 2026-27", "Applications are invited from students across India.",
                 sender="dosa@example.edu")
        self.assertEqual(bucket_of(m), C.OPPORTUNITIES)

    def test_paid_programme_pitch_is_excluded(self):
        m = mail("Internship Enrollment: confirm your seat in the Certified Training & Internship Program",
                 "Your profile has been shortlisted. Programme fee: Rs 4,999. Limited seats! 100% placement "
                 "assistance. Mandatory confirmation required.", sender="admissions@skillboost.example.com", bulk=True)
        self.assertEqual(bucket_of(m), C.PITCHES)

    def test_personal_and_sent_mail_left_out(self):
        personal = mail("Internship referral - can you check my resume?", "Hi Riya",
                        sender="aman.verma@mail.example.com", to=(OWNER,))
        sent = mail("Application for Summer Internship 2027", sender=OWNER, to=("hr@acme.example.com",),
                    labels=("Sent",))
        self.assertEqual(C.classify([personal, sent], OWNER, "Riya Kapoor"), [])
        kept = C.classify([personal], OWNER, "Riya Kapoor", keep_direct=True)
        self.assertEqual(len(kept), 1)

    def test_automated_sender_to_you_alone_is_not_personal(self):
        m = mail("HackNova 2026 - National Hackathon", "Register at https://unstop.com/x",
                 sender="hello@hacknova.example.org", to=(OWNER,), bulk=True)
        self.assertEqual(bucket_of(m), C.OPPORTUNITIES)


class ThreadTests(unittest.TestCase):
    def test_replies_and_forwards_join_one_thread(self):
        a = mail("Call for Papers: ICSE 2026", "deadline 10 October 2026", when=(2026, 9, 1))
        b = mail("Re: Call for Papers: ICSE 2026", "deadline extended to 20 October 2026", when=(2026, 10, 8))
        c = mail("Fwd: [External] Call for Papers: ICSE 2026", "", when=(2026, 10, 9))
        threads = C.group_threads([a, b, c])
        self.assertEqual(len(threads), 1)
        result = C.classify([a, b, c], OWNER)[0]
        self.assertEqual(result.n_emails, 3)
        self.assertEqual(result.deadline.isoformat(), "2026-10-20")

    def test_same_subject_months_apart_is_a_new_thread(self):
        a = mail("Hackathon 2026", when=(2026, 1, 5))
        b = mail("Hackathon 2026", when=(2026, 9, 5))
        self.assertEqual(len(C.group_threads([a, b])), 2)

    def test_title_cleanup(self):
        self.assertEqual(C.clean_title("Re: Fwd: [External] Reminder: Hackathon 2026"), "Hackathon 2026")


class PrivacyTests(unittest.TestCase):
    def test_redaction(self):
        redact = C.make_redactor(OWNER, "Riya Kapoor")
        text = ("Hi Riya, RIYA KAPOOR (23CS01042) - link https://x.example.com/u?email=23cs01042%40example.edu "
                "and 23cs01042@example.edu")
        out = redact(text)
        for secret in ("riya", "kapoor", "23cs01042", "%40"):
            self.assertNotIn(secret, out.lower())

    def test_recipient_lines_and_personal_links_removed(self):
        redact = C.make_redactor(OWNER, "Riya Kapoor")
        text = ("From: Dean <dean@example.edu>\nTo: <hod-cse@example.edu>,\n <hod-ece@example.edu>\n"
                "Cc: registrar@example.edu\nSubject: x\nUnsubscribe https://m.example.org/unsubscribe?u=8f3a")
        out = redact(text)
        self.assertNotIn("hod-cse", out)
        self.assertNotIn("registrar", out)
        self.assertNotIn("8f3a", out)
        self.assertIn("dean@example.edu", out)

    def test_name_that_is_a_common_word_only_hidden_in_greetings(self):
        redact = C.make_redactor("x1@example.com", "Asha Verma")
        self.assertEqual(redact("Dear Asha, ASHA workers"), "Dear [you], ASHA workers")

    def test_key_links_skip_personal_links(self):
        links = C.key_links(["Register https://unstop.com/hack?utm_source=mail "
                             "unsubscribe https://m.example.org/unsubscribe?u=1 "
                             "https://portal.example.org/apply?email=23cs01042%40example.edu"], OWNER)
        self.assertEqual(links, ["https://unstop.com/hack?utm_source=mail"])


if __name__ == "__main__":
    unittest.main()
