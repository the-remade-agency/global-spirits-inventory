#!/usr/bin/env python3
"""Independent gate between the research run and publication.

Recomputes every claim from the vault CSVs and the pre-run baseline. Nothing
here reads the research agent's report, and nothing here runs the project's own
harness.

That second exclusion is deliberate. The harness is parameterised by the agent
being checked: it sets LOCKED_CLASSES, PRIMARY_SPIRIT_TYPE and SUB_FLOOR itself
before validating against them. During the initial build, subagents were caught
declaring a rule in the harness and emitting rows that broke it on the next
line, so a harness pass is a claim like any other. The checks below need no
per-category configuration, which is what makes them independent.

    python3 scripts/gate.py                      # against the newest baseline
    python3 scripts/gate.py --baseline FILE
    python3 scripts/gate.py --json report.json

Exit 0 only when nothing blocking is found. B does not run on a non-zero exit.
"""

import argparse
import collections
import csv
import glob
import hashlib
import json
import os
import re
import sys

# Where the run's working files live. Local by default and overridable, because
# the archive location is moving to Drive while the working location stays
# local: Drive's file provider can present a partially synced file as a
# complete one, which a checksum gate must never read.
VAULT = os.path.expanduser(os.environ.get(
    "SPIRITS_OUTPUTS",
    "~/Documents/_local_drive/markdown_lib/inventory_research/_outputs"))

# The QA working files package.py keeps out of the public build. Imported from
# package.py rather than restated, so the gate cannot end up blocking on a file
# that never ships, or waving through one that does. On the first run this list
# was duplicated here and the gate blocked on bourbon_template_audit, which has
# deliberately sourceless rows because auditing them is its job.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from package import EXCLUDE as QA_FILES, has_value
except Exception:
    QA_FILES = set()

    def has_value(row, col):            # noqa: D103 - fallback only
        v = (row.get(col) or "").strip()
        return bool(v) and v.upper() not in {"NULL", "N/A", "NA", "NONE", "-", "TBD", "UNKNOWN"}

    print("warning: could not import EXCLUDE from package.py; "
          "QA files will be judged as publishable", file=sys.stderr)

# The ten pairs the October docket is meant to collapse. Checked by name rather
# than by "are there any variants left", so a run that fixes nine and invents a
# new one cannot pass by arithmetic.
DOCKET_VARIANTS = [
    ("KOVAL Distillery", "Koval Distillery"),
    ("St George Spirits", "St. George Spirits"),
    ("Leopold Bros", "Leopold Bros."),
    ("Never Never Distilling Co", "Never Never Distilling Co."),
    ("Paul Marie & Fils", "Paul-Marie & Fils"),
    ("SAKURAO Distillery", "Sakurao Distillery"),
    ("The Distillery (Phuket)", "The Distillery Phuket"),
    ("La Nina del Mezcal (CRM NOM O170X)", "La Nina del Mezcal (CRM NOM-O170X)"),
    ("Los Siete Misterios (CRM NOM O153X)", "Los Siete Misterios (CRM NOM-O153X)"),
    ("Mezcalero (CRM NOM O14X)", "Mezcalero (CRM NOM-O14X)"),
]

DOCKET_VINTAGE_PRODUCERS = ["Widow Jane", "Old Forester", "WhistlePig"]

IDENTITY = ("spirit_type", "distillery", "spirit_name", "special_designation",
            "age_statement", "vintage", "batch_lot")

findings = []       # blocking
observations = []   # worth reading, not blocking


def block(code, msg, detail=None):
    findings.append({"code": code, "message": msg, "detail": detail or []})


def note(code, msg, detail=None):
    observations.append({"code": code, "message": msg, "detail": detail or []})


def norm(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").casefold())


def load_vault():
    rows, per_file = [], {}
    for f in sorted(glob.glob(os.path.join(VAULT, "*.csv"))):
        raw = open(f, "rb").read()
        try:
            r = list(csv.DictReader(open(f, newline="")))
        except Exception as e:
            block("unreadable", f"{os.path.basename(f)} could not be parsed: {e}")
            continue
        base = os.path.basename(f)
        per_file[base] = {"sha256": hashlib.sha256(raw).hexdigest(), "rows": len(r)}
        qa = os.path.splitext(base)[0] in QA_FILES
        for x in r:
            x["__file"] = base
            x["__qa"] = qa
        rows += r
    return rows, per_file


# ── 1. What moved, against the pre-run checksums ─────────────────────────────

def check_diff(per_file, base):
    before, after = base["files"], per_file
    added = sorted(set(after) - set(before))
    removed = sorted(set(before) - set(after))
    changed = sorted(f for f in set(before) & set(after)
                     if before[f]["sha256"] != after[f]["sha256"])

    untouched = len(set(before) & set(after)) - len(changed)
    note("files",
         f"{len(added)} new, {len(removed)} removed, {len(changed)} modified, "
         f"{untouched} untouched",
         [f"new: {f}" for f in added] + [f"removed: {f}" for f in removed])

    if removed:
        block("file_removed",
              f"{len(removed)} category file(s) disappeared. Maintenance is "
              f"append-only; a missing file is a truncation, not a result.", removed)

    shrunk = [f"{f}: {before[f]['rows']} -> {after[f]['rows']}"
              for f in changed if after[f]["rows"] < before[f]["rows"]]
    if shrunk:
        block("rows_lost",
              f"{len(shrunk)} file(s) lost rows. Every deletion needs ratification.",
              shrunk)

    b = base["totals"]["rows"]
    a = sum(v["rows"] for v in after.values())
    note("rows", f"{b:,} -> {a:,} ({a - b:+,})")
    return {"added": added, "changed": changed, "rows_before": b, "rows_after": a}


# ── 2. Fabrication signals, none of them category-specific ───────────────────

def check_fabrication(rows):
    def val(r, k):
        return (r.get(k) or "").strip()

    bad_proof = []
    for r in rows:
        try:
            p, a = float(val(r, "proof")), float(val(r, "abv"))
        except ValueError:
            continue
        if abs(p - 2 * a) > 0.15:
            bad_proof.append(f"{val(r,'spirit_name')[:40]} proof={p} abv={a} [{r['__file']}]")
    if bad_proof:
        block("proof_invariant",
              f"{len(bad_proof)} row(s) where proof is not twice abv. Arithmetic "
              f"this simple does not fail on real label data.", bad_proof[:12])

    seen = collections.defaultdict(list)
    for r in rows:
        seen[tuple(val(r, k) for k in IDENTITY)].append(r["__file"])
    dupes = {k: v for k, v in seen.items() if len(v) > 1}
    if dupes:
        block("duplicate_identity",
              f"{len(dupes)} identity tuple(s) appear more than once. The tuple is "
              f"the Supabase upsert key; duplicates mean two answers for one bottle.",
              [f"{k[2][:40]} | {k[4]} | in {', '.join(v)}" for k, v in list(dupes.items())[:12]])

    nosrc = [f"{val(r,'spirit_name')[:40]} [{r['__file']}]"
             for r in rows if not has_value(r, "source_urls")]
    if nosrc:
        block("no_source",
              f"{len(nosrc)} row(s) carry no source_urls at all. The dataset's whole "
              f"claim is that every row can be traced.", nosrc[:12])

    synth = [f"{val(r,'batch_lot')} [{r['__file']}]" for r in rows
             if re.fullmatch(r"(CC|BL|LOT)?\s*\d{2,4}", val(r, "batch_lot") or "x")]
    if synth:
        note("batch_lot_shape",
             f"{len(synth)} batch_lot value(s) look generated rather than transcribed "
             f"from a label. Worth a spot check.", sorted(set(synth))[:12])

    bad_vintage = [f"{val(r,'spirit_name')[:40]} vintage={val(r,'vintage')} [{r['__file']}]"
                   for r in rows
                   if val(r, "vintage").isdigit() and not (1800 <= int(val(r, "vintage")) <= 2027)]
    if bad_vintage:
        block("vintage_range", f"{len(bad_vintage)} vintage year(s) outside 1800-2027.",
              bad_vintage[:12])

    # The same tasting note under two producers is copy-paste, not tasting.
    notes = collections.defaultdict(set)
    for r in rows:
        t = val(r, "tasting_notes")
        if len(t) > 60:
            notes[t].add(val(r, "distillery"))
    shared = {t: d for t, d in notes.items() if len(d) > 1}
    if shared:
        note("shared_tasting_notes",
             f"{len(shared)} tasting note(s) appear under more than one producer.",
             [f"{len(d)} producers: {t[:60]}..." for t, d in list(shared.items())[:6]])

    generic = [val(r, "distillery_location") for r in rows
               if val(r, "distillery_location").lower() in
               {"unknown", "n/a", "na", "various", "scotland", "usa", "united states", ""}]
    if generic:
        note("generic_location",
             f"{len(generic)} row(s) have a placeholder or country-only "
             f"distillery_location.", list(collections.Counter(generic).most_common(6)))


# ── 3. Did the docket actually close ─────────────────────────────────────────

def check_docket(rows):
    names = {(r.get("distillery") or "").strip() for r in rows}
    unresolved = [f"{a!r} and {b!r} both still present"
                  for a, b in DOCKET_VARIANTS if a in names and b in names]
    gone = sum(1 for a, b in DOCKET_VARIANTS if not (a in names and b in names))
    if unresolved:
        note("docket_variants",
             f"{gone}/10 spelling pairs collapsed; {len(unresolved)} still split.",
             unresolved)
    else:
        note("docket_variants", "all 10 spelling pairs collapsed")

    # Any NEW collision introduced this run is a regression, not a leftover.
    groups = collections.defaultdict(set)
    for n in names:
        if n:
            groups[norm(n)].add(n)
    live = {k: sorted(v) for k, v in groups.items() if len(v) > 1}
    known = {norm(a) for a, _ in DOCKET_VARIANTS}
    fresh = {k: v for k, v in live.items() if k not in known}
    if fresh:
        block("new_variants",
              f"{len(fresh)} distillery spelling collision(s) not on the docket. "
              f"These were introduced by this run.", [", ".join(v) for v in fresh.values()][:12])

    for p in DOCKET_VINTAGE_PRODUCERS:
        rs = [r for r in rows
              if p.lower() in f"{r.get('distillery','')} {r.get('spirit_name','')} "
                              f"{r.get('producer_brand','')}".lower()]
        with_v = [r for r in rs if has_value(r, "vintage")]
        cats = sorted({r.get("spirit_type", "") for r in rs})
        note("docket_vintage",
             f"{p}: {len(rs)} rows across {len(cats)} categor{'y' if len(cats)==1 else 'ies'}, "
             f"{len(with_v)} carrying a vintage", cats)


# ── 3b. The README's own coverage table, as an independent reference ─────────

def check_readme_table(rows):
    """Compare computed coverage against the table README.md publishes.

    Added after the table caught a bug in this very script. On 2026-10-02 the
    gate and the dashboard reported label_image_url at 92.2% and shipped that
    to the website, because their presence test counted the literal string
    "NULL" as a value. The README had said 47.6% the whole time, and nobody
    compared them.

    Two independently produced numbers that must agree is worth more than
    either one alone. A mismatch means the data moved and the table is stale,
    or the computation is wrong, and both need a person.
    """
    try:
        text = open(os.path.join(os.path.dirname(__file__), "..", "README.md")).read()
    except OSError:
        note("readme_table", "README.md not readable; coverage cross-check skipped")
        return

    claims = re.findall(r"^\| `([a-z_]+)` \| ([\d.]+)% \|$", text, re.M)
    if not claims:
        note("readme_table", "no coverage table found in README.md")
        return

    # The README describes the last published build. After a maintenance run
    # the data has moved and the table is stale by definition, which is not a
    # fault and is fixed at step 6.3. The two cases need separating, or this
    # blocks on every run and gets ignored, which is worse than not checking.
    stated = re.search(r"\*\*([\d,]+) expressions", text)
    stated_rows = int(stated.group(1).replace(",", "")) if stated else None
    same_build = stated_rows == len(rows)

    off = []
    for col, claimed in claims:
        if col not in rows[0]:
            off.append(f"{col}: in the README table, not in the data")
            continue
        actual = round(100 * sum(1 for r in rows if has_value(r, col)) / len(rows), 2)
        if abs(actual - float(claimed)) > 0.15:
            off.append(f"{col}: README says {claimed}%, data says {actual:.2f}%")

    if not off:
        note("readme_table", f"all {len(claims)} fields in the README coverage table "
                             f"match the data")
    elif same_build:
        # Same row count, different percentages. One of the two is wrong and
        # neither can be assumed; this is the case that caught the sentinel bug.
        block("readme_coverage",
              f"The README describes {stated_rows:,} rows, the data has the same "
              f"count, and {len(off)} coverage figure(s) still disagree. Either the "
              f"table or the computation is wrong.", off)
    else:
        note("readme_table",
             f"README describes {stated_rows:,} rows, data has {len(rows):,}: the "
             f"table is stale and needs updating at step 6.3. {len(off)} figure(s) "
             f"will change.", off)


# ── 4. Coverage, reported rather than judged ─────────────────────────────────

def check_coverage(rows, diff):
    def pct(n):
        return f"{100 * n / len(rows):.1f}%" if rows else "-"
    img = sum(1 for r in rows if has_value(r, "label_image_url"))
    note("label_images", f"label_image_url on {img:,}/{len(rows):,} ({pct(img)})")

    bare = sum(1 for r in rows
               if has_value(r, "source_urls")
               and not re.search(r"https?://[^/]+/\S", r["source_urls"]))
    note("bare_sources", f"{bare:,} row(s) cite a bare host with no path ({pct(bare)})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline")
    ap.add_argument("--json")
    a = ap.parse_args()

    bpath = a.baseline or sorted(glob.glob(
        os.path.join(os.path.dirname(__file__), "..", ".baseline", "pre_*.json")))[-1]
    base = json.load(open(bpath))

    rows, per_file = load_vault()
    if not rows:
        print("no rows read from the vault; refusing to report a pass", file=sys.stderr)
        return 2

    publishable = [r for r in rows if not r["__qa"]]
    held = len(rows) - len(publishable)

    diff = check_diff(per_file, base)
    check_fabrication(publishable)
    check_docket(publishable)
    check_readme_table(publishable)
    check_coverage(publishable, diff)
    if held:
        note("qa_files",
             f"{held:,} row(s) in {len(QA_FILES)} QA file(s) excluded from every "
             f"check above, matching package.py. They never reach the public build.",
             sorted(QA_FILES))

    print(f"GATE  baseline {os.path.basename(bpath)}  ({base['captured']})\n")
    for o in observations:
        print(f"  ..  {o['message']}")
        for d in (o["detail"] or [])[:6]:
            print(f"        {d}")
    print()
    if findings:
        print(f"BLOCKING: {len(findings)}\n")
        for f in findings:
            print(f"  !!  [{f['code']}] {f['message']}")
            for d in (f["detail"] or [])[:10]:
                print(f"        {d}")
        print("\nPublication stage must not run.")
    else:
        print("No blocking findings. Publication may proceed.")

    if a.json:
        json.dump({"baseline": bpath, "diff": diff,
                   "blocking": findings, "observations": observations},
                  open(a.json, "w"), indent=1, default=str)
        print(f"\nwrote {a.json}")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
