"""Write a small, made-up Gmail-style mailbox for trying the tool and for the tests.

Every person, company and address in it is invented (example.edu / example.com / example.org).

    python examples/make_sample_mailbox.py                 # writes examples/sample_mailbox.mbox
    python examples/make_sample_mailbox.py out.mbox --zip  # also writes a Google-Takeout-style out.zip
"""
from __future__ import annotations

import argparse
import os
import zipfile
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from email.policy import default
from email.utils import format_datetime, parsedate_to_datetime

OWNER = "Riya Kapoor <23cs01042@example.edu>"
IST = timezone(timedelta(hours=5, minutes=30))

# (labels, from, to, cc, subject, body, extra headers); dates are filled in order below
MAILS = [
    ("Inbox,Category Updates", "Training & Placement Cell <placement@example.edu>", "ug-2023-batch@example.edu", "",
     "Summer Internship 2027 at Acme Robotics - Apply by 15 October 2026",
     "Dear Students,\n\nAcme Robotics is offering summer internships (May-July 2027) for B.Tech students of the "
     "2027 and 2028 batches.\n\nEligibility: CGPA 7.0 and above, all branches\nStipend: Rs 40,000 per month\n"
     "Location: Bengaluru (on site)\n\nApply here: https://forms.gle/AcmeRobotics2027\n"
     "Last date to apply: 15 October 2026\n\nRegards,\nTraining & Placement Cell", {}),

    ("Inbox,Category Promotions", "Team HackNova <hello@hacknova.example.org>", OWNER, "",
     "HackNova 2026 - National Student Hackathon | Rs 5 Lakh prize pool",
     "<html><body><p>Hi Riya,</p><p>HackNova 2026 is a 36-hour national hackathon open to students of all "
     "colleges in India. Teams of 2-4.</p><p><b>Prizes:</b> Rs 5,00,000 in total</p>"
     "<p>Registrations close on <b>20 October 2026</b>.</p>"
     "<p><a href=\"https://unstop.com/hackathons/hacknova-2026\">Register now</a></p>"
     "<p style=\"font-size:10px\"><a href=\"https://mailer.hacknova.example.org/unsubscribe?email=23cs01042%40example.edu\">"
     "Unsubscribe</a></p></body></html>",
     {"List-Unsubscribe": "<https://mailer.hacknova.example.org/unsubscribe?email=23cs01042%40example.edu>",
      "Content-Type": "text/html"}),

    ("Inbox,Important", "Office of Dean (Student Affairs) <dosa@example.edu>", "all-students@example.edu", "",
     "Fwd: National Merit Scholarship 2026-27 for UG students - last date 31 October 2026",
     "Dear Students,\nPlease see the scholarship notice below and apply if eligible.\n\n"
     "---------- Forwarded message ---------\nFrom: Scholarship Division <scholarships@education.example.org>\n"
     "Date: Mon, Sep 21, 2026 at 11:05 AM\nSubject: National Merit Scholarship 2026-27\n"
     "To: <registrar@example.edu>, <hod-cse@example.edu>,\n <hod-ece@example.edu>\n\n"
     "Applications are invited from meritorious undergraduate students across India for the National Merit "
     "Scholarship 2026-27. Amount: Rs 50,000 per year. Family income below Rs 8 lakh per year.\n"
     "Apply online at https://scholarships.education.example.org/apply\n"
     "Last date for online application: 31.10.2026", {}),

    ("Inbox", "ICSE 2026 Secretariat <conference@iconf.example.org>", "students@example.edu", "",
     "Call for Papers - International Conference on Sustainable Energy (ICSE 2026)",
     "Dear Researchers,\n\nWe invite original papers for ICSE 2026, to be held on 10-12 December 2026.\n\n"
     "Important dates\nFull paper submission deadline: 10 October 2026\nNotification of acceptance: 30 October 2026\n"
     "Submit via https://cmt.example.org/ICSE2026\n\nBest student paper award: Rs 25,000", {}),

    ("Inbox", "ICSE 2026 Secretariat <conference@iconf.example.org>", "students@example.edu", "",
     "Re: Call for Papers - International Conference on Sustainable Energy (ICSE 2026)",
     "Dear Researchers,\n\nOn popular request, the full paper submission deadline has been extended to "
     "20 October 2026.\n\nSubmit via https://cmt.example.org/ICSE2026", {}),

    ("Inbox", "Science Academies Fellowships <fellowships@academies.example.org>", "ug-2023-batch@example.edu", "",
     "Applications open: Summer Research Fellowship Programme 2027",
     "The Summer Research Fellowship Programme 2027 offers 8-week research projects with scientists across "
     "India. Students in the 2nd and 3rd year of B.Tech/B.Sc are eligible. A fellowship of Rs 12,500 per month "
     "is paid.\n\nApply on or before 30 November 2026 at https://academies.example.org/srfp/apply", {}),

    ("Inbox", "Coding Club Secretary <codingclub.secy@example.edu>", "all-ug@example.edu", "",
     "Coding Club Inductions 2026 - form closes 5 October",
     "Hey everyone!\n\nThe Coding Club is inducting first and second year students. Fill the form by "
     "5 October 2026: https://forms.gle/CodingClubInductions\nThe test will be held in LH-2 on 7 October.", {}),

    ("Inbox,Category Promotions", "Career Desk <admissions@skillboost.example.com>", OWNER, "",
     "Internship Enrollment: confirm your seat in the Certified Training & Internship Program",
     "Dear Riya,\n\nYour profile has been shortlisted for our Certified Training & Internship Program in "
     "Machine Learning. Programme fee: Rs 4,999 only. Limited seats left!\n100% placement assistance.\n"
     "Mandatory confirmation required within 24 hours: https://skillboost.example.com/confirm",
     {"List-Unsubscribe": "<mailto:unsubscribe@skillboost.example.com>"}),

    ("Inbox", "Prof. A. Rao (Classroom) <no-reply@classroom.google.com>", OWNER, "",
     "New assignment: Lab 4 - Data Structures", "Prof. A. Rao posted a new assignment. Due 9 October 2026.", {}),

    ("Inbox", "Hostel Office <hostel.office@example.edu>", "all-residents@example.edu", "",
     "Revised mess menu for October", "Dear residents, the revised mess menu is attached.", {}),

    ("Inbox,Category Promotions", "Shopping Store <store-news@amazon.in>", OWNER, "",
     "Great Festival Sale: up to 80% off on laptops", "Deals end 15 October. Shop now.",
     {"List-Unsubscribe": "<https://amazon.in/unsub>"}),

    ("Inbox,Category Social", "LinkedIn <notifications-noreply@linkedin.com>", OWNER, "",
     "Riya, you appeared in 12 searches this week", "See who is looking at your profile.", {}),

    ("Inbox", "Academic Office <academic.office@example.edu>", "ug-2023-batch@example.edu", "",
     "Results of Mid-Semester Examinations", "The mid-semester results are available on the portal.", {}),

    ("Inbox", "Aman Verma <aman.verma@mail.example.com>", OWNER, "",
     "Internship referral - can you check my resume?",
     "Hi Riya, could you look at my resume before I apply? Thanks, Aman", {}),

    ("Sent", OWNER, "HR Team <hr@acme.example.com>", "",
     "Application for Summer Internship 2027", "Dear HR team, please find my resume attached. Riya Kapoor", {}),

    ("Spam", "Lucky Jobs <win@jobs.example.net>", OWNER, "",
     "PAID INTERNSHIP!!! earn Rs 50,000 weekly", "Click here to claim.", {}),

    ("Trash", "Events <events@example.org>", OWNER, "", "Hackathon invite", "Old invite.", {}),

    ("Inbox", "Sleep & Memory Lab <lab@psych.example.org>", "students@example.edu", "",
     "Participants needed: paid online study on sleep and memory (Rs 500)",
     "We are looking for students aged 18-25 for a 45-minute online study. Participants receive Rs 500. "
     "Sign up at https://psych.example.org/sleep-study before 25 October 2026.", {}),

    ("Inbox,Category Updates", "Jobs Portal <student@jobsportal.example.com>", OWNER, "",
     "Top internships for you, Riya",
     "Hi Riya, 25 new internships match your profile.\nData Analyst Intern at Globex - Rs 15,000/month - "
     "apply by 18 October 2026\nSee all: https://jobsportal.example.com/internships?utm_source=mail\n"
     "Unsubscribe: https://jobsportal.example.com/unsubscribe?u=8f3a9c",
     {"List-Unsubscribe": "<https://jobsportal.example.com/unsubscribe?u=8f3a9c>"}),

    ("Inbox", "Training & Placement Cell <placement@example.edu>", "ug-2023-batch@example.edu", "",
     "Campus Recruitment Drive: Globex Analytics - Graduate Engineer Trainee (2027 batch)",
     "Dear Students,\n\nGlobex Analytics will recruit Graduate Engineer Trainees from the 2027 batch. "
     "CTC: Rs 12 LPA.\nRegister on the placement portal by 12 October 2026: https://placement.example.edu/drives/globex",
     {}),

    ("Inbox", "Career Development Centre <career.cell@example.edu>", "ug-2023-batch@example.edu", "",
     "Talk on Higher Studies in Germany - 7 October, LH-1",
     "Dear Students, a talk on higher studies in Germany will be held on 7 October at 5 PM in LH-1.", {}),
]


def build(start: datetime):
    """Return (label, EmailMessage) pairs; message i is sent start + i * 18 hours."""
    out = []
    for i, (labels, sender, to, cc, subject, body, extra) in enumerate(MAILS):
        msg = EmailMessage(policy=default)
        msg["From"], msg["To"], msg["Subject"] = sender, to, subject
        if cc:
            msg["Cc"] = cc
        msg["Date"] = format_datetime(start + timedelta(hours=18 * i))
        msg["Message-ID"] = f"<sample-{i:02d}@mail.example.com>"
        msg["Delivered-To"] = "23cs01042@example.edu"
        msg["X-Gmail-Labels"] = labels
        for key, value in extra.items():
            if key != "Content-Type":
                msg[key] = value
        msg.set_content(body, subtype="html" if extra.get("Content-Type") == "text/html" else "plain")
        out.append(msg)
    # the HackNova mail again, as Takeout repeats a message once per label
    dup = EmailMessage(policy=default)
    for key, value in out[1].items():
        dup[key] = value
    dup.set_content(out[1].get_content(), subtype="html")
    out.append(dup)
    return out


def write_mbox(path: str, start: datetime = datetime(2026, 9, 20, 9, 30, tzinfo=IST)):
    with open(path, "wb") as fh:
        for i, msg in enumerate(build(start)):
            when = parsedate_to_datetime(msg["Date"]).astimezone(timezone.utc)
            fh.write(f"From 17{i:017d}@xxx {when:%a %b %d %H:%M:%S} +0000 {when:%Y}\n".encode())
            raw = msg.as_bytes(policy=default.clone(linesep="\n"))
            raw = b"\n".join((b">" + line) if line.startswith(b"From ") else line for line in raw.split(b"\n"))
            fh.write(raw.rstrip(b"\n") + b"\n\n")


def write_takeout_zip(mbox_path: str, zip_path: str):
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(mbox_path, "Takeout/Mail/All mail Including Spam and Trash.mbox")


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("output", nargs="?", default=os.path.join(here, "sample_mailbox.mbox"))
    p.add_argument("--zip", action="store_true", help="also write a Google-Takeout-style .zip next to it")
    args = p.parse_args()
    write_mbox(args.output)
    print(f"wrote {args.output}")
    if args.zip:
        z = os.path.splitext(args.output)[0] + ".zip"
        write_takeout_zip(args.output, z)
        print(f"wrote {z}")


if __name__ == "__main__":
    main()
