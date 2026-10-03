#!/usr/bin/env python3
"""Regenerate the project dashboard's data, and build a publishable version.

The dashboard was last generated 2026-06-29 and still reports 10,860 rows and
1,748 distilleries, both of which were wrong by September. It was hand-built,
which is why it drifted; this computes every figure from the published CSV so
it cannot say a number the dataset does not.

Two outputs from one pass:

  internal  everything, for the vault. Keeps the methodology, timeline and
            learnings blocks, which are not derivable from the data and are
            carried through from the previous build.

  public    the same figures with every internal field removed. The June build
            embedded the absolute path of Eric's Drive, including his email
            address, five times, and a learnings block whose entries include
            coaching about agents fabricating rows to hit a floor. None of
            that can go on a public website.

    python3 scripts/dashboard.py --out /tmp/d.json            # public, default
    python3 scripts/dashboard.py --internal --carry OLD.json
    python3 scripts/dashboard.py --template T.html --html OUT.html
"""

import argparse
import collections
import csv
import datetime
import json
import os
import re
import sys
from urllib.parse import urlsplit

CSV_PATH = "data/spirits_inventory.csv"

# An allow-list, deliberately, not a list of things to strip. A block-list
# leaks anything added upstream later; this excludes it until someone adds it
# here on purpose. What it currently keeps out:
#
#   source_paths        absolute Drive paths, with an email address in them
#   learnings_codified  agent coaching, including notes about fabricated rows
#   maintenance_runs    internal pass/fail against success criteria
#   skip_list_domains   sites that defeated the scraper
#   generated_at_local  timezone is a location tell and adds nothing
PUBLIC_KEYS = {
    "generated_at_utc", "headline", "categories", "files",
    "top_distilleries_50", "top_ndps_25", "top_image_domains_30",
    "methodology_decisions",
}

# timeline was on the allow-list until the scan below caught it: it is a build
# log, and its entries name internal feedback rules and read "5 of 6 success
# criteria met". Allow-listing a key is a judgement about the whole key, and
# this one looked like project history until someone read the strings.

# Patterns that must never appear in a public build, whatever key they arrive
# under. The allow-list decides which keys ship; this decides whether what is
# inside them is safe, which is the part a reviewer gets wrong. Checked on the
# serialised output, so a value nested anywhere is still caught.
LEAK_PATTERNS = [
    ("absolute local path", r"CloudStorage|/Users/|My Drive"),
    ("email address",       r"[\w.+-]+@[\w-]+\.[\w.]+"),
    ("agent feedback rule", r"feedback_\w+"),
    ("internal run grading", r"success criteria|PASSED \(|FAILED \("),
    ("scraper skip list",   r"skip_list"),
    ("vault-relative path", r"_outputs/|_research/|markdown[-_]lib"),
]


def norm_distillery(name):
    return re.sub(r"[^a-z0-9]", "", (name or "").casefold())


def slug(s):
    return re.sub(r"[^a-z0-9]+", "_", (s or "").casefold()).strip("_")


def host_of(url):
    try:
        h = urlsplit(url.strip()).netloc.lower()
        return h[4:] if h.startswith("www.") else h
    except Exception:
        return ""


def build(rows):
    def v(r, k):
        return (r.get(k) or "").strip()

    imaged = [r for r in rows if v(r, "label_image_url")]
    ndp_rows = [r for r in rows if v(r, "is_ndp").lower() in ("true", "1", "yes")]
    brands = {v(r, "producer_brand") for r in ndp_rows if v(r, "producer_brand")}
    names = {v(r, "distillery") for r in rows if v(r, "distillery")}

    domains = collections.Counter()
    for r in imaged:
        for u in re.split(r"[;\s|]+", v(r, "label_image_url")):
            h = host_of(u)
            if h:
                domains[h] += 1

    cats = {}
    for r in rows:
        st = v(r, "spirit_type")
        if not st:
            continue
        c = cats.setdefault(slug(st), {
            "display_name": st, "rows": 0, "imaged_url": 0, "ndp": 0,
            "classes": collections.Counter(), "countries": collections.Counter(),
        })
        c["rows"] += 1
        if v(r, "label_image_url"):
            c["imaged_url"] += 1
        if v(r, "is_ndp").lower() in ("true", "1", "yes"):
            c["ndp"] += 1
        if v(r, "special_designation"):
            c["classes"][v(r, "special_designation").split(";")[0].strip()] += 1
        if v(r, "cohort"):
            # The cohort already encodes the region split the old build called
            # "countries"; derive it rather than keeping a second mapping that
            # can disagree with the data.
            c["countries"][re.sub(rf"^{slug(st)}_?", "", v(r, "cohort")) or v(r, "cohort")] += 1

    for c in cats.values():
        c["img_url_pct"] = round(100 * c["imaged_url"] / c["rows"], 1) if c["rows"] else 0.0
        c["ndp_pct"] = round(100 * c["ndp"] / c["rows"], 1) if c["rows"] else 0.0
        c["classes"] = dict(c["classes"].most_common())
        c["countries"] = dict(c["countries"].most_common())

    dist = collections.Counter(v(r, "distillery") for r in rows if v(r, "distillery"))
    ndps = collections.Counter(v(r, "producer_brand") for r in ndp_rows if v(r, "producer_brand"))

    return {
        "generated_at_utc": datetime.datetime.now(datetime.timezone.utc)
                            .strftime("%Y-%m-%dT%H:%M:%SZ"),
        "headline": {
            "total_rows": len(rows),
            "total_categories": len(cats),
            "total_files": len({v(r, "cohort") for r in rows if v(r, "cohort")}),
            "total_distilleries": len({norm_distillery(n) for n in names}),
            "total_ndps": len(brands),
            "total_image_domains": len(domains),
            "imaged_url_count": len(imaged),
            "imaged_url_pct": round(100 * len(imaged) / len(rows), 1) if rows else 0.0,
            "ndp_count": len(ndp_rows),
            "ndp_pct": round(100 * len(ndp_rows) / len(rows), 1) if rows else 0.0,
        },
        "categories": dict(sorted(cats.items())),
        "files": sorted({v(r, "cohort") for r in rows if v(r, "cohort")}),
        "top_distilleries_50": dict(dist.most_common(50)),
        "top_ndps_25": dict(ndps.most_common(25)),
        "top_image_domains_30": dict(domains.most_common(30)),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--internal", action="store_true",
                    help="keep internal-only blocks (default is the public build)")
    ap.add_argument("--carry", help="previous dashboard json to carry non-derivable blocks from")
    ap.add_argument("--out", help="write the data json here")
    ap.add_argument("--template", help="dashboard HTML to inject into")
    ap.add_argument("--html", help="write the rendered HTML here")
    a = ap.parse_args()

    with open(CSV_PATH, newline="") as fh:
        rows = list(csv.DictReader(fh))
    data = build(rows)

    # methodology, timeline and learnings describe the project, not the rows,
    # so they cannot be recomputed. Carry them forward rather than silently
    # dropping them from the internal view.
    if a.carry and os.path.exists(a.carry):
        old = json.load(open(a.carry))
        for k in ("methodology_decisions", "timeline", "learnings_codified",
                  "maintenance_runs", "skip_list_domains"):
            if k in old:
                data[k] = old[k]

    if not a.internal:
        dropped = sorted(k for k in data if k not in PUBLIC_KEYS)
        for k in dropped:
            data.pop(k)
        print(f"  public build: dropped {len(dropped)} internal key(s): {', '.join(dropped) or 'none'}",
              file=sys.stderr)

        # Refuse rather than warn. A warning on a build that then ships is the
        # same as no check at all.
        probe = json.dumps(data, ensure_ascii=False)
        found = []
        for label, pat in LEAK_PATTERNS:
            m = re.search(pat, probe, re.I)
            if m:
                i = m.start()
                found.append(f"{label}: ...{probe[max(0, i - 70):i + 70]}...")
        if found:
            print("\n  REFUSING TO EMIT. Internal content survived the allow-list:",
                  file=sys.stderr)
            for f in found:
                print(f"    {f}", file=sys.stderr)
            sys.exit(2)

    h = data["headline"]
    print(f"  rows {h['total_rows']:,}  distilleries {h['total_distilleries']:,}  "
          f"categories {h['total_categories']}  images {h['imaged_url_pct']}%", file=sys.stderr)

    blob = json.dumps(data, ensure_ascii=False, separators=(",", ":"))

    if a.out:
        json.dump(data, open(a.out, "w"), ensure_ascii=False, indent=1)
        print(f"  wrote {a.out}", file=sys.stderr)

    if a.template:
        tpl = open(a.template).read()
        pat = re.compile(r"^const DATA = .*$", re.M)
        if not pat.search(tpl):
            sys.exit("template has no `const DATA = ...` line to replace")
        out = pat.sub(lambda _: f"const DATA = {blob};", tpl, count=1)
        # Assert the swap: a template whose old blob survives is worse than a
        # failure, because it renders plausible stale numbers.
        if "2026-06-29T14:28:11Z" in out:
            sys.exit("old generated_at survived the swap; refusing to write")
        dest = a.html or a.template
        open(dest, "w").write(out)
        print(f"  wrote {dest}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
