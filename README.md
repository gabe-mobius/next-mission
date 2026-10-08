# Next Mission: shared checklist files

This repository holds the shared files for the Next Mission Grok Bot template, an assistant for U.S. service members who are retiring or separating from active duty.

## What is here

- `MASTER_CHECKLIST.md` is a starter checklist for service members who are retiring or separating. It is organized by how much time is left before the separation or retirement date, from 4 or more years out through the period after separation. It also lists free and discounted perks for transitioning members and veterans.
- `STATE_BENEFITS.md` lists state veteran benefits. It currently covers Texas and Oklahoma, and it explains how to research and add another state using the same rules.
- `check_checklist.py` and `check_state_benefits.py` check the sourcing rules in the two Markdown files.
- `deadlines.py` builds a personal deadline list from the checklist and a profile file.
- `profile.example.json` is an example profile with an explanation of every field.
- `test_profiles/` holds three made-up profiles used for testing. They do not describe real people.
- `VERSION` holds the date of the checklist's last full check.

## How sourcing works

Every row marked `sourced` links to an official page, quotes the words that support the row, and gives the date the page was checked. A row marked `UNVERIFIED` has not been confirmed on an allowed official page. Treat it as something to look into, not as a fact.

The two check scripts enforce these rules. Run them after any edit:

```
python3 check_checklist.py
python3 check_state_benefits.py
```

Each script fails and lists the problem rows if a sourced row is missing an allowed URL, a quote, or a valid date, or if a row has an invalid status. `check_checklist.py` also checks the 'Applies to', 'Branch', 'Due', and 'ID' columns and the Change log. Each script reads its file from `/home/box/transition` by default. To check a copy somewhere else, pass the file path as the first argument, for example `python3 check_checklist.py ./MASTER_CHECKLIST.md`.

## Using deadlines.py

Copy `profile.example.json` to `profile.json` in the same folder and replace the example values with your own (branch, retiring or separating, planned date, spouse and children, planned state, and reminder preferences). Then run:

```
python3 deadlines.py           # items due soon, plus late items you can still act on
python3 deadlines.py --days 60 # look 60 days ahead
python3 deadlines.py --plan    # the full checklist filtered for your profile, grouped by time before your date
```

The script keeps only the rows that apply to your branch and to whether you are retiring or separating, and it works out each due date from your planned date. You can point it at a different profile with `--profile`, and you can test it as if it were another day with `--today YYYY-MM-DD`. Your `profile.json` holds personal details, so do not commit it to a public repository.

## Where the files go

The Next Mission bot expects these files in `/home/box/transition`. A bot created from the template downloads them there during its first conversation.

## Updates

The files are refreshed weekly. When a rule, deadline, number, due date, tag, or status changes in the checklist, the Change log at the end of `MASTER_CHECKLIST.md` records the old value and the new value. `VERSION` is updated to the date of the latest full check.

## Important

This is general information. It is not legal, tax, or financial advice. Rules change and vary by branch, so confirm each item with the linked source and with your own transition, personnel, finance, or VA office. Confirm all move rules, including time limits and household goods shipments, with your installation transportation office.
