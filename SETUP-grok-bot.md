# Next Mission: Setup: Grok Bot (Tier A, the reference build)

Grok Bot is where Next Mission started, and it runs the full behavior: automated reminders and a monthly rules check that keeps your own copy current. You never touch GitHub or any files; your bot does all of it.

## What you need

- A Grok Bot plan (paid). Grok Bot gives you a team of always-on agents with their own cloud computer.
- The Next Mission template link: **https://x.ai/bot/pfhAjpJ4AZTTE2yfpZggS**

## Set it up

1. Create your bot from the Next Mission template link.
2. Start a conversation. Before it says hello, your bot downloads nine files, one time, from the public Next Mission repository (github.com/gabe-mobius/next-mission) onto its own computer: the master checklist, the state benefits file, the scripts that verify sources, work out deadlines, and compare versions, plus the README, the VERSION file, and the profile format.
3. Your bot runs the source checks on the files before using them. If it ever cannot reach the repository, it will tell you and offer to build your checklist straight from the official government pages instead.
4. Answer the interview. One question at a time: your branch, retiring or separating, your date, spouse and kids, your plans, where you'll live, and how often you want reminders.
5. If the GI Bill transfer deadline applies to you, the bot will warn you in that first conversation. It cannot be recovered once missed.
6. You get your personal checklist, sorted by time before your date, every item carrying its official source. Your bot also hands you a web page of your plan in your branch colors, with checkboxes, that opens in any browser on your computer or phone. It sends you a fresh copy whenever something changes.

## How it stays current

- **Reminders.** Your reminder preferences become a scheduled "Transition reminders" job. Each run works out what is due for you (upcoming deadlines, late items you can still act on, and free perks whose claim windows are opening or closing) and sends one short note with source links. If there is nothing worth saying, it sends nothing. Change the schedule or pause it any time by asking.
- **Monthly rules check.** Once a month, your bot re-verifies the rules in your own copy that apply to you against the official sources. It updates any changed row with the source, a quote, and the date, marks anything it can't confirm as not yet confirmed, and runs the source checks. Then it tells you in plain language what changed, as old versus new, with the source link. It never downloads from or writes to the repository again after setup. Nothing changed means no message. You can also ask "What changed for me?" anytime.
- **State benefits and perks.** Your bot rechecks the ones that fit you when they have not been checked in 3 months.

## Good to know

- Your profile (branch, date, family) stays on your bot's computer. Do not share it publicly.
- This is general information, not legal, tax, or financial advice. Confirm move rules with your installation transportation office.
