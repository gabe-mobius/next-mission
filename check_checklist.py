#!/usr/bin/env python3
"""Checks sourcing and tagging rules in MASTER_CHECKLIST.md.

Usage:  python3 check_checklist.py [path/to/MASTER_CHECKLIST.md]
With no argument it checks MASTER_CHECKLIST.md in the same folder as this script.

Fails (exit code 1) and lists the offending rows if:
  * a row's Status is not exactly `sourced` or `UNVERIFIED`;
  * a `sourced` row has an empty Source URL, any URL that is not allowed for
    that row, an empty quote/value, or an empty/invalid Date checked
    (must be a real YYYY-MM-DD date, not in the future);
  * a main-section table lacks the 'Applies to', 'Branch', or 'Due' column, or
    a row has an invalid value in one of them:
      Applies to: exactly one of retiring, separating, both
      Branch:     `all`, or a comma list of army, navy, marine-corps,
                  air-force, space-force, coast-guard
      Due:        `none`, a whole number of days (e.g. -365, 0, +180), or a
                  window `A..B` with A <= B (e.g. -180..-90)
  * a `sourced` row in the perks section has an empty 'Who qualifies' cell;
  * the perks table lacks the 'Who qualifies' or 'Window' column, or a perk row
    has an invalid Window. Window is `any`, or `A..B` where A and B are whole
    numbers of days relative to the separation date (multiples of 365 mean
    calendar years) and either side may be `any` (e.g. -365..+365, -180..0,
    any..+365), with A <= B and not `any..any`;
  * a row whose Topic mentions move, HHG, household goods, travel, or storage
    is UNVERIFIED and its Item text lacks the exact sentence
    'Confirm this with your installation transportation office.';
  * a table row has the wrong number of cells;
  * a table lacks the 'ID' column, or an ID is missing, malformed (lowercase
    letters, digits and hyphens), or used twice;
  * the Change log 'Value changes (old -> new)' table is missing or invalid:
      - Date must be a real YYYY-MM-DD date, not in the future;
      - Field must be one of LOG_FIELDS; Old and New must differ;
      - the first entry for a Row ID + Field may use Old `(new row)`; every
        later entry's Old value must equal the previous entry's New value;
      - the newest New value must equal the row's current cell (so an edit
        that was not logged, or a log that contradicts the table, fails);
        if the newest New value is `(removed)`, the row must not exist.

Source URL rules (a cell may hold several URLs, e.g. "(1) https://a ; (2) https://b"):
  * Every section: CORE_DOMAINS (and their subdomains).
  * Every section: the one JTR PDF URL in ALLOWED_EXACT_URLS (media.defense.gov
    is otherwise NOT allowed).
  * Main sections, only for rows whose Branch is not `all`: the branches' own
    official sites in BRANCH_DOMAINS (and their subdomains).
  * Perks section ('Free and discounted perks ...'): also any .mil or .gov
    domain, or a provider's own domain listed in PERK_PROVIDER_DOMAINS. Add a
    provider only after confirming the URL is that organization's own offer
    page (never a blog, coupon or news site).
Prints counts for the main checklist and the perks section, and per 'Applies to'.
"""
import os, re, sys, datetime
from urllib.parse import urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "MASTER_CHECKLIST.md")
CORE_DOMAINS = ["va.gov", "benefits.va.gov", "dodtap.mil", "skillbridge.osd.mil", "tricare.mil",
                "tsp.gov", "militaryonesource.mil", "move.mil", "travel.dod.mil"]
ALLOWED_EXACT_URLS = {"https://media.defense.gov/2022/jan/04/2002917147/-1/-1/0/jtr.pdf"}
BRANCH_DOMAINS = ["army.mil", "hrc.army.mil", "navy.mil", "mynavyhr.navy.mil", "marines.mil",
                  "af.mil", "afpc.af.mil", "spaceforce.mil", "uscg.mil"]
PERK_PROVIDER_DOMAINS = [
    "linkedin.com",          # LinkedIn
    "microsoft.com",         # Microsoft (MSSA)
    "salesforce.com",        # Salesforce (Trailhead / Salesforce Military)
    "syracuse.edu",          # Syracuse University IVMF (Onward to Opportunity)
    "acp-usa.org",           # American Corporate Partners
    "hireheroesusa.org",     # Hire Heroes USA
    "hiringourheroes.org",   # Hiring Our Heroes
    "grow.google",           # Google (Grow with Google)
    "openai.com",            # OpenAI (ChatGPT Plus for service members and veterans; includes help.openai.com)
    "chatgpt.com",           # OpenAI (chatgpt.com/veterans-claim offer page)
]
PERKS_HEADING = "free and discounted perks"
VALID_STATUS = {"sourced", "UNVERIFIED"}
VALID_APPLIES = {"retiring", "separating", "both"}
VALID_BRANCHES = {"army", "navy", "marine-corps", "air-force", "space-force", "coast-guard"}
LOG_SECTION = "value changes"
LOG_COLS = ["Date", "Row ID", "Field", "Old value", "New value", "Source URL", "Note"]
LOG_FIELDS = {"Rule / deadline / number", "Due", "Applies to", "Branch", "Status", "Window"}
ID_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
MAIN_REQUIRED_COLS = ["#", "ID", "Item", "Topic", "Applies to", "Branch", "Due", "Rule / deadline / number",
                      "Source URL", "Source quote or value", "Date checked", "Status"]
DUE_RE = re.compile(r"^(none|[+-]?\d+|[+-]?\d+\.\.[+-]?\d+)$")
PERKS_REQUIRED_COLS = ["Who qualifies", "Window"]
WINDOW_RE = re.compile(r"^(any|(any|[+-]?\d+)\.\.(any|[+-]?\d+))$")
MOVE_TOPIC_RE = re.compile(r"\bmov(e|es|ed|ing)\b|\bhhg\b|household goods|\btravel|\bstorage\b", re.I)
TRANSPORT_SENTENCE = "Confirm this with your installation transportation office."
URL_RE = re.compile(r"https?://[^\s;|]+")
TODAY = datetime.date.today()

def on_domain(host, domains):
    host = (host or "").lower().rstrip(".")
    return any(host == d or host.endswith("." + d) for d in domains)

def url_ok(url, perks, branch_specific):
    if url in ALLOWED_EXACT_URLS:
        return True, ""
    p = urlparse(url)
    if p.scheme not in ("https", "http") or not p.netloc:
        return False, "not a full http(s) URL"
    host = p.hostname or ""
    if on_domain(host, CORE_DOMAINS):
        return True, ""
    if branch_specific and not perks and on_domain(host, BRANCH_DOMAINS):
        return True, ""
    if perks and (host.endswith(".mil") or host.endswith(".gov") or on_domain(host, PERK_PROVIDER_DOMAINS)):
        return True, ""
    if on_domain(host, BRANCH_DOMAINS):
        return False, f"branch site '{host}' is only allowed on rows whose Branch is not 'all'"
    return False, f"domain '{host}' not allowed in this section"

def split_row(line):
    s = line.strip()
    if s.startswith("|"): s = s[1:]
    if s.endswith("|"): s = s[:-1]
    return [c.strip() for c in s.split("|")]

def check_due(due):
    if not DUE_RE.match(due):
        return False
    if ".." in due:
        a, b = (int(x) for x in due.split(".."))
        return a <= b
    return True

def check_window(w):
    if not WINDOW_RE.match(w) or w == "any..any":
        return False
    if ".." in w:
        a, b = w.split("..")
        if a != "any" and b != "any":
            return int(a) <= int(b)
    return True

def norm(v):
    return re.sub(r"\s+", " ", v).strip()

def valid_date(d):
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", d):
        return False
    try:
        return datetime.date.fromisoformat(d) <= TODAY
    except ValueError:
        return False

def check_log(log_rows, table_rows, errors):
    """log_rows: list of (line_no, dict). table_rows: {id: dict of current cells}."""
    if not log_rows:
        errors.append("Change log: 'Value changes (old -> new)' table is missing or empty")
        return
    last = {}
    for n, e in log_rows:
        rid = f"line {n} [Change log {e.get('Row ID', '?')}]"
        if not valid_date(e.get("Date", "")):
            errors.append(f"{rid}: invalid or future Date '{e.get('Date', '')}'")
        if e.get("Field") not in LOG_FIELDS:
            errors.append(f"{rid}: Field must be one of {sorted(LOG_FIELDS)} (got '{e.get('Field')}')")
            continue
        old, new = norm(e.get("Old value", "")), norm(e.get("New value", ""))
        if not old or not new or old == new:
            errors.append(f"{rid}: Old value and New value must both be filled in and must differ")
        key = (e.get("Row ID", ""), e["Field"])
        if key in last:
            if old != last[key]:
                errors.append(f"{rid}: Old value '{old}' does not match the previous New value '{last[key]}' "
                              f"for {key[0]} / {key[1]} (contradiction in the log)")
        last[key] = new
    for (row_id, field), new in last.items():
        if new == "(removed)":
            if row_id in table_rows:
                errors.append(f"Change log: {row_id} is logged as removed but still exists in the checklist")
            continue
        if row_id not in table_rows:
            errors.append(f"Change log: Row ID '{row_id}' is not in the checklist (log it as '(removed)' or fix the ID)")
            continue
        cur = norm(table_rows[row_id].get(field, ""))
        if cur != new:
            errors.append(f"Change log contradiction: {row_id} / {field} is '{cur}' in the checklist, "
                          f"but the newest logged New value is '{new}'. Log the change (old -> new) or fix the row.")

def main():
    lines = open(PATH, encoding="utf-8").read().splitlines()
    section, header, errors = "", None, []
    table_rows, ids_seen, log_rows = {}, set(), []
    counts = {"main": {"total": 0, "sourced": 0, "UNVERIFIED": 0},
              "perks": {"total": 0, "sourced": 0, "UNVERIFIED": 0}}
    applies_counts = {k: 0 for k in sorted(VALID_APPLIES)}
    for n, line in enumerate(lines, 1):
        if line.startswith("#"):
            section, header = line.lstrip("#").strip(), None
            continue
        if not line.strip().startswith("|"):
            header = None
            continue
        cells = split_row(line)
        perks = PERKS_HEADING in section.lower()
        is_log = LOG_SECTION in section.lower()
        if header is None:
            header = cells
            if is_log:
                if header != LOG_COLS:
                    errors.append(f"line {n}: Change log table header must be {LOG_COLS}")
                continue
            if "ID" not in header:
                errors.append(f"line {n} [{section}]: table header missing required 'ID' column")
            if "Status" not in header or "#" not in header:
                errors.append(f"line {n}: table header missing '#' or 'Status' column: {header}")
            required = PERKS_REQUIRED_COLS if perks else MAIN_REQUIRED_COLS
            missing = [c for c in required if c not in header]
            if missing:
                errors.append(f"line {n} [{section}]: table header missing required column(s): {missing}")
            continue
        if all(re.fullmatch(r":?-{3,}:?", c) for c in cells):
            continue  # separator row
        if is_log:
            if len(cells) != len(header):
                errors.append(f"line {n} [Change log]: has {len(cells)} cells, header has {len(header)}")
            else:
                log_rows.append((n, dict(zip(header, cells))))
            continue
        bucket = "perks" if perks else "main"
        rid = f"line {n} [{section} #{cells[0] if cells else '?'}]"
        if len(cells) != len(header):
            errors.append(f"{rid}: has {len(cells)} cells, header has {len(header)}")
            continue
        row = dict(zip(header, cells))
        counts[bucket]["total"] += 1
        row_id = row.get("ID", "")
        if not ID_RE.match(row_id):
            errors.append(f"{rid}: missing or malformed ID '{row_id}'")
        elif row_id in ids_seen:
            errors.append(f"{rid}: duplicate ID '{row_id}'")
        else:
            ids_seen.add(row_id)
            table_rows[row_id] = row
        status = row.get("Status", "")

        branch_specific = False
        if not perks:
            applies = row.get("Applies to", "")
            if applies not in VALID_APPLIES:
                errors.append(f"{rid}: 'Applies to' must be retiring, separating, or both (got '{applies}')")
            else:
                applies_counts[applies] += 1
            branch = row.get("Branch", "")
            if branch != "all":
                parts = [b.strip() for b in branch.split(",")]
                if not branch or any(p not in VALID_BRANCHES for p in parts) or len(set(parts)) != len(parts):
                    errors.append(f"{rid}: invalid Branch '{branch}'")
                else:
                    branch_specific = True
            if not check_due(row.get("Due", "")):
                errors.append(f"{rid}: invalid Due '{row.get('Due', '')}' (use none, -365, +180, 0, or A..B)")
        elif not check_window(row.get("Window", "")):
            errors.append(f"{rid}: invalid Window '{row.get('Window', '')}' (use any, -365..+365, -180..0, or any..+365)")

        if status not in VALID_STATUS:
            errors.append(f"{rid}: Status must be exactly 'sourced' or 'UNVERIFIED' (got '{status}')")
            continue
        counts[bucket][status] += 1
        if (status == "UNVERIFIED" and MOVE_TOPIC_RE.search(row.get("Topic", ""))
                and TRANSPORT_SENTENCE not in row.get("Item", "")):
            errors.append(f"{rid}: UNVERIFIED move/travel/HHG/storage row must say "
                          f"'{TRANSPORT_SENTENCE}' in its Item text")
        if status != "sourced":
            continue
        url_cell = row.get("Source URL", "")
        urls = URL_RE.findall(url_cell)
        if not url_cell or not urls:
            errors.append(f"{rid}: sourced row has empty or unreadable Source URL")
        for url in urls:
            ok, why = url_ok(url, perks, branch_specific)
            if not ok:
                errors.append(f"{rid}: {why} ({url})")
        if not row.get("Source quote or value", ""):
            errors.append(f"{rid}: sourced row has empty Source quote or value")
        d = row.get("Date checked", "")
        try:
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", d):
                raise ValueError
            if datetime.date.fromisoformat(d) > TODAY:
                errors.append(f"{rid}: Date checked '{d}' is in the future")
        except ValueError:
            errors.append(f"{rid}: sourced row has empty or invalid Date checked '{d}'")
        if perks and not row.get("Who qualifies", ""):
            errors.append(f"{rid}: perks row has empty 'Who qualifies'")

    check_log(log_rows, table_rows, errors)
    m, p = counts["main"], counts["perks"]
    print(f"Main checklist: total items: {m['total']}, sourced: {m['sourced']}, unverified: {m['UNVERIFIED']}")
    print(f"Perks section:  total items: {p['total']}, sourced: {p['sourced']}, unverified: {p['UNVERIFIED']}")
    print(f"All items:      total items: {m['total']+p['total']}, sourced: {m['sourced']+p['sourced']}, "
          f"unverified: {m['UNVERIFIED']+p['UNVERIFIED']}")
    print("Main checklist by 'Applies to': " + ", ".join(f"{k}: {v}" for k, v in applies_counts.items()))
    print(f"Change log value entries: {len(log_rows)}")
    if errors:
        print(f"\nFAIL: {len(errors)} problem(s):")
        for e in errors:
            print("  - " + e)
        sys.exit(1)
    print("\nPASS: every row has a valid status and tags, and every sourced row has allowed URL(s), a quote, and a valid date.")

if __name__ == "__main__":
    main()
