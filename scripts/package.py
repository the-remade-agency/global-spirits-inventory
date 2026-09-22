#!/usr/bin/env python3
"""Build the published dataset from the working research outputs.

Run this after each quarterly maintenance pass, then tag a release. The point of
a script rather than a copy is that the consolidated file and the per-cohort
files cannot drift: both are produced from one source in one pass.

    python3 scripts/package.py --src /path/to/inventory_research/_outputs
"""
import argparse, csv, glob, hashlib, json, os, sys
from datetime import date

# QA working files, not inventory. They carry their own schema (csv_file,
# row_index, recommended_is_template, reasoning) and describe rows in the other
# files rather than adding any.
EXCLUDE = {"bourbon_ndp_audit", "bourbon_template_audit"}

# The cohort is encoded only in the source filename. Consolidating without
# promoting it to a column silently loses the grouping that distinguishes, say,
# bourbon_kentucky_craft from bourbon_indiana.
COHORT_COL = "cohort"


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

    os.makedirs(os.path.join(a.out, "by_cohort"), exist_ok=True)
    header, rows, cohorts, drift = None, [], [], []

    for f in files:
        cohort = os.path.splitext(os.path.basename(f))[0]
        with open(f, newline="", encoding="utf-8-sig", errors="replace") as fh:
            r = csv.DictReader(fh)
            if header is None:
                header = list(r.fieldnames)
            elif list(r.fieldnames) != header:
                drift.append(cohort)
                continue
            n = 0
            for row in r:
                row[COHORT_COL] = cohort
                rows.append(row)
                n += 1
        cohorts.append({"cohort": cohort, "rows": n})
        # per-cohort file, with the cohort column added so the two views match
        out_cols = header + [COHORT_COL]
        with open(os.path.join(a.out, "by_cohort", cohort + ".csv"), "w",
                  newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=out_cols)
            w.writeheader()
            with open(f, newline="", encoding="utf-8-sig", errors="replace") as src:
                for row in csv.DictReader(src):
                    row[COHORT_COL] = cohort
                    w.writerow(row)

    if drift:
        print(f"REFUSING: {len(drift)} file(s) have a different schema: {drift}",
              file=sys.stderr)
        return 1

    out_cols = header + [COHORT_COL]
    consolidated = os.path.join(a.out, "spirits_inventory.csv")
    with open(consolidated, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=out_cols)
        w.writeheader()
        w.writerows(rows)

    digest = hashlib.sha256(open(consolidated, "rb").read()).hexdigest()
    manifest = {
        "built": date.today().isoformat(),
        "rows": len(rows),
        "cohorts": len(cohorts),
        "columns": out_cols,
        "excluded_qa_files": sorted(EXCLUDE),
        "sha256_spirits_inventory_csv": digest,
        "by_cohort": cohorts,
    }
    json.dump(manifest, open(os.path.join(a.out, "manifest.json"), "w"), indent=2)

    print(f"  cohorts   {len(cohorts)}")
    print(f"  rows      {len(rows):,}")
    print(f"  columns   {len(out_cols)}")
    print(f"  sha256    {digest[:16]}…")
    return 0


if __name__ == "__main__":
    sys.exit(main())
