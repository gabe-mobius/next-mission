# Next Mission: shared checklist files

This repository holds the shared files for the Next Mission Grok Bot template, an assistant for U.S. service members who are retiring or separating from active duty.

## What is here

- `MASTER_CHECKLIST.md` is a starter checklist for service members who are retiring or separating. It is organized by how much time is left before the separation or retirement date, from 4 or more years out through the period after separation. It also lists free and discounted perks for transitioning members and veterans.
- `STATE_BENEFITS.md` lists state veteran benefits. It currently covers Texas and Oklahoma, and it explains how to research and add another state using the same rules.
- `check_checklist.py` and `check_state_benefits.py` check the sourcing rules in the two Markdown files.
- `deadlines.py` builds a personal deadline list from the checklist and a profile file, and lists free perks you can claim now or soon.
- `compare_versions.py` lists the checklist rows that changed between a saved previous copy and the current copy, by row ID, old value versus new value, filtered to a profile.
- `profile.example.json` is an example profile with an explanation of every field.
- `test_profiles/` holds three made-up profiles used for testing the scripts. They do not describe real people, and a normal install does not need them.
- `VERSION` holds the date of the checklist's last full check.

## How sourcing works

Every row marked `sourced` links to an official page, quotes the words that support the row, and gives the date the page was checked. A row marked `UNVERIFIED` has not been confirmed on an allowed official page. Treat it as something to look into, not as a fact.

The two check scripts enforce these rules. Run them after any edit:

```
python3 check_checklist.py
python3 check_state_benefits.py
```

Each script fails and lists the problem rows if a sourced row is missing an allowed URL, a quote, or a valid date, or if a row has an invalid status. `check_checklist.py` also checks the 'Applies to', 'Branch', 'Due', and 'ID' columns and the Change log. Each script checks the file in its own folder by default. To check a copy somewhere else, pass the file path as the first argument, for example `python3 check_checklist.py /path/to/MASTER_CHECKLIST.md`.

## Using deadlines.py

Copy `profile.example.json` to `profile.json` in the same folder and replace the example values with your own (branch, retiring or separating, planned date, spouse and children, planned state, and reminder preferences). Then run:

```
python3 deadlines.py           # items due soon, plus late items you can still act on
python3 deadlines.py --days 60 # look 60 days ahead
python3 deadlines.py --plan    # the full checklist filtered for your profile, grouped by time before your date
python3 deadlines.py --perks   # free perks you can claim now, perks opening soon, and perks with no time limit
```

The script keeps only the rows that apply to your branch and to whether you are retiring or separating, and it works out each due date from your planned date. A 'Due' offset that is a whole multiple of 365 days is read as calendar years (so 4 years before 2027-12-08 is 2023-12-08); other offsets are counted in days. In `--plan`, rows in each section are sorted by date. Perks use the 'Window' column in the perks table (for example `-365..+365`, `any..+365`, or `any`); the default run adds a short section for perks whose claim window opens or closes within your look-ahead, so reminders surface them. Perks have no branch or retiring/separating tags, so choose the ones that fit your plans. You can point it at a different profile with `--profile`, and you can test it as if it were another day with `--today YYYY-MM-DD`. Your `profile.json` holds personal details, so do not commit it to a public repository.

## Checking for rule changes

Before downloading a newer checklist, save the current one, then compare:

```
cp MASTER_CHECKLIST.md MASTER_CHECKLIST.prev.md && cp VERSION VERSION.prev
# download the new MASTER_CHECKLIST.md and VERSION
python3 check_checklist.py
python3 compare_versions.py          # changed rows that apply to profile.json, old vs new
python3 compare_versions.py --all    # every changed row
python3 compare_versions.py --json   # the same, as JSON
```

`compare_versions.py` matches rows by ID, ignores the Change log, and reports a row if its old or new version applies to the profile. If there is no `MASTER_CHECKLIST.prev.md`, it says there is nothing to compare.

## Where the files go

The Next Mission bot expects these files in `/home/box/transition`. A bot created from the template downloads them there during its first conversation.

## Updates

The files are refreshed weekly. When a rule, deadline, number, due date, tag, or status changes in the checklist, the Change log at the end of `MASTER_CHECKLIST.md` records the old value and the new value. `VERSION` is updated to the date of the latest full check.

## Important

This is general information. It is not legal, tax, or financial advice. Rules change and vary by branch, so confirm each item with the linked source and with your own transition, personnel, finance, or VA office. Confirm all move rules, including time limits and household goods shipments, with your installation transportation office.
