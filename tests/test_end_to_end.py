"""Run the real command line on the made-up sample mailbox: Takeout zip, mbox, Thunderbird folder, merge."""
import contextlib
import glob
import io
import os
import re
import shutil
import sys
import tempfile
import unittest
import zipfile

from openpyxl import load_workbook

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "examples"))

import make_sample_mailbox  # noqa: E402
from opportunity_extractor.cli import _clean_path, main  # noqa: E402
from opportunity_extractor.reader import read_mails  # noqa: E402

SECRETS = re.compile(r"riya|kapoor|23cs01042|%40|unsubscribe\?|hod-cse", re.I)


def run(*argv):
    with contextlib.redirect_stdout(io.StringIO()) as out:
        code = main(list(argv))
    return code, out.getvalue()


def sheet(path, name):
    ws = load_workbook(path)[name]
    header = [c.value for c in ws[1]]
    return [dict(zip(header, row)) for row in ws.iter_rows(min_row=2, values_only=True)]


class EndToEnd(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.mbox = os.path.join(cls.tmp, "sample.mbox")
        make_sample_mailbox.write_mbox(cls.mbox)
        cls.zip = os.path.join(cls.tmp, "takeout-20261101T000000Z-001.zip")
        make_sample_mailbox.write_takeout_zip(cls.mbox, cls.zip)
        cls.out = os.path.join(cls.tmp, "out")
        code, cls.log = run("extract", cls.zip, "--since", "all", "--college", "Example College",
                            "--out-dir", cls.out)
        assert code == 0, cls.log
        cls.share = glob.glob(os.path.join(cls.out, "opportunities_example-college_*.xlsx"))[0]
        cls.private = glob.glob(os.path.join(cls.out, "DO_NOT_SHARE_review_example-college_*.xlsx"))[0]

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_share_file_has_the_opportunities(self):
        rows = {r["Title"]: r for r in sheet(self.share, "Opportunities")}
        expected = {
            "Summer Internship 2027 at Acme Robotics - Apply by 15 October 2026": "2026-10-15",
            "HackNova 2026 - National Student Hackathon | Rs 5 Lakh prize pool": "2026-10-20",
            "National Merit Scholarship 2026-27 for UG students - last date 31 October 2026": "2026-10-31",
            "Call for Papers - International Conference on Sustainable Energy (ICSE 2026)": "2026-10-20",
            "Applications open: Summer Research Fellowship Programme 2027": "2026-11-30",
            "Participants needed: paid online study on sleep and memory (Rs 500)": "2026-10-25",
            "Top internships for you, [you]": "2026-10-18",
            "Campus Recruitment Drive: Globex Analytics - Graduate Engineer Trainee (2027 batch)": "2026-10-12",
        }
        self.assertEqual(set(rows), set(expected))
        for title, deadline in expected.items():
            self.assertEqual(rows[title]["Deadline"].date().isoformat(), deadline, title)
        self.assertEqual(rows["Call for Papers - International Conference on Sustainable Energy (ICSE 2026)"]
                         ["Emails in thread"], 2)

    def test_share_file_hides_the_owner_and_personal_links(self):
        wb = load_workbook(self.share)
        for ws in wb.worksheets:
            for row in ws.iter_rows(values_only=True):
                for value in row:
                    if isinstance(value, str):
                        self.assertIsNone(SECRETS.search(value), value[:200])

    def test_status_is_a_live_formula(self):
        ws = load_workbook(self.share)["Opportunities"]
        header = [c.value for c in ws[1]]
        status = ws.cell(row=2, column=header.index("Status") + 1).value
        self.assertTrue(str(status).startswith("=IF(ISNUMBER("), status)

    def test_private_file_holds_campus_items_and_pitches(self):
        campus = [r["Title"] for r in sheet(self.private, "Campus-only")]
        pitches = [r["Title"] for r in sheet(self.private, "Excluded pitches")]
        self.assertEqual(campus, ["Coding Club Inductions 2026 - form closes 5 October"])
        self.assertEqual(len(pitches), 1)

    def test_spam_trash_sent_personal_and_duplicates_never_appear(self):
        everything = " ".join(str(v) for path in (self.share, self.private)
                              for ws in load_workbook(path).worksheets
                              for row in ws.iter_rows(values_only=True) for v in row if v)
        for absent in ("PAID INTERNSHIP!!!", "Hackathon invite", "Application for Summer Internship 2027",
                       "can you check my resume", "mess menu", "Lab 4"):
            self.assertNotIn(absent, everything)
        titles = [r["Title"] for r in sheet(self.share, "Opportunities")]
        self.assertEqual(len(titles), len(set(titles)))

    def test_mbox_and_zip_read_the_same(self):
        self.assertEqual(len(read_mails(self.mbox)), len(read_mails(self.zip)))
        self.assertEqual(len(read_mails(self.zip)), 19)  # 22 written - spam - trash - one duplicate

    def test_thunderbird_folder(self):
        profile = os.path.join(self.tmp, "ImapMail", "imap.example.edu")
        os.makedirs(profile)
        shutil.copy(self.mbox, os.path.join(profile, "INBOX"))  # Thunderbird keeps folders without extension
        with open(os.path.join(profile, "INBOX.msf"), "w") as fh:
            fh.write("// <!-- <mdb:mork:z v=\"1.4\"/> -->")
        self.assertEqual(len(read_mails(os.path.join(self.tmp, "ImapMail"))), 19)

    def test_thunderbird_deleted_messages_are_skipped(self):
        path = os.path.join(self.tmp, "deleted.mbox")
        with open(self.mbox, "rb") as src, open(path, "wb") as dst:
            data = src.read()
            dst.write(data.replace(b"\nX-Gmail-Labels: Inbox,Category Updates\n",
                                   b"\nX-Gmail-Labels: Inbox,Category Updates\nX-Mozilla-Status: 0009\n"))
        self.assertLess(len(read_mails(path)), 19)

    def test_since_filter(self):
        self.assertLess(len(read_mails(self.mbox, since=__import__("datetime").datetime(2026, 10, 1))), 19)

    def test_merge_two_colleges(self):
        other_dir = os.path.join(self.tmp, "other")
        code, _ = run("extract", self.mbox, "--since", "all", "--college", "Second College", "--out-dir", other_dir)
        self.assertEqual(code, 0)
        submissions = os.path.join(self.tmp, "submissions")
        os.makedirs(submissions)
        shutil.copy(self.share, submissions)
        for f in glob.glob(os.path.join(other_dir, "*.xlsx")):  # the private file must be skipped
            shutil.copy(f, submissions)
        master = os.path.join(self.tmp, "master.xlsx")
        code, log = run("merge", submissions, "-o", master)
        self.assertEqual(code, 0)
        self.assertIn("2 files", log)
        rows = sheet(master, "Opportunities")
        self.assertEqual(len(rows), 8)
        for row in rows:
            self.assertEqual(row["Times shared"], 2)
            self.assertEqual(row["Shared by"], "Example College, Second College")

    def test_no_placement_keeps_placement_cell_notices_private(self):
        out = os.path.join(self.tmp, "no_placement")
        code, _ = run("extract", self.mbox, "--since", "all", "--college", "Example College", "--out-dir", out,
                      "--no-placement")
        self.assertEqual(code, 0)
        share = sheet(glob.glob(os.path.join(out, "opportunities_*.xlsx"))[0], "Opportunities")
        held = sheet(glob.glob(os.path.join(out, "DO_NOT_SHARE_*.xlsx"))[0], "Placement cell")
        self.assertEqual(len(share), 6)
        self.assertEqual({r["Scope"] for r in held}, {"Placement cell"})
        self.assertEqual(len(held), 2)

    def test_dragged_paths_are_cleaned(self):
        if os.name == "nt":
            self.assertEqual(_clean_path('"C:\\Users\\me\\takeout (1).zip"'), "C:\\Users\\me\\takeout (1).zip")
            self.assertEqual(_clean_path("& 'C:\\Users\\me\\takeout.zip'"), "C:\\Users\\me\\takeout.zip")
        else:
            self.assertEqual(_clean_path("/Users/me/My\\ Downloads/takeout\\ \\(1\\).zip "),
                             "/Users/me/My Downloads/takeout (1).zip")
            self.assertEqual(_clean_path("'/home/me/takeout.zip'"), "/home/me/takeout.zip")
            self.assertEqual(_clean_path("file:///home/me/My%20Mail.mbox"), "/home/me/My Mail.mbox")


if __name__ == "__main__":
    unittest.main()
