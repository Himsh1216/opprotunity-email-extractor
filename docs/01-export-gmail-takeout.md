# 1 · Export your Gmail with Google Takeout

Google Takeout is Google's own export service. It packs your mail into a single `.mbox` file inside a `.zip`. You sign in to Google, not to this tool, and nobody else sees your password.

**Time:** about 3 minutes to request. Google then takes anywhere from under an hour to a day or more to prepare it, depending on mailbox size. **Space:** expect roughly 1–10 GB for a student mailbox.

## Steps

1. Open **[takeout.google.com](https://takeout.google.com)** on a computer. Check the account in the top-right corner. If you use several Google accounts, switch to the one whose mail you want, for example your college account.
2. Under **Select data to include**, click **Deselect all**.
3. Scroll to **Mail** and tick it.
   - *Optional:* **All Mail data included** lets you pick labels. Leave everything selected unless the export would be too large. Opportunity emails usually sit in Inbox, Updates, Promotions and Forums.
4. Scroll to the bottom and click **Next step**.
5. Choose:
   - **Destination:** *Send download link via email*
   - **Frequency:** *Export once*
   - **File type & size:** *.zip* and **50 GB**, so that you get a single file instead of several parts
6. Click **Create export**. You can close the tab.
7. When the email *"Your Google data is ready to download"* arrives, click **Download your files**. Google may ask for your password again; that is Google's own page. You get a file named like `takeout-20261113T101500Z-001.zip`.

**Don't unzip it.** The tool reads the `.zip` directly. Inside is `Takeout/Mail/All mail Including Spam and Trash.mbox`. The tool skips spam, trash, drafts and chats by itself, using Gmail's labels.

> The download link stays valid for about a week. If it expires, request the export again.

## If something is different

| What you see | What it means / what to do |
|---|---|
| **Mail** isn't in the list, or Takeout says it isn't available for your account | Your college's Google Workspace admin has turned Takeout off; admins can do this, and some school editions start with it off. Use the Thunderbird route in [02-export-other-mail.md](02-export-other-mail.md). |
| The export arrived in several `.zip` parts | Put all the parts in one folder and drag that **folder** into the tool. |
| You want a smaller download | In step 3, choose only some labels. Every label you pick becomes its own `.mbox`, and the tool removes the duplicates that appear in several labels. |
| You selected more than Mail | No problem. The tool ignores everything in the `.zip` except `.mbox` files. |

Next: [03-run-the-tool.md](03-run-the-tool.md)
