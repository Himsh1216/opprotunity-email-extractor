# 3 · Run the tool

## Install Python once (3.9 or newer)

| System | How |
|---|---|
| **Windows** | Download from [python.org/downloads](https://www.python.org/downloads/). On the first installer screen, tick **"Add python.exe to PATH"**, then click **Install Now**. |
| **macOS** | Download the macOS installer from [python.org/downloads](https://www.python.org/downloads/). Running `xcode-select --install` in Terminal also works; it brings Python 3.9. |
| **Linux** | Python is usually installed already. On Debian or Ubuntu also run `sudo apt install python3-venv`. |

## Get the tool

On the GitHub page, click the green **Code** button → **Download ZIP**, then unzip it, for example into Documents. If you use git, `git clone` the repository instead.

## Run it

| System | How |
|---|---|
| **Windows** | Double-click **`run_windows.bat`**. If Windows warns *"publisher could not be verified"* or *"Windows protected your PC"*, choose **Run**, or **More info → Run anyway**. The file is plain text, so you can open it in Notepad first. |
| **macOS / Linux** | Open **Terminal**, type `bash ` (with a space), drag **`run_mac_linux.sh`** into the window and press **Enter**. |

The first run creates a private Python environment in the folder (`.venv`) and installs `openpyxl`, the library that writes Excel files. This needs internet once. After that the tool works offline.

Then answer three prompts:

```
1) Drag your Google Takeout .zip (or an .mbox file, or a folder of them)
   into this window, then press Enter:
> /Users/riya/Downloads/takeout-20261113T101500Z-001.zip

2) Your college name (the E-Cell sees it when files are merged): Example Institute of Technology

3) Start date as YYYY-MM-DD, or 'all', or just press Enter for the last 180 days:
```

Sample output:

```
Reading takeout-20261113T101500Z-001.zip (from 17 May 2026) ...
  scanned 5,000 emails ...
  2,140 emails in range. Mailbox owner: 23cs01042@example.edu (Riya Kapoor).
  Used only to hide your details and leave out personal mail; it is not written to the share file.

Done in 6s.
    61 opportunities      -> output/opportunities_example-institute-of-technology_2026-11-13.xlsx
    12 to review           -> output/DO_NOT_SHARE_review_example-institute-of-technology_2026-11-13.xlsx  (sheet 'Review')
    39 campus-only          -> same private file (sheet 'Campus-only')
     3 paid-programme pitches -> same private file (sheet 'Excluded pitches')
```

The `output` folder opens by itself. Expect about 30 seconds per 10,000 emails scanned. Emails outside your date range are skipped after reading only their headers, which is much faster.

## Command line (optional)

```bash
# activate the environment the launcher created, or use your own Python with openpyxl installed
python -m opportunity_extractor extract ~/Downloads/takeout-001.zip --since 2026-07-01 --college "Example Institute"
python -m opportunity_extractor extract ~/ThunderbirdProfile/ImapMail --since all --out-dir results
python -m opportunity_extractor extract inbox.mbox --me 23cs01042@example.edu --name "Riya Kapoor"
```

| Option | Meaning |
|---|---|
| `--since YYYY-MM-DD` / `all` | First date to include (default: last 180 days) |
| `--until YYYY-MM-DD` | Last date to include |
| `--college NAME` | Shown to the organisers as *Shared by*, and used in the file name |
| `--out-dir DIR` | Where to write the two files (default: current folder) |
| `--me EMAIL`, `--name NAME` | Override the detected owner, which is used to hide you and to spot personal mail |
| `--keep-direct` | Also consider emails written only to you; by default they are left out for privacy |
| `--no-placement` | Move your placement cell's own notices to the private file |
| `--config rules.json` | Extra keywords and senders (see [06-how-it-works.md](06-how-it-works.md)). The guided mode loads `rules.json` from the tool folder automatically. |

`python -m opportunity_extractor convert INPUT` writes every email in range to one private spreadsheet, if you want that for yourself.

## Troubleshooting

| Message | Fix |
|---|---|
| `Python 3.9 or newer is not installed` | Install Python as above. On Windows, tick *Add python.exe to PATH*; if you missed it, run the installer again and choose *Modify*. |
| `Could not install openpyxl` | Connect to the internet once. Some campus networks block pip, so try a mobile hotspot. |
| `ensurepip is not available` (Linux) | `sudo apt install python3-venv`, then run again |
| `No .mbox file found inside …zip` | The `.zip` doesn't contain Mail. Check that you ticked **Mail** in Takeout. |
| `No emails found in that date range` | Answer `all` to question 3, or give an earlier start date |
| `Could not find '…'` after dragging | Type the full path, or drag the file again. On Windows you can also right-click the file and choose **Copy as path**. |
| Status column is empty in Excel | Click **Enable Editing** in Excel's yellow Protected View bar. The formulas recalculate when you open the file. |
| The detected owner is wrong | Run from the command line with `--me` and `--name` |

Next: [04-review-and-share.md](04-review-and-share.md)
