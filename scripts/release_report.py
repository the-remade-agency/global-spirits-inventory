#!/usr/bin/env python3
"""Diff the current build against the last published release.

The quarterly maintenance run discovers new bottlings in the vault; this turns
the rebuilt public CSV into the numbers that go out with the release: GitHub
release notes, the vault's quarterly digest, and the figures the website reads
from the manifest.

    python3 scripts/release_report.py                 # vs the latest tag
    python3 scripts/release_report.py --since v2026.10
    python3 scripts/release_report.py --out notes.md

Rows are matched on the identity tuple the collection spec declares as the
upsert key. A row whose key is unchanged but whose fields moved is reported as
revised rather than as a removal plus an addition, because a release note that
says "412 added, 400 removed" when 400 bottles had a proof corrected is worse
than no note.
"""

import argparse
import collections
import csv
import io
import re
import subprocess
import sys

# The collection spec's upsert key. Distillery and spirit type join it here:
# the spec's tuple is unique within a cohort, and this diff runs across all 288.
KEY = ("spirit_type", "distillery", "spirit_name", "special_designation",
       "age_statement", "vintage", "batch_lot")

CSV_PATH = "data/spirits_inventory.csv"

# Changes to these are noise in a release note: they move on almost every row
# whenever a maintenance pass touches it, and say nothing about the bottle.
IGNORE_IN_DIFF = {"last_verified", "source_urls", "label_image_url"}


def norm_distillery(name):
    """Fold the capitalisation and punctuation variants KNOWN_GAPS lists."""
    return re.sub(r"[^a-z0-9]", "", name.casefold())


def git(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True)


def latest_tag():
    r = git("describe", "--tags", "--abbrev=0")
    return r.stdout.strip() if r.returncode == 0 else None


def read_at(ref):
    """The CSV as it stood at a git ref, or None if it wasn't there."""
    if ref is None:
        return None
    r = git("show", f"{ref}:{CSV_PATH}")
    if r.returncode != 0:
        return None
    return list(csv.DictReader(io.StringIO(r.stdout)))


def read_now():
    with open(CSV_PATH, newline="") as fh:
        return list(csv.DictReader(fh))


def key_of(row):
    return tuple((row.get(k) or "").strip() for k in KEY)


def totals(rows):
    names = {r["distillery"].strip() for r in rows if r.get("distillery", "").strip()}
    sourced = sum(1 for r in rows if (r.get("source_urls") or "").strip())
    return {
        "rows": len(rows),
        "distilleries": len({norm_distillery(n) for n in names}),
        "distillery_strings": len(names),
        "spirit_types": len({r["spirit_type"].strip() for r in rows if r.get("spirit_type", "").strip()}),
        "cohorts": len({r["cohort"] for r in rows if r.get("cohort")}),
        "sourced_pct": round(100.0 * sourced / len(rows), 1) if rows else 0.0,
    }


def delta(new, old, key, fmt="{:+,}"):
    if old is None:
        return ""
    d = new[key] - old[key]
    return "  (no change)" if d == 0 else "  " + fmt.format(d)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", help="git ref to compare against (default: latest tag)")
    ap.add_argument("--out", help="write markdown here instead of stdout")
    a = ap.parse_args()

    ref = a.since or latest_tag()
    now = read_now()
    before = read_at(ref)

    if ref and before is None:
        print(f"warning: no {CSV_PATH} at {ref}; reporting current totals only",
              file=sys.stderr)
        ref = None

    t_now = totals(now)
    t_old = totals(before) if before else None

    out = io.StringIO()
    w = out.write

    if ref:
        w(f"Changes since **{ref}**.\n\n")
    else:
        w("First published release. No previous build to compare against.\n\n")

    w("| | Now | Change |\n| --- | ---: | ---: |\n")
    for label, k in (("Rows", "rows"), ("Distilleries", "distilleries"),
                     ("Spirit types", "spirit_types"), ("Cohorts", "cohorts")):
        w(f"| {label} | {t_now[k]:,} | {delta(t_now, t_old, k).strip() or '--'} |\n")
    pct = f"{t_now['sourced_pct']}%"
    chg = f"{t_now['sourced_pct'] - t_old['sourced_pct']:+.1f} pts" if t_old else "--"
    w(f"| Rows citing a source | {pct} | {chg} |\n\n")

    if before:
        old_by = {key_of(r): r for r in before}
        new_by = {key_of(r): r for r in now}
        added = [new_by[k] for k in new_by.keys() - old_by.keys()]
        removed = [old_by[k] for k in old_by.keys() - new_by.keys()]

        fields = [f for f in now[0].keys() if f not in IGNORE_IN_DIFF]
        revised, churn = [], collections.Counter()
        for k in new_by.keys() & old_by.keys():
            moved = [f for f in fields
                     if (new_by[k].get(f) or "").strip() != (old_by[k].get(f) or "").strip()]
            if moved:
                revised.append(new_by[k])
                churn.update(moved)

        w(f"**{len(added):,} added, {len(removed):,} removed, "
          f"{len(revised):,} revised in place.**\n\n")

        if added:
            w("New rows by spirit type:\n\n| Spirit type | Rows |\n| --- | ---: |\n")
            for t, c in collections.Counter(r["spirit_type"] for r in added).most_common():
                w(f"| {t} | {c:,} |\n")
            w("\n")

            old_names = {norm_distillery(r["distillery"].strip()) for r in before}
            fresh = sorted({r["distillery"].strip() for r in added
                            if norm_distillery(r["distillery"].strip()) not in old_names})
            if fresh:
                w(f"Distilleries appearing for the first time ({len(fresh)}): ")
                w(", ".join(fresh[:25]) + (", ..." if len(fresh) > 25 else "") + "\n\n")

        if churn:
            w("Fields corrected on existing rows:\n\n| Field | Rows |\n| --- | ---: |\n")
            for f, c in churn.most_common(12):
                w(f"| `{f}` | {c:,} |\n")
            w("\n")

        if removed:
            w(f"Rows removed ({len(removed):,}). Removals are deletions of "
              "duplicates or of entries that could not be substantiated; see "
              "`KNOWN_GAPS.md` for the standing list.\n\n")

    text = out.getvalue()
    if a.out:
        with open(a.out, "w") as fh:
            fh.write(text)
        print(f"wrote {a.out}")
    else:
        sys.stdout.write(text)


if __name__ == "__main__":
    main()
