#!/usr/bin/env python3
"""Checks the sourcing rules in STATE_BENEFITS.md.

Usage:  python3 check_state_benefits.py [path/to/STATE_BENEFITS.md]

The script exits with a non-zero code and lists the offending rows if:
  * a table row does not have exactly 8 cells;
  * a row's Status is not exactly `sourced` or `UNVERIFIED`;
  * a `sourced` row has an empty Source URL, a URL that is not http(s), or a
    URL whose host is not on an allowed domain (see below);
  * a `sourced` row has an empty "Source quote or value" cell;
  * a `sourced` row has a missing or invalid "Date checked" (it must be a real
    calendar date in YYYY-MM-DD form and not in the future).
It also checks that every UNVERIFIED row still has a valid date, and it prints
counts (sourced / UNVERIFIED / total) for each state section.

Allowed domains for `sourced` rows (a host matches a domain if it is that
domain or any subdomain of it):
  * STATE_GOV_DOMAINS: official state government .gov domains.
  * Any host ending in .state.XX.us, where XX is a two-letter state code.
  * va.gov (U.S. Department of Veterans Affairs).
  * EXTRA_OFFICIAL_DOMAINS: other official state agency domains, each with a
    comment saying why it is official. Add a domain here only after you have
    confirmed it is the state agency's own site (ideally because a page on the
    state's .gov domain links to it). Never add blogs, news, law-firm, or
    commercial benefit-guide sites.

A section is a "## " heading. Rows are counted under the most recent heading.
"""
import datetime
import re
import sys
from urllib.parse import urlparse

PATH = sys.argv[1] if len(sys.argv) > 1 else "/home/box/transition/STATE_BENEFITS.md"

# Official state government .gov domains. Add a state's main domain(s) here
# when you add that state to STATE_BENEFITS.md.
STATE_GOV_DOMAINS = [
    "texas.gov",      # State of Texas (tvc., comptroller., dps., tpwd., glo., gov., tcss.legis. ...)
    "oklahoma.gov",   # State of Oklahoma (veterans, tax, service, omes ...)
    "ok.gov",         # State of Oklahoma's older official .gov domain
]

FEDERAL_DOMAINS = [
    "va.gov",         # U.S. Department of Veterans Affairs (incl. department.va.gov, benefits.va.gov)
]

# Other official state agency domains that are not on a .gov domain.
EXTRA_OFFICIAL_DOMAINS = [
    # Oklahoma State Regents for Higher Education (the state's coordinating
    # board for public colleges). The Regents' own official publication (the
    # 2026-27 Counselors' Resource Book) says it is "issued by the Oklahoma
    # State Regents for Higher Education, as authorized by 70 O.S. 2001,
    # Section 3206" and that copies "are available through the agency website
    # at www.okhighered.org."
    "okhighered.org",
    # Oklahoma Department of Wildlife Conservation, a constitutional state
    # agency (see https://oklahoma.gov/top/agency/320.html). Service Oklahoma's
    # own oklahoma.gov link-exit page for fishing licenses links to
    # https://www.wildlifedepartment.com/fishing/resources.
    "wildlifedepartment.com",
    # Oklahoma Legislature's official bill-tracking site (used only for bill
    # status, never as a benefit source on its own).
    "oklegislature.gov",
]

STATE_US_RE = re.compile(r"(^|\.)state\.[a-z]{2}\.us$")
STATUSES = {"sourced", "UNVERIFIED"}
HEADER = ["#", "Benefit", "Who qualifies", "Rule / amount / deadline", "Source URL",
          "Source quote or value", "Date checked", "Status"]


def host_allowed(host):
    host = host.lower().rstrip(".")
    if host.startswith("www."):
        host = host[4:]
    if STATE_US_RE.search(host):
        return True
    for d in STATE_GOV_DOMAINS + FEDERAL_DOMAINS + EXTRA_OFFICIAL_DOMAINS:
        if host == d or host.endswith("." + d):
            return True
    return False


def valid_date(s):
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        return False
    try:
        d = datetime.date.fromisoformat(s)
    except ValueError:
        return False
    return d <= datetime.date.today()


def split_row(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def main():
    problems = []
    counts = {}
    order = []
    section = None
    in_table = False
    with open(PATH, encoding="utf-8") as f:
        lines = f.readlines()
    for n, line in enumerate(lines, 1):
        if line.startswith("## "):
            section = line[3:].strip()
            in_table = False
            continue
        if not line.lstrip().startswith("|"):
            in_table = False
            continue
        cells = split_row(line)
        if cells == HEADER:
            in_table = True
            if section not in counts:
                counts[section] = {"sourced": 0, "UNVERIFIED": 0}
                order.append(section)
            continue
        if all(re.fullmatch(r":?-{3,}:?", c) for c in cells):
            continue
        if not in_table:
            problems.append(f"line {n}: table row outside a recognized benefits table")
            continue
        label = f"{section} row {cells[0] if cells else '?'} (line {n})"
        if len(cells) != 8:
            problems.append(f"{label}: expected 8 cells, found {len(cells)}")
            continue
        num, benefit, who, rule, url, quote, date, status = cells
        if status not in STATUSES:
            problems.append(f"{label}: Status must be exactly `sourced` or `UNVERIFIED`, found '{status}'")
            continue
        counts[section][status] += 1
        if not valid_date(date):
            problems.append(f"{label}: Date checked '{date}' is not a valid YYYY-MM-DD date (or is in the future)")
        if status == "sourced":
            if not url:
                problems.append(f"{label}: sourced row has no Source URL")
            else:
                p = urlparse(url)
                if p.scheme not in ("http", "https") or not p.hostname:
                    problems.append(f"{label}: Source URL '{url}' is not a valid http(s) URL")
                elif not host_allowed(p.hostname):
                    problems.append(f"{label}: Source URL host '{p.hostname}' is not on an allowed domain")
            if not quote:
                problems.append(f"{label}: sourced row has no Source quote or value")
            if not benefit:
                problems.append(f"{label}: sourced row has no Benefit")

    print("Counts per state section:")
    for s in order:
        c = counts[s]
        print(f"  {s}: sourced={c['sourced']} UNVERIFIED={c['UNVERIFIED']} total={c['sourced'] + c['UNVERIFIED']}")
    if not order:
        problems.append("no benefits tables found")
    if problems:
        print(f"\nFAILED: {len(problems)} problem(s):")
        for p in problems:
            print("  - " + p)
        sys.exit(1)
    print("\nPASSED: every sourced row has an allowed URL, a quote, and a valid date.")


if __name__ == "__main__":
    main()
