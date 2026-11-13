"""Keyword rules. Each rule is (label shown in the 'Why flagged' column, regex, weight).

Tune these, or add your own without editing code through a JSON config (see examples/rules.example.json).
"""
from __future__ import annotations

import json
import re
from typing import Dict, List, Tuple

Rule = Tuple[str, str, int]

# Thresholds on the total score of a thread.
HIGH = 7        # >= HIGH: listed on the Opportunities sheet
MEDIUM = 4      # MEDIUM..HIGH-1: listed on the Review sheet
PITCH = 5       # pitch score >= PITCH: moved to the Excluded pitches sheet
BODY_CAP = 6    # most points the body can add

# ---- subject line: what an opportunity announcement looks like -------------------------------
SUBJECT_RULES: List[Rule] = [
    ("internship", r"\bintern(?:s|ship|ships)?\b", 7),
    ("hiring", r"\bhiring\b|\bnow hiring|\bwe(?:'re| are) hiring", 7),
    ("recruitment drive", r"\brecruitment\b|\bplacement (?:drive|opportunit)|"
                          r"\bcampus (?:drive|hiring|placement|recruitment)|\boff[- ]campus\b|\bpool(?:ed)? (?:campus )?drive", 7),
    ("job opening", r"\bjob(?:s)?\b.{0,15}\b(?:opening|opportunit|offer|fair|posting|vacanc)|\bvacanc(?:y|ies)\b|"
                    r"\bpositions? (?:open|available)|\bwalk[- ]?in\b|\bgraduate (?:engineer )?trainee|"
                    r"\bmanagement trainee|\bpre[- ]placement offer|\bfaculty positions?|\bpost of\b", 6),
    ("scholarship", r"\bscholarships?\b|\bstudentships?\b|\bfee waiver|\bfinancial (?:aid|assistance)", 7),
    ("fellowship", r"\bfellowships?\b", 7),
    ("hackathon", r"\bhack(?:athon|fest|s)?\b|\bhack\w{1,8}\s+\d+(?:\.\d+)?\b|\bideathon|\bdatathon|\bcodeathon|"
                  r"\bbuildathon|\bmakeathon|\bgame ?jam", 7),
    ("competition", r"\bcompetitions?\b|\bcontests?\b|\bolympiad|\bcase (?:study )?(?:competition|challenge)|"
                    r"\bquiz(?:zes)?\b|\bdebate\b|\bprize pool\b", 7),
    ("challenge", r"\bchallenge\b", 5),
    ("participation call", r"\binvit\w* (?:you |students )?to participate\b|\bparticipate in\b|\bparticipation in\b|"
                           r"\bcall for participation|\bparticipation invit\w*|\binvitation (?:for|to) participat\w*|"
                           r"\bmass participation|\bstudent participation", 4),
    ("call for", r"\bcall for (?:papers?|abstracts?|proposals?|applications?|nominations?|entries|participants?|"
                 r"submissions?|participation|ideas|contributions?)|\bpresent your (?:ideas?|papers?|research|work)", 7),
    ("applications open", r"\bapplications? (?:are )?(?:now )?(?:open|invited|closing)|\binvit(?:ing|ation for) applications|"
                          r"\bapply (?:now|by|before|online|today)|\bregistrations? (?:are )?(?:now )?(?:open|live|closing)|"
                          r"\bregister (?:now|by|before|today)|\bnominations? (?:are )?(?:open|invited)|"
                          r"\binvitation for nominations|\badmissions? (?:are )?(?:open|20\d\d)|"
                          r"\blast date to (?:apply|register)|\bdeadline (?:extended|approaching)|"
                          r"\bcomplete your application|\blast day to (?:apply|register)|\bis (?:now )?live\b", 6),
    ("programme", r"\bsummer school|\bwinter school|\bbootcamp|\btraining (?:program|programme)|"
                  r"\bskill(?:s)? (?:development )?program|\bcertification (?:course|program)|\bonline course|"
                  r"\bmasterclass|\bfaculty development program|\bfdp\b", 5),
    ("workshop", r"\bworkshop\b", 2),
    ("award", r"\bawards?\b|\bpuraskar\b", 6),
    ("conference", r"\bconference\b|\bsymposium\b|\bconclave\b|\bsummit\b|\bcongress\b", 3),
    ("higher studies", r"\bph\.?\s?d\.?\b.{0,30}\b(?:admission|program|position|opening|application)|"
                       r"\bm\.?tech\b.{0,25}\badmission|\bmasters?\b.{0,25}\b(?:program|admission|abroad)|"
                       r"\badmissions?\b|\bstudy abroad|\bexchange program", 5),
    ("ambassador", r"\bambassadors?\b", 6),
    ("paid study", r"\bpaid (?:study|research|participation|survey)|\bcall for participants|"
                   r"\bparticipants? (?:needed|wanted|required)|\bresearch participants?", 7),
    ("selection", r"\binduction|\binducting\b|\bopen selections?|\bselections? for\b|\btrials?\b|\bcontingent\b|"
                  r"\bcore team|\bjoin (?:our|the) team|\bteam selection|\b(?:club|core|team) recruitments?\b", 5),
    ("opportunity", r"\bopportunit(?:y|ies)\b", 4),
    ("startup support", r"\bstartup\b.{0,30}\b(?:program|challenge|cohort|grant|funding|incubat)|\bincubation\b|"
                        r"\bgrants?\b|\bfunding (?:call|opportunit)|\bseed fund", 5),
]

# ---- body: supporting evidence (each counted once, total capped at BODY_CAP) ------------------
BODY_RULES: List[Rule] = [
    ("eligibility stated", r"\beligib(?:le|ility)\b", 1),
    ("stipend/salary", r"\bstipend\b|\bctc\b|\blpa\b|\bsalary\b|\bremuneration\b|\bper month\b", 2),
    ("prizes", r"\bprizes?\b|\bcash reward|\bprize pool|\bworth (?:₹|rs)", 2),
    ("application link", r"forms\.gle|docs\.google\.com/forms|forms\.office\.com|unstop\.com|devfolio\.co|"
                         r"hackerearth\.com|internshala\.com|\b(?:registration|application) (?:link|form)|"
                         r"\b(?:apply|register) (?:here|at|via|through|using|on)\b", 2),
    ("deadline stated", r"\blast date|\bdeadline\b|\bon or before\b|\bcloses on\b|\bapply by\b|\bregister by\b", 1),
    ("selection process", r"\bselection process|\bshortlisting\b|\bjob description|\bjd\b|"
                          r"\broles? (?:&|and) responsibilities|\bselected candidates will", 1),
    ("who can apply", r"\bopen to (?:all|students|undergraduate|ug|pg)|\bwho can (?:apply|participate)|"
                      r"\bteam size|\bteams? of (?:up to )?\d|\bindividual or team", 1),
]

# ---- subject lines that are NOT announcements, whatever else they say --------------------------
NEGATIVE_RULES: List[Rule] = [
    ("results/selection process", r"\bshortlist(?:ed)?\b(?!.{0,25}\bregistration)|\bselected (?:students|candidates|list)|"
                                  r"\bresults?\b|\bwinners?\b|\bcongratulations\b|"
                                  r"\binterview (?:schedule|slots?|link|invite|process|date)|\bround \d|"
                                  r"\b(?:online )?(?:test|assessment) (?:link|schedule|details|credentials)|"
                                  r"\boffer letter|\bjoining\b|\bonboarding\b|\bpre[- ]placement talk|\bppt\b|"
                                  r"\bcertificates? (?:of|for) (?:participation|merit)|\bclosing ceremony|\bprize distribution|"
                                  r"\b(?:final|contingent|selected|merit|provisional) list\b|\bstatus of\b|"
                                  r"\byour (?:application|submission|registration) (?:status|has been|is)\b|\baward of\b", -9),
    ("scholarship/fee paperwork", r"\bdisburse|\bbank (?:account )?details|\bverification\b|\bhard ?copy|"
                                  r"\bdocuments? (?:submission|required|verification)|\bfee (?:payment|receipt|structure)|"
                                  r"\brenewal (?:form|documents)", -8),
    ("convocation", r"\bconvocation\b|\bgraduation ceremony|\bdegree certificate", -9),
    ("coursework", r"(?<!backward )\bclass(?:es)?\b|\blectures?\b(?! series)|\bassignment|\bquiz \d|"
                   r"\bquiz (?:on|tomorrow|today|schedule|postponed|marks|link)|\blink for the quiz|\bmid[- ]?sem|\bend[- ]?sem|"
                   r"\bexam(?:ination)?s?\b|\btime ?table|\battendance\b|\bgrades?\b|\bsyllabus\b|"
                   r"\bnew (?:material|announcement)|\bdue tomorrow|\btutorial\b|\blab\b|\bviva\b", -7),
    ("hostel/mess", r"\bmess\b|\bmenu\b|\bhostel\b|\bwarden\b|\bsnacks?\b|\bdinner\b|\blunch\b|\bbreakfast\b|"
                    r"\bwater supply|\bpower (?:shut ?down|cut|outage)|\bmaintenance\b|\blaundry\b|\bgate pass", -7),
    ("account/system", r"security alert|\bsign[- ]?in\b|\bpassword\b|verification code|\botp\b|delivery status|"
                       r"undeliver|automatic reply|out of office|\breceipt\b|\binvoice\b|"
                       r"\border (?:confirmed|shipped|delivered)|\bpayment (?:received|successful|failed)|"
                       r"\b(?:shared|invited) (?:with you|you to)\b", -9),
    ("admin/greetings", r"\boffice order\b|\bholiday\b|\bcondolence|\bgreetings\b|\bhappy \w+|\bwishes\b|"
                        r"\bobituary\b|\bnotice regarding\b|\bregarding (?:my|the) (?:fee|leave|attendance)|"
                        r"\boutgoing\b|\btenure\b|\bachievements?\b|\bfarewell\b", -5),
    ("talk/info session", r"\btalk (?:on|by)\b|\binfo(?:rmation)? session|\bwebinar on\b|\bguest lecture|"
                          r"\bsession on\b|\blecture series\b|\binteraction with\b", -6),
    ("feedback/survey", r"\bfeedback\b|\bsurvey\b|\bpoll\b|\bquestionnaire", -6),
    ("event/campaign", r"\bcelebrations?\b|\bcleaning drive|\bpledge\b|\bplantation|\bblood donation|\bawareness\b|\bcampaign\b|"
                       r"\bscreening\b|\bdj night|\bgarba|\bfood festival", -5),
    ("social notification", r"\breacted to\b|\bcommented on\b|\bviewed your profile|\baccepted your invitation|"
                            r"\binvitation to connect|\bnew messages?\b|\bmentioned you\b|\bfollowed you\b|\bposted\b", -10),
    ("promotion", r"\b\d{1,2}\s?% off\b|\bsale\b|\bdiscount|\bcoupon|\bcashback|\bbuy now|\bshop now|\bdeals?\b|"
                  r"\boffer ends\b|\bfree trial\b|\bupgrade\b|\bsubscription\b|\bnewsletter\b", -7),
]

SENDER_RULES: List[Rule] = [
    ("course notification", r"@classroom\.google\.com$|@(?:[\w-]+\.)*(?:moodle|canvas|instructure|blackboard)\.", -10),
    ("social network sender", r"@(?:[\w-]+\.)*(?:linkedin|facebook|facebookmail|instagram|twitter|x|quora|youtube|"
                              r"medium|reddit|pinterest|discord|snapchat|telegram|whatsapp)\.com$", -12),
    ("shopping/media sender", r"@(?:[\w-]+\.)*(?:amazon|flipkart|myntra|ajio|meesho|swiggy|zomato|paytm|phonepe|"
                              r"uber|olacabs|zepto|blinkit|bigbasket|nykaa|bookmyshow|netflix|spotify|hotstar|"
                              r"airtel|jio|economictimes|economictimesnews|timesofindia|hindustantimes|"
                              r"moneycontrol|ndtv|indiatimes|zrpl)\.(?:com|in|co\.in|net)$", -8),
]

# Automated senders: mail from these is never "personal", even when addressed only to you.
AUTOMATED_SENDER = r"^(?:no[-_.]?reply|do[-_.]?not[-_.]?reply|donot[-_.]?reply|noreply\w*|notifications?|newsletters?|" \
                   r"news|info|updates?|hello|team|support|helpdesk|admissions?|marketing|events?|community|contact|" \
                   r"mailer|bounces?|alerts?)\b"

# Student bodies, clubs, councils, fests and halls (any college) - their own events are campus-only.
STUDENT_BODY_TOKENS = {"gsec", "secy", "secretary", "club", "clubs", "soc", "society", "council", "fest", "coord",
                       "coordinator", "chairperson", "president", "vpresident", "vp", "sg", "gymkhana", "hor", "hall",
                       "hostel", "messsec", "cult", "sports", "lit", "quiz", "ecell", "nss", "ncc", "fasnc", "aso"}
# Links that do not point outside the college (forms, drives, chat groups, social media).
NEUTRAL_LINK_DOMAINS = ("google.com", "forms.gle", "goo.gl", "bit.ly", "tinyurl.com", "forms.office.com",
                        "office.com", "whatsapp.com", "chat.whatsapp.com", "instagram.com", "linkedin.com",
                        "youtube.com", "youtu.be", "facebook.com", "twitter.com", "x.com", "zoom.us", "meet.google.com",
                        "teams.microsoft.com", "microsoft.com", "drive.google.com", "canva.com", "notion.site")

# Career / training & placement cell addresses (any college).
PLACEMENT_SENDER = r"^(?:[\w.-]*[._-])?(?:cdc|tpo|tnp|t-n-p|tandp|placements?|career|careers|crc|ctp|cgc|cdps|ocs|" \
                   r"training[._-]?(?:and[._-]?)?placement|placement[._-]?cell|internship[._-]?cell)[\w.-]*@"
PLACEMENT_BONUS = 3
BULK_PENALTY = -1

# ---- opportunity type: first match wins (subject first, then the start of the body) ------------
TYPE_RULES: List[Tuple[str, str]] = [
    ("Paid Research Study", r"\bpaid (?:study|research|participation|survey)|\bcall for participants|"
                            r"\bparticipants? (?:needed|wanted|required)|\b(?:eeg|fmri|eye[- ]tracking|user) study"),
    ("Campus Selection / Induction", r"\binduction|\binducting\b|\bopen selections?|\bselections? for\b|\btrials?\b|"
                                     r"\bcontingent\b|\bcore team|\bjoin (?:our|the) team|\bteam selection|\bclub recruitments?"),
    ("Internship", r"\bintern(?:s|ship|ships)?\b"),
    ("Job / Recruitment", r"\bhiring\b|\brecruit|\bjobs?\b|\bvacanc|\bopenings?\b|\bplacement\b|\bcampus drive|"
                          r"\bfull[- ]time|\btrainee\b|\bppo\b|\bpositions?\b|\bpost of\b|\bwalk[- ]?in\b"),
    ("Scholarship / Fellowship", r"\bscholarship|\bfellowship|\bstudentship|\bfee waiver|\bfinancial (?:aid|assistance)"),
    ("Hackathon / Competition", r"\bhack(?:athon|fest|s)?\b|\bhack\w{1,8}\s+\d+(?:\.\d+)?\b|\bideathon|\bdatathon|"
                                r"\bcodeathon|\bbuildathon|\bmakeathon|"
                                r"\bgame ?jam|\bcompetition|\bcontest|\bolympiad|\bquiz\b|\bchallenge\b|\bdebate\b|"
                                r"\bcase study\b|\bprize pool"),
    ("Award / Nomination", r"\baward|\bnominat|\bpuraskar|\bhonou?rs?\b"),
    ("Call for Papers / Conference", r"\bcall for (?:papers?|abstracts?|submissions?|proposals?|contributions?)|\bpapers?\b|"
                                     r"\babstracts?\b|\bconference|\bsymposium|\bsummit\b|\bconclave|\bjournal|\bcongress\b"),
    ("Training / Skill Programme", r"\bworkshop|\bbootcamp|\btraining\b|\bcourse\b|\bcertification|\bsummer school|"
                                   r"\bwinter school|\bmasterclass|\bfdp\b|\bskill"),
    ("Higher Studies / Admissions", r"\badmission|\bph\.?\s?d|\bm\.?tech|\bmasters?\b|\bstudy abroad|\bexchange program|\bgre\b"),
    ("Ambassador Role", r"\bambassador"),
    ("Startup / Funding", r"\bstartup|\bincubat|\bgrants?\b|\bfunding|\bseed fund"),
]

# ---- campus-only items (club inductions, hostel events, inter-college sports selections) -------
CAMPUS_SUBJECT = (r"\binter[- ]?(?:hall|hostel|house|branch|department|batch)|\bhall of residence|\bhostel|"
                  r"\bresidents\b|\bgeneral championship|\bfreshers?'?\b|\binduction|\binducting|\bcontingent\b|"
                  r"\binter[- ]?(?:iit|nit|iiit)\b|\bour (?:club|society)|\bclub\b|\bsociety\b|\bgymkhana\b")
CAMPUS_BODY = (r"\binter[- ]?(?:hall|hostel)|\bresidents\b|\bfreshers?'?\b|\binduction|\bcontingent\b|"
               r"\bgeneral championship|\bhall of residence|\binter[- ]?iit\b")
# Types that are about the outside world even when a student body relays them.
OUTWARD_TYPES = {"Internship", "Job / Recruitment", "Scholarship / Fellowship", "Higher Studies / Admissions",
                 "Call for Papers / Conference", "Paid Research Study", "Startup / Funding"}
OPEN_TO_OTHERS = (r"\binter[- ]?college|\b(?:inter)?national\b|\binternational\b|\ball[- ]india\b|\bacross india|"
                  r"\bnation[- ]?wide|\bregional\b|\bglobal\b|\bother (?:colleges|institutes|universities)|"
                  r"\bopen to (?:all|students of all)")

# ---- unsolicited paid programmes sold as "internships" -----------------------------------------
PITCH_DOMAINS: List[str] = ["ucanly", "corizo", "elytespark", "internzvalley", "unlox", "unloxacademy",
                            "skillvedanth", "verzeo", "internsvalley"]
PITCH_RULES: List[Rule] = [
    ("'profile shortlisted' without applying", r"\bprofile (?:has been |is )?shortlisted|"
                                               r"\byou(?:'ve| have) been (?:shortlisted|selected) for (?:an? |the )?"
                                               r"(?:internship|training|program)", 3),
    ("programme fee", r"\bprogram(?:me)? fee|\bregistration fee\b.{0,60}\b(?:internship|training|program)|"
                      r"\bfee grant|\bscholarship code|\buse (?:the )?code\b|\bfee (?:is )?applicable", 3),
    ("placement assistance / guarantee", r"\bplacement assistance|\bjob guarantee|\bguaranteed (?:internship|placement)", 2),
    ("certified training & internship", r"\btraining\s*(?:&|and|cum|-cum-)\s*internship|\binternship\s*(?:&|and)\s*training|"
                                        r"\b(?:ibm|microsoft|google|aws|nasscom|nsdc|aicte)\b.{0,40}"
                                        r"\b(?:certified|certification|collaborat\w*|approved)\b", 2),
    ("pressure tactics", r"\blimited (?:seats|slots)|\bslots? (?:left|allocated|remaining)|\bcloses today\b|\bhurry\b|"
                         r"\blast few seats|\bfirst come,? first (?:serve|take)", 1),
    ("'mandatory' / 'urgent' wording", r"\bmandatory confirmation|\baction required|\burgent response required|"
                                        r"\bconfirm your (?:seat|slot|enrol)", 2),
    ("resume-score / enrolment hook", r"\bresume score|\binternship enrol(?:l)?ment|\bacademic internship", 3),
]

# ---- links worth showing -----------------------------------------------------------------------
GOOD_LINK = (r"forms\.gle|docs\.google\.com/forms|forms\.office\.com|unstop|devfolio|hackerearth|hackerrank|"
             r"internshala|lu\.ma|eventbrite|typeform|airtable|register|registration|apply|application|"
             r"careers?|jobs?|hackathon|challenge|scholarship|fellowship|admission|bit\.ly|tinyurl|forms\.")
BAD_LINK = (r"unsubscribe|optout|opt-out|/preferences|facebook\.com|instagram\.com|twitter\.com|//x\.com|youtube\.com|"
            r"linkedin\.com/(?:company|in|school)/|\.(?:png|jpe?g|gif)(?:\?|$)|google\.com/maps|play\.google|"
            r"apps\.apple|/track|click\.|/wf/click|mailchi\.mp|list-manage")


def load_config(path: str) -> Dict:
    """Extend the rules from a JSON file. Unknown keys are ignored."""
    with open(path, encoding="utf-8") as fh:
        cfg = json.load(fh)
    extra = [re.escape(k) for k in cfg.get("extra_opportunity_keywords", [])]
    if extra:
        SUBJECT_RULES.append(("your keyword", r"\b(?:" + "|".join(extra) + r")\b", 7))
    ignore = [re.escape(k) for k in cfg.get("extra_ignore_keywords", [])]
    if ignore:
        NEGATIVE_RULES.append(("your ignore keyword", r"\b(?:" + "|".join(ignore) + r")\b", -10))
    PITCH_DOMAINS.extend(d.lower() for d in cfg.get("pitch_domains", []))
    campus = [re.escape(k) for k in cfg.get("campus_keywords", [])]
    global CAMPUS_SUBJECT
    if campus:
        CAMPUS_SUBJECT += r"|\b(?:" + "|".join(campus) + r")\b"
    return cfg
