#!/usr/bin/env python3
"""Personal deadline list built from MASTER_CHECKLIST.md and your profile.

Usage:
  python3 deadlines.py                 # items due soon + late items you can still act on
  python3 deadlines.py --days 60       # look 60 days ahead instead of the profile's lookahead_days
  python3 deadlines.py --plan          # your full filtered checklist, grouped by time bucket
  python3 deadlines.py --perks         # free perks you can claim now or soon, plus any-time perks
  python3 deadlines.py --profile test_profiles/navy_separatee.json --today 2026-10-08

The profile is read from profile.json next to this script unless --profile is given.
Copy profile.example.json to profile.json and fill it in. Rows are kept when:
  * 'Applies to' is `both` or matches retiring_or_separating, and
  * 'Branch' is `all` or lists your branch, and
  * GI Bill transfer and Survivor Benefit Plan rows only when you have a spouse or children.
'Due' is relative to separation_date (e.g. -365, +120, -180..-90, none). An offset that
is a whole multiple of 365 is read as calendar years (-1460 from 2027-12-08 is 2023-12-08);
any other offset is counted in days.
Perks come from the perks section. Each perk row has a 'Window' cell (any, -365..+365,
any..+365, ...) counted the same way from separation_date. Perks have no branch or
retiring/separating tags, so they are filtered by window only; pick the ones that fit the
person's plans. The default run adds a short section for perks whose window opens (or
closes) within the look-ahead; --perks lists everything you can claim now or soon.
This is a planning aid, not legal advice; check each row's source.
"""
import argparse, datetime, json, os, re, sys, textwrap
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

HERE = os.path.dirname(os.path.abspath(__file__))
BRANCHES = ["army", "navy", "marine-corps", "air-force", "space-force", "coast-guard"]
CADENCES = ["daily", "weekly", "biweekly", "monthly"]
DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
FAMILY_TOPICS = ("GI Bill transfer (TEB)", "Retirement (SBP)")
PERKS_HEADING = "free and discounted perks"
# Extra plain-English notes printed under specific rows, keyed by row ID.
NOTES = {
    "4y-gi-bill-transfer": (
        "Time-sensitive decision, not an automatic to-do: transferring requires agreeing to 4 more "
        "years of service (an added service obligation), requested in milConnect while on active duty. "
        "If your date is less than 4 years away, transferring means serving past it. Whether that is "
        "worth it is your decision; talk it over with your career counselor or personnel office."),
}


def die(msg, code=1):
    print(msg)
    sys.exit(code)


def load_profile(path):
    if not os.path.exists(path):
        die(f"No profile found at {path}.\n"
            f"Create one by copying profile.example.json to profile.json and filling in your own details:\n"
            f"  cp {os.path.join(HERE, 'profile.example.json')} {os.path.join(HERE, 'profile.json')}")
    try:
        p = json.load(open(path, encoding="utf-8"))
    except json.JSONDecodeError as e:
        die(f"The profile at {path} is not valid JSON: {e}")
    p = {k: v for k, v in p.items() if not k.startswith("_")}
    errs = []
    branch = str(p.get("branch", "")).strip().lower().replace(" ", "-")
    if branch not in BRANCHES:
        errs.append(f"branch must be one of {', '.join(BRANCHES)} (got '{p.get('branch')}')")
    p["branch"] = branch
    ros = str(p.get("retiring_or_separating", "")).strip().lower()
    if ros not in ("retiring", "separating"):
        errs.append(f"retiring_or_separating must be 'retiring' or 'separating' (got '{p.get('retiring_or_separating')}')")
    p["retiring_or_separating"] = ros
    try:
        p["separation_date"] = datetime.date.fromisoformat(str(p.get("separation_date", "")))
    except ValueError:
        errs.append(f"separation_date must be YYYY-MM-DD (got '{p.get('separation_date')}')")
    if not isinstance(p.get("spouse", False), bool):
        errs.append("spouse must be true or false")
    try:
        p["children"] = int(p.get("children", 0))
        if p["children"] < 0:
            raise ValueError
    except (TypeError, ValueError):
        errs.append("children must be a whole number, 0 or more")
    p["reminder_cadence"] = str(p.get("reminder_cadence") or "weekly").strip().lower()
    if p["reminder_cadence"] not in CADENCES:
        errs.append(f"reminder_cadence must be one of {', '.join(CADENCES)}")
    p["reminder_day"] = str(p.get("reminder_day") or "Monday").strip()
    if p["reminder_cadence"] != "daily" and p["reminder_day"].lower() not in DAYS:
        errs.append("reminder_day must be a day of the week, for example Monday")
    p["reminder_time"] = str(p.get("reminder_time") or "08:00").strip()
    if not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", p["reminder_time"]):
        errs.append("reminder_time must be HH:MM in 24-hour time, for example 08:00")
    p["timezone"] = str(p.get("timezone") or "America/Chicago").strip()
    try:
        ZoneInfo(p["timezone"])
    except (ZoneInfoNotFoundError, ValueError):
        errs.append(f"timezone must be an IANA name such as America/Chicago (got '{p['timezone']}')")
    try:
        p["lookahead_days"] = int(p.get("lookahead_days", 30) if p.get("lookahead_days") is not None else 30)
        if p["lookahead_days"] < 0:
            raise ValueError
    except (TypeError, ValueError):
        errs.append("lookahead_days must be a whole number, 0 or more")
    if errs:
        die("Your profile has problems:\n" + "\n".join(f"  - {e}" for e in errs))
    return p


def offset_date(base, days):
    """base + days, but whole multiples of 365 are calendar years (Feb 29 -> Feb 28)."""
    if days and days % 365 == 0:
        y = base.year + days // 365
        try:
            return base.replace(year=y)
        except ValueError:
            return base.replace(year=y, day=28)
    return base + datetime.timedelta(days=days)


def parse_due(due):
    due = due.strip()
    if due == "none":
        return None
    if ".." in due:
        a, b = due.split("..")
        return int(a), int(b)
    return int(due), int(due)


def parse_window(w):
    """'any' -> (None, None); 'A..B' with either side 'any' -> (int|None, int|None)."""
    w = (w or "any").strip()
    if w == "any":
        return None, None
    a, b = w.split("..")
    return (None if a == "any" else int(a)), (None if b == "any" else int(b))


def load_perks(path):
    perks, section, header = [], "", None
    for line in open(path, encoding="utf-8").read().splitlines():
        if line.startswith("#"):
            section, header = line.lstrip("#").strip(), None
            continue
        if not line.strip().startswith("|"):
            header = None
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if header is None:
            header = cells
            continue
        if PERKS_HEADING not in section.lower() or len(cells) != len(header):
            continue
        if all(re.fullmatch(r":?-{3,}:?", c) for c in cells):
            continue
        r = dict(zip(header, cells))
        try:
            r["window"] = parse_window(r.get("Window", "any"))
        except ValueError:
            r["window"] = (None, None)
        perks.append(r)
    return perks


def perk_dates(r, sep):
    a, b = r["window"]
    return (None if a is None else offset_date(sep, a)), (None if b is None else offset_date(sep, b))


def show_perk(r, sep, extra=""):
    da, db = perk_dates(r, sep)
    if da is None and db is None:
        when = "any time"
    elif da is None:
        when = f"until {db.isoformat()}"
    elif db is None:
        when = f"from {da.isoformat()}"
    else:
        when = f"{da.isoformat()} to {db.isoformat()}"
    flag = "  [UNVERIFIED: confirm before relying on it]" if r.get("Status") == "UNVERIFIED" else ""
    print(f"- {when}{extra}  [{r['ID']}] {r.get('Topic', '')}{flag}")
    print(textwrap.fill(first_sentence(r["Item"]), width=100, initial_indent="    ", subsequent_indent="    "))
    print(textwrap.fill("Who qualifies: " + r.get("Who qualifies", ""), width=100, initial_indent="    ", subsequent_indent="      "))
    for u in urls(r) or ["(no official source confirmed)"]:
        print(f"    Source: {u}")


def classify_perks(perks, sep, today, end):
    """Returns (open_dated, opening, anytime, closed) lists of (sort_date, extra_text, row)."""
    open_dated, opening, anytime, closed = [], [], [], 0
    for r in perks:
        da, db = perk_dates(r, sep)
        if da is None and db is None:
            anytime.append((today, "", r))
        elif db is not None and db < today:
            closed += 1
        elif da is not None and da > today:
            if da <= end:
                opening.append((da, f" (opens in {(da - today).days} days)", r))
        else:
            extra = f" (open now; closes in {(db - today).days} days)" if db is not None else " (open now)"
            open_dated.append((db or end, extra, r))
    return open_dated, opening, anytime, closed


def load_rows(path):
    rows, section, header = [], "", None
    for line in open(path, encoding="utf-8").read().splitlines():
        if line.startswith("#"):
            section, header = line.lstrip("#").strip(), None
            continue
        if not line.strip().startswith("|"):
            header = None
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if header is None:
            header = cells
            continue
        if all(re.fullmatch(r":?-{3,}:?", c) for c in cells) or "Due" not in header:
            continue
        if PERKS_HEADING in section.lower() or len(cells) != len(header):
            continue
        r = dict(zip(header, cells))
        r["bucket"] = section
        r["window"] = parse_due(r["Due"])
        rows.append(r)
    return rows


def keep(row, p):
    if row["Applies to"] not in ("both", p["retiring_or_separating"]):
        return False
    if row["Branch"] != "all" and p["branch"] not in [b.strip() for b in row["Branch"].split(",")]:
        return False
    if row["Topic"] in FAMILY_TOPICS and not (p.get("spouse") or p.get("children", 0) > 0):
        return False
    return True


def first_sentence(text, limit=240):
    """First sentence of the item; adds the next sentence when the first is very short."""
    text = re.sub(r"\*\*", "", text)
    sents = re.findall(r".+?[.!?](?=\s|$)", text) or [text]
    s = sents[0].strip()
    if len(s) < 60 and len(sents) > 1:
        s = s + " " + sents[1].strip()
    return s if len(s) <= limit else s[:limit - 3].rstrip() + "..."


def urls(row):
    return re.findall(r"https?://[^\s;|]+", row.get("Source URL", ""))


def next_reminder(p, now):
    tz = ZoneInfo(p["timezone"])
    hh, mm = map(int, p["reminder_time"].split(":"))
    cad = p["reminder_cadence"]

    def at(d):
        return datetime.datetime(d.year, d.month, d.day, hh, mm, tzinfo=tz)

    if cad == "daily":
        d = now.date()
        return at(d) if at(d) > now else at(d + datetime.timedelta(days=1))
    wd = DAYS.index(p["reminder_day"].lower())
    if cad == "weekly":
        d = now.date() + datetime.timedelta(days=(wd - now.weekday()) % 7)
        return at(d) if at(d) > now else at(d + datetime.timedelta(days=7))
    if cad == "biweekly":
        try:
            anchor = datetime.date.fromisoformat(str(p.get("saved_on")))
        except ValueError:
            anchor = now.date()
        anchor += datetime.timedelta(days=(wd - anchor.weekday()) % 7)
        d = anchor
        while at(d) <= now:
            d += datetime.timedelta(days=14)
        return at(d)
    # monthly: first <reminder_day> of each month
    y, m = now.year, now.month
    for _ in range(3):
        first = datetime.date(y, m, 1)
        d = first + datetime.timedelta(days=(wd - first.weekday()) % 7)
        if at(d) > now:
            return at(d)
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def fmt_window(row, sep):
    a, b = row["window"]
    da, db = offset_date(sep, a), offset_date(sep, b)
    return (f"{da.isoformat()}" if a == b else f"{da.isoformat()} to {db.isoformat()}"), da, db


def show(row, sep, today, extra=""):
    when, da, db = fmt_window(row, sep)
    flag = "  [UNVERIFIED: confirm before relying on it]" if row["Status"] == "UNVERIFIED" else ""
    print(f"- {when}{extra}  [{row['ID']}] {row['Topic']}{flag}")
    print(textwrap.fill(first_sentence(row["Item"]), width=100, initial_indent="    ", subsequent_indent="    "))
    print(textwrap.fill("Rule: " + row["Rule / deadline / number"], width=100, initial_indent="    ", subsequent_indent="      "))
    if row["ID"] in NOTES:
        print(textwrap.fill("Note: " + NOTES[row["ID"]], width=100, initial_indent="    ", subsequent_indent="      "))
    for u in urls(row) or ["(no official source confirmed)"]:
        print(f"    Source: {u}")


def main():
    ap = argparse.ArgumentParser(description="Show transition deadlines for your profile.")
    ap.add_argument("--profile", default=os.path.join(HERE, "profile.json"))
    ap.add_argument("--checklist", default=os.path.join(HERE, "MASTER_CHECKLIST.md"))
    ap.add_argument("--days", type=int, default=None, help="look-ahead window in days (default: profile lookahead_days, else 30)")
    ap.add_argument("--today", default=None, help="pretend today is YYYY-MM-DD (for testing)")
    ap.add_argument("--plan", action="store_true", help="print the full filtered checklist grouped by bucket")
    ap.add_argument("--perks", action="store_true", help="list perks you can claim now or within the look-ahead, plus any-time perks")
    a = ap.parse_args()

    p = load_profile(a.profile)
    tz = ZoneInfo(p["timezone"])
    if a.today:
        today = datetime.date.fromisoformat(a.today)
        now = datetime.datetime(today.year, today.month, today.day, tzinfo=tz)
    else:
        now = datetime.datetime.now(tz)
        today = now.date()
    days = a.days if a.days is not None else p["lookahead_days"]
    sep = p["separation_date"]
    to_sep = (sep - today).days

    rows = [r for r in load_rows(a.checklist) if keep(r, p)]
    print(f"Transition deadlines for {p.get('name') or 'you'}: {p['branch']}, {p['retiring_or_separating']}, "
          f"separation date {sep.isoformat()} "
          + (f"({to_sep} days from today)." if to_sep >= 0 else f"({-to_sep} days ago)."))
    print(f"Today: {today.isoformat()} ({p['timezone']}). Rows that apply to you: {len(rows)}.")
    nr = next_reminder(p, now)
    day_txt = "" if p["reminder_cadence"] == "daily" else f" on {p['reminder_day'].capitalize()}"
    if p["reminder_cadence"] == "monthly":
        day_txt = f" on the first {p['reminder_day'].capitalize()} of each month"
    print(f"Reminder preference: {p['reminder_cadence']}{day_txt} at {p['reminder_time']} {p['timezone']}; "
          f"next reminder {nr.strftime('%Y-%m-%d %H:%M %Z')}. Look-ahead: {days} days.")
    print("This is a planning aid, not legal advice. Confirm each item with the linked source and your offices.\n")

    end = today + datetime.timedelta(days=days)
    if a.perks:
        perks = load_perks(a.checklist)
        open_dated, opening, anytime, closed = classify_perks(perks, sep, today, end)
        print("Free and discounted perks (no branch or status filter; pick the ones that fit your plans).")
        print("Read each provider's full terms before you sign up.\n")
        print("1) Claim window open now:")
        if not open_dated:
            print("   None.")
        for _, extra, r in sorted(open_dated, key=lambda x: x[0]):
            show_perk(r, sep, extra)
        print()
        print(f"2) Claim window opens in the next {days} days:")
        if not opening:
            print("   None.")
        for _, extra, r in sorted(opening, key=lambda x: x[0]):
            show_perk(r, sep, extra)
        print()
        print("3) No time limit stated (available any time you qualify):")
        if not anytime:
            print("   None.")
        for _, extra, r in anytime:
            show_perk(r, sep, extra)
        print()
        later = sorted((perk_dates(r, sep)[0], r["ID"]) for r in perks
                       if perk_dates(r, sep)[0] is not None and perk_dates(r, sep)[0] > end)
        if later:
            print("Opening later: " + "; ".join(f"[{i}] from {d.isoformat()}" for d, i in later) + ".")
        print(f"{closed} perk window(s) have already closed.")
        return

    if a.plan:
        buckets = []
        for r in rows:
            if r["bucket"] not in buckets:
                buckets.append(r["bucket"])
        far = datetime.date.max
        for b in buckets:
            print(f"== {b} ==")
            in_b = [r for r in rows if r["bucket"] == b]
            in_b.sort(key=lambda r: (far, far) if r["window"] is None else fmt_window(r, sep)[1:])
            for r in in_b:
                if r["window"] is None:
                    flag = "  [UNVERIFIED]" if r["Status"] == "UNVERIFIED" else ""
                    print(f"- no fixed date  [{r['ID']}] {r['Topic']}{flag}")
                    print(textwrap.fill(first_sentence(r["Item"]), width=100, initial_indent="    ", subsequent_indent="    "))
                    print(textwrap.fill("Rule: " + r["Rule / deadline / number"], width=100, initial_indent="    ", subsequent_indent="      "))
                    if r["ID"] in NOTES:
                        print(textwrap.fill("Note: " + NOTES[r["ID"]], width=100, initial_indent="    ", subsequent_indent="      "))
                    for u in urls(r) or ["(no official source confirmed)"]:
                        print(f"    Source: {u}")
                else:
                    show(r, sep, today)
            print()
        return

    due, late, closed, undated = [], [], 0, 0
    for r in rows:
        if r["window"] is None:
            undated += 1
            continue
        _, da, db = fmt_window(r, sep)
        if da <= end and db >= today:
            due.append((da, r))
        elif db < today:
            # Pre-separation items are still actionable until the separation date.
            if r["window"][1] <= 0 and today < sep:
                late.append((db, r))
            else:
                closed += 1

    print(f"1) Due in the next {days} days ({today.isoformat()} to {end.isoformat()}):")
    if not due:
        print("   Nothing with a fixed date falls in this window.")
    for da, r in sorted(due, key=lambda x: x[0]):
        _, da, db = fmt_window(r, sep)
        if da == db:
            extra = (" (today)" if da == today else f" (in {(da - today).days} days)") if da >= today else ""
        elif da > today:
            extra = f" (opens in {(da - today).days} days)"
        else:
            extra = f" (open now; closes in {(db - today).days} days)"
        show(r, sep, today, extra)
    print()
    print("2) Past the recommended date but still possible before your separation date (if not already done,\n   look at these soon; some need a waiver, a late request, or extra service, so read each row):")
    if not late:
        print("   None.")
    for db, r in sorted(late, key=lambda x: x[0]):
        show(r, sep, today, f" (passed {(today - db).days} days ago)")
    print()
    print(f"{undated} rows have no fixed date and {closed} rows with dates have already closed. "
          f"Run with --plan to see your full list.")
    open_dated, opening, _, _ = classify_perks(load_perks(a.checklist), sep, today, end)
    closing = [x for x in open_dated if x[2]["window"][1] is not None and x[0] <= end]
    if opening or closing:
        print()
        print(f"3) Perks whose claim window opens or closes in the next {days} days (run with --perks for all perks):")
        for _, extra, r in sorted(opening + closing, key=lambda x: x[0]):
            show_perk(r, sep, extra)


if __name__ == "__main__":
    main()
