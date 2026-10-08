#!/usr/bin/env python3
"""List checklist rows that changed between the previous and current MASTER_CHECKLIST.md, by row ID.

Monthly check, in this folder:
  cp MASTER_CHECKLIST.md MASTER_CHECKLIST.prev.md && cp VERSION VERSION.prev
  (download the new MASTER_CHECKLIST.md and VERSION)
  python3 compare_versions.py            # changes that apply to profile.json
  python3 compare_versions.py --all      # every change, no profile filter
  python3 compare_versions.py --json     # machine-readable output

By default the script reads MASTER_CHECKLIST.prev.md, MASTER_CHECKLIST.md, VERSION.prev,
VERSION, and profile.json from the folder it lives in. Other paths: --old, --new, --profile.
--include-minor also shows quote, date-checked, and row-number changes.

Rows are matched by their ID column (IDs never change once published), so moved or
renumbered rows are not reported. Main-checklist rows are kept when 'Applies to' is 'both'
or matches the profile, 'Branch' is 'all' or lists the profile's branch, and GI Bill
transfer / Survivor Benefit Plan rows only when the profile has a spouse or children (the
same rules as deadlines.py). A changed row is reported if either its old or its new version
applies, so a row that stops applying is still mentioned. Perk rows have no branch or
status tags and are always reported. The Change log section is ignored (it is a record of
changes, not a rule).
"""
import argparse, datetime, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
FAMILY_TOPICS = ("GI Bill transfer (TEB)", "Retirement (SBP)")
MAJOR = ["Rule / deadline / number", "Due", "Window", "Applies to", "Branch", "Who qualifies",
         "Status", "Item", "Topic", "Source URL"]
MINOR = ["Source quote or value", "Date checked", "#"]
URL_RE = re.compile(r"https?://[^\s;|]+")


def parse(path):
    rows, h2, section, header = {}, "", "", None
    for n, line in enumerate(open(path, encoding="utf-8").read().splitlines(), 1):
        if line.startswith("#"):
            if re.match(r"#{1,2}\s", line):
                h2 = line.lstrip("#").strip()
            section, header = line.lstrip("#").strip(), None
            continue
        if not line.strip().startswith("|"):
            header = None
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if header is None:
            header = cells
            continue
        if all(re.fullmatch(r":?-{3,}:?", c) for c in cells):
            continue
        if h2.lower().startswith("change log") or "ID" not in header or len(cells) != len(header):
            continue
        r = dict(zip(header, cells))
        r["_section"], r["_line"], r["_perk"] = section, n, "Applies to" not in header
        rows[r["ID"]] = r
    return rows


def load_profile(path):
    if not path or not os.path.exists(path):
        return None
    p = json.load(open(path, encoding="utf-8"))
    p["branch"] = str(p.get("branch", "")).strip().lower().replace(" ", "-")
    p["retiring_or_separating"] = str(p.get("retiring_or_separating", "")).strip().lower()
    try:
        p["separation_date"] = datetime.date.fromisoformat(str(p.get("separation_date")))
    except ValueError:
        p["separation_date"] = None
    try:
        kids = int(p.get("children", 0) or 0)
    except (TypeError, ValueError):
        kids = 0
    p["family"] = bool(p.get("spouse")) or kids > 0
    return p


def applies(r, p):
    if r is None:
        return False
    if p is None or r["_perk"]:
        return True
    if r.get("Applies to") not in ("both", p["retiring_or_separating"]):
        return False
    if r.get("Branch") != "all" and p["branch"] not in [b.strip() for b in r.get("Branch", "").split(",")]:
        return False
    if r.get("Topic") in FAMILY_TOPICS and not p["family"]:
        return False
    return True


def offset_date(base, days):
    """Same rule as deadlines.py: whole multiples of 365 are calendar years."""
    if days and days % 365 == 0:
        y = base.year + days // 365
        try:
            return base.replace(year=y)
        except ValueError:
            return base.replace(year=y, day=28)
    return base + datetime.timedelta(days=days)


def dates_for(value, p):
    """'(for you: ...)' text for a Due or Window value, or ''."""
    if not p or not p.get("separation_date") or not value:
        return ""
    v = value.strip()
    if v in ("none", "any"):
        return ""
    parts = v.split("..") if ".." in v else [v, v]
    out = []
    for x in parts:
        if x == "any":
            out.append(None)
            continue
        try:
            out.append(offset_date(p["separation_date"], int(x)))
        except ValueError:
            return ""
    a, b = out
    if a == b:
        return f" (for you: {a.isoformat()})"
    if a is None:
        return f" (for you: until {b.isoformat()})"
    if b is None:
        return f" (for you: from {a.isoformat()})"
    return f" (for you: {a.isoformat()} to {b.isoformat()})"


def read(path):
    try:
        return open(path, encoding="utf-8").read().strip() or None
    except OSError:
        return None


def main():
    ap = argparse.ArgumentParser(description="List changed checklist rows by ID, old vs new, filtered by profile.")
    ap.add_argument("--old", default=os.path.join(HERE, "MASTER_CHECKLIST.prev.md"))
    ap.add_argument("--new", default=os.path.join(HERE, "MASTER_CHECKLIST.md"))
    ap.add_argument("--old-version", default=os.path.join(HERE, "VERSION.prev"))
    ap.add_argument("--new-version", default=os.path.join(HERE, "VERSION"))
    ap.add_argument("--profile", default=os.path.join(HERE, "profile.json"))
    ap.add_argument("--all", action="store_true", help="ignore the profile and list every change")
    ap.add_argument("--include-minor", action="store_true", help="also show quote, date-checked, and row-number changes")
    ap.add_argument("--json", action="store_true", help="print JSON instead of plain text")
    a = ap.parse_args()

    vo, vn = read(a.old_version), read(a.new_version)
    missing = [f for f in (a.old, a.new) if not os.path.exists(f)]
    if missing:
        msg = ("Nothing to compare: " + " and ".join(missing) + " not found. Before downloading a new "
               "checklist, copy MASTER_CHECKLIST.md to MASTER_CHECKLIST.prev.md and VERSION to VERSION.prev.")
        if a.json:
            print(json.dumps({"compared": False, "reason": msg, "version_old": vo, "version_new": vn, "changes": []}, indent=2))
        else:
            print(msg)
        return

    old, new = parse(a.old), parse(a.new)
    p = None if a.all else load_profile(a.profile)
    note = None
    if not a.all and p is None:
        note = f"No profile found at {a.profile}; showing every change."

    fields = MAJOR + (MINOR if a.include_minor else [])
    out = []
    for rid in sorted(set(old) | set(new), key=lambda i: (new.get(i) or old.get(i))["_line"]):
        o, n = old.get(rid), new.get(rid)
        if not (applies(o, p) or applies(n, p)):
            continue
        if o is None:
            out.append({"id": rid, "kind": "added", "section": n["_section"],
                        "new": {k: n[k] for k in MAJOR if k in n}})
            continue
        if n is None:
            out.append({"id": rid, "kind": "removed", "section": o["_section"],
                        "old": {k: o[k] for k in MAJOR if k in o}})
            continue
        # A column that exists in only one copy (for example a newly added column) is not a rule change.
        ch = [{"field": k, "old": o[k], "new": n[k]} for k in fields if k in o and k in n and o[k] != n[k]]
        if not ch:
            continue
        e = {"id": rid, "kind": "changed", "section": n["_section"], "topic": n.get("Topic", ""), "changes": ch,
             "also_updated": [k for k in MINOR if k not in fields and k in o and k in n and o[k] != n[k]],
             "applies_now": applies(n, p), "sources": URL_RE.findall(n.get("Source URL", ""))}
        if p is not None and not e["applies_now"]:
            e["note"] = "This row no longer applies to this profile."
        out.append(e)

    if a.json:
        print(json.dumps({"compared": True, "version_old": vo, "version_new": vn,
                          "version_changed": vo != vn, "filtered_by_profile": p is not None,
                          "note": note, "changes": out}, indent=2))
        return
    if note:
        print(note)
    print(f"VERSION: {vo or '(no VERSION.prev saved)'} -> {vn or '(no VERSION file)'}"
          + ("  (unchanged)" if vo and vo == vn else ""))
    scope = f"{p['branch']}, {p['retiring_or_separating']}" if p else "all rows"
    if not out:
        print(f"No rule changes that apply to this profile ({scope}).")
        return
    print(f"{len(out)} changed row(s) that apply to this profile ({scope}):\n")
    for e in out:
        if e["kind"] == "added":
            print(f"[{e['id']}] NEW ROW in '{e['section']}'")
            for k, v in e["new"].items():
                print(f"    {k}: {v}" + (dates_for(v, p) if k in ("Due", "Window") else ""))
        elif e["kind"] == "removed":
            print(f"[{e['id']}] REMOVED from '{e['section']}'")
            for k, v in e["old"].items():
                print(f"    was {k}: {v}")
        else:
            print(f"[{e['id']}] {e['topic']} ('{e['section']}')")
            for c in e["changes"]:
                xo = dates_for(c["old"], p) if c["field"] in ("Due", "Window") else ""
                xn = dates_for(c["new"], p) if c["field"] in ("Due", "Window") else ""
                print(f"    {c['field']}:\n      old: {c['old']}{xo}\n      new: {c['new']}{xn}")
            if e["also_updated"]:
                print(f"    (also updated: {', '.join(e['also_updated'])})")
            if e.get("note"):
                print(f"    {e['note']}")
            for u in e["sources"]:
                print(f"    Source: {u}")
        print()


if __name__ == "__main__":
    main()
