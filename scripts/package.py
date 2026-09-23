#!/usr/bin/env python3
"""Build the published dataset from the working research outputs.

Run this after each quarterly maintenance pass, then tag a release. The point of
a script rather than a copy is that the consolidated file and the per-cohort
files cannot drift: both are produced from one source in one pass.

    python3 scripts/package.py --src /path/to/inventory_research/_outputs
"""
import argparse, csv, glob, hashlib, json, os, re, sys
from datetime import date

# QA working files, not inventory. They carry their own schema (csv_file,
# row_index, recommended_is_template, reasoning) and describe rows in the other
# files rather than adding any.
EXCLUDE = {"bourbon_ndp_audit", "bourbon_template_audit"}

# The cohort is encoded only in the source filename. Consolidating without
# promoting it to a column silently loses the grouping that distinguishes, say,
# bourbon_kentucky_craft from bourbon_indiana.
COHORT_COL = "cohort"

# Held out of the public release. CC BY 4.0 grants downstream users the right to
# copy, adapt and commercialise the whole dataset, and that right cannot be
# granted over text we do not own. An audit on 2026-09-22 found 5,525 of 5,744
# notes carried no source tag and 679 contained full sentences, with producer
# marketing copy present verbatim (Tariquet Armagnac, checked against the
# producer's own page). Factual attributes are not copyrightable; that prose is.
#
# The column returns once a maintenance pass applies the rule now recorded in
# research_system_prompt.md: original descriptors only, never verbatim, source
# tag required.
DROP_FROM_PUBLIC = {"tasting_notes"}


def distillery_counts(rows):
    """Distinct distillery strings, and distinct distilleries after normalising
    case and punctuation. The two differ where one producer is spelled two ways;
    the normalised figure is the one quoted in the README."""
    names = {r["distillery"].strip() for r in rows if r.get("distillery", "").strip()}
    norm = {re.sub(r"[^a-z0-9]", "", n.casefold()) for n in names}
    return len(names), len(norm)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", default="data")
    a = ap.parse_args()

    files = [f for f in sorted(glob.glob(os.path.join(a.src, "*.csv")))
             if os.path.splitext(os.path.basename(f))[0] not in EXCLUDE]
    if not files:
        print("no source CSVs found", file=sys.stderr)
        return 1

    # Two passes. The first only reads headers, so a schema mismatch is caught
    # before anything is written. The original single pass wrote by_cohort files
    # as it went and checked drift at the end, which meant a refused build left
    # partial output on disk for the next run to trip over.
    header, drift = None, []
    for f in files:
        with open(f, newline="", encoding="utf-8-sig", errors="replace") as fh:
            fields = list(csv.DictReader(fh).fieldnames or [])
        if header is None:
            header = fields
        elif fields != header:
            drift.append(os.path.basename(f))
    if drift:
        print(f"REFUSING: {len(drift)} file(s) have a different schema: {drift}",
              file=sys.stderr)
        print("  nothing was written.", file=sys.stderr)
        return 1

    bycohort = os.path.join(a.out, "by_cohort")
    if os.path.isdir(bycohort):
        for stale in glob.glob(os.path.join(bycohort, "*.csv")):
            os.remove(stale)
    os.makedirs(bycohort, exist_ok=True)
    rows, cohorts, empty = [], [], []

    for f in files:
        cohort = os.path.splitext(os.path.basename(f))[0]
        with open(f, newline="", encoding="utf-8-sig", errors="replace") as fh:
            r = csv.DictReader(fh)
            n = 0
            for row in r:
                row[COHORT_COL] = cohort
                for c in DROP_FROM_PUBLIC:
                    row.pop(c, None)
                rows.append(row)
                n += 1
        if n == 0:
            # An empty cohort file is a collection gap, not a dataset member.
            # Shipping it makes the cohort count overstate coverage.
            empty.append(cohort)
            continue
        cohorts.append({"cohort": cohort, "rows": n})
        # per-cohort file, with the cohort column added so the two views match
        out_cols = [c for c in header if c not in DROP_FROM_PUBLIC] + [COHORT_COL]
        with open(os.path.join(a.out, "by_cohort", cohort + ".csv"), "w",
                  newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=out_cols)
            w.writeheader()
            with open(f, newline="", encoding="utf-8-sig", errors="replace") as src:
                for row in csv.DictReader(src):
                    row[COHORT_COL] = cohort
                    for c in DROP_FROM_PUBLIC:
                        row.pop(c, None)
                    w.writerow(row)

    out_cols = [c for c in header if c not in DROP_FROM_PUBLIC] + [COHORT_COL]
    consolidated = os.path.join(a.out, "spirits_inventory.csv")
    with open(consolidated, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=out_cols)
        w.writeheader()
        w.writerows(rows)

    digest = hashlib.sha256(open(consolidated, "rb").read()).hexdigest()
    n_raw, n_norm = distillery_counts(rows)
    n_types = len({r["spirit_type"].strip() for r in rows if r.get("spirit_type", "").strip()})
    manifest = {
        "built": date.today().isoformat(),
        "rows": len(rows),
        "cohorts": len(cohorts),
        "distillery_strings": n_raw,
        "distilleries": n_norm,
        "spirit_types": n_types,
        "columns": out_cols,
        "excluded_qa_files": sorted(EXCLUDE),
        "columns_withheld_from_public_release": sorted(DROP_FROM_PUBLIC),
        "empty_cohorts_dropped": sorted(empty),
        "sha256_spirits_inventory_csv": digest,
        "by_cohort": cohorts,
    }
    json.dump(manifest, open(os.path.join(a.out, "manifest.json"), "w"), indent=2)

    print(f"  cohorts   {len(cohorts)}" + (f"  ({len(empty)} empty dropped: {', '.join(empty)})" if empty else ""))
    print(f"  rows      {len(rows):,}")
    print(f"  distilleries {n_norm:,}" + (f"  ({n_raw - n_norm} spelling variants merged)" if n_raw != n_norm else ""))
    print(f"  columns   {len(out_cols)}")
    print(f"  sha256    {digest[:16]}…")
    return 0


if __name__ == "__main__":
    sys.exit(main())
