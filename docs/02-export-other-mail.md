# 2 · Export from Outlook, a college account with Takeout blocked, Apple Mail or any IMAP account

Use this guide if Google Takeout isn't available to you. It works for:

- Microsoft 365 / Outlook college accounts
- Outlook.com and Hotmail
- Yahoo, Zoho and other IMAP mail
- Gmail accounts where the admin blocked Takeout

The general method is **Thunderbird**, the free and open-source mail app from the Mozilla Foundation (the makers of Firefox). It downloads your mail to your own computer, where this tool can read it.

The tool reads all of these:

- Thunderbird's folders directly (they are mbox files without an extension)
- `.mbox` exports
- Apple Mail `.mbox` exports
- `.eml` files
- maildir folders

## A. Thunderbird (Outlook, Microsoft 365, Gmail, Yahoo, IMAP)

1. Install Thunderbird from **[thunderbird.net](https://www.thunderbird.net)**.
2. Add your account. On first start the account setup opens; later you can reach it via **≡ menu → Account Settings → Account Actions → Add Mail Account**.
   - Enter your name and email address. Thunderbird detects Google and Microsoft accounts and opens **their** sign-in page, so your password goes to Google or Microsoft, not to Thunderbird's servers and not to this tool.
   - If you see *"Need admin approval"* or IMAP is refused, your college has blocked outside mail apps. Ask the IT office, or skip to the note at the end.
3. Let it download your mail. By default Thunderbird keeps a copy of every folder on your computer. You can check this under **Account Settings → Synchronization & Storage → "Keep messages for this account on this computer"**. Wait until the status bar stops showing *Downloading message …*, which can take an hour for a big mailbox.
   - **Gmail through Thunderbird:** `[Gmail] → All Mail` holds everything. Make sure it is ticked under **Synchronization & Storage → Advanced…**.

Then use either of the two routes below.

### A1. Point the tool at Thunderbird's own folder (no add-on)

1. In Thunderbird: **≡ menu → Help → Troubleshooting Information**. Next to **Profile Folder**, click **Open Folder**.
2. **Close Thunderbird.**
3. In the folder that opened, find the **`ImapMail`** folder. It holds one subfolder per account, such as `outlook.office365.com` or `imap.gmail.com`.
4. Drag the `ImapMail` folder, or one account's subfolder, into the tool window.

The tool reads every folder file and ignores the `.msf` index files. It removes duplicates (the same mail in Inbox and All Mail) by Message-ID, and skips messages you deleted in Thunderbird.

### A2. Export with the ImportExportTools NG add-on

1. In Thunderbird: **≡ menu → Add-ons and Themes**, search for **ImportExportTools NG** and click **Add to Thunderbird**.
2. Right-click the folder you want, for example **Inbox** or **All Mail**, then **ImportExportTools NG → Export folder**. Some versions label it **Folder Export (mbox)**. Choose where to save.
3. Drag the exported file, or the folder that contains it, into the tool window.

## B. Apple Mail (Mac)

1. Select a mailbox in the sidebar, for example Inbox, then use **Mailbox menu → Export Mailbox…** and choose a folder.
2. Mail creates a folder such as `Inbox.mbox`. Drag that folder, or the folder that contains several of them, into the tool window.

## C. Outlook desktop `.pst` files (advanced)

The tool cannot read `.pst` files directly. On Mac or Linux you can convert one with `readpst`:

```bash
brew install libpst            # macOS (Homebrew);  Ubuntu/Debian: sudo apt install pst-utils
readpst -o converted/ backup.pst
```

Then run the tool on the `converted/` folder. On Windows, route A is simpler.

## If your college blocks both Takeout and IMAP

Then the mail cannot leave the college system with your own tools. Don't work around your college's IT policy. Ask a classmate whose account allows export, or ask the E-Cell to request the opportunity emails from the college office directly.

Next: [03-run-the-tool.md](03-run-the-tool.md)
