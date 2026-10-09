# Next Mission: Setup: Grok Bot (Tier A, the reference build)

Grok Bot is where Next Mission started, and it runs the full behavior: automated reminders, a monthly rules check, and updates handled for you. You never touch GitHub or any files; your bot does all of it.

## What you need

- A Grok Bot plan (paid). Grok Bot gives you a team of always-on agents with their own cloud computer.
- The Next Mission template link: **https://x.ai/bot/pfhAjpJ4AZTTE2yfpZggS**

## Set it up

1. Create your bot from the Next Mission template link.
2. Start a conversation. Before it says hello, your bot downloads nine files from the public Next Mission repository (github.com/gabe-mobius/next-mission) onto its own computer: the master checklist, the state benefits file, the scripts that verify sources, work out deadlines, and compare versions, plus the README, the VERSION file, and the profile format.
3. Your bot runs the source checks on the files before using them. If it ever cannot reach the repository, it will tell you and offer to build your checklist straight from the official government pages instead.
4. Answer the interview. One question at a time: your branch, retiring or separating, your date, spouse and kids, your plans, where you'll live, and how often you want reminders.
5. If the GI Bill transfer deadline applies to you, the bot will warn you in that first conversation. It cannot be recovered once missed.
6. You get your personal checklist, sorted by time before your date, every item carrying its official source.

## How it stays current

- **Reminders.** Your reminder preferences become a scheduled "Transition reminders" job. Each run works out what is due for you (upcoming deadlines, late items you can still act on, and free perks whose claim windows are opening or closing) and sends one short note with source links. If there is nothing worth saying, it sends nothing. Change the schedule or pause it any time by asking.
- **Monthly rules check (the 4th).** The master checklist is re-verified and republished on the 2nd of each month. On the 4th, your bot downloads the new files into a holding folder and swaps them in only if they pass the source checks. It then compares old and new, keeps only the changes that apply to you, and reports them in plain language with the source link. Nothing changed means no message.
- **State benefits and perks.** Your bot rechecks the ones that fit you when they have not been checked in 3 months.

## Good to know

- Your profile (branch, date, family) stays on your bot's computer. Do not share it publicly.
- This is general information, not legal, tax, or financial advice. Confirm move rules with your installation transportation office.
