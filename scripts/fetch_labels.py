#!/usr/bin/env python3
"""Download label images for rows that do not have one cached yet.

The cache feeds the cellar-app project and lives on Drive beside the dataset's
own outputs. Its naming convention was derived from the existing 4,267 files
rather than invented: sha256(url).hexdigest()[:16], plus the extension from the
URL path, falling back to the one implied by Content-Type. Verified against all
4,966 index entries, 4,966 of which match exactly.

Getting that wrong would silently re-download everything under new names and
leave cellar-app pointing at the old ones, so the convention is asserted in
--check rather than assumed.

    python3 scripts/fetch_labels.py --check          # verify naming, download nothing
    python3 scripts/fetch_labels.py --dry-run
    python3 scripts/fetch_labels.py --limit 10
    python3 scripts/fetch_labels.py                  # the rest

Resumable by construction: anything already on disk is skipped, so an
interrupted run costs nothing. Failures are recorded, never retried blindly.
"""

import argparse
import collections
import concurrent.futures
import csv
import glob
import hashlib
import json
import mimetypes
import os
import re
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from package import has_value  # noqa: E402

OUTPUTS = os.path.expanduser(os.environ.get(
    "SPIRITS_OUTPUTS",
    "~/Documents/_local_drive/markdown_lib/inventory_research/_outputs"))
LABELS = os.path.expanduser(os.environ.get(
    "SPIRITS_LABELS",
    "~/Library/CloudStorage/GoogleDrive-ericpace7@gmail.com/My Drive/x_code/inventory_research/labels"))

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 " \
     "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
OK_TYPES = ("image/jpeg", "image/png", "image/webp", "image/avif",
            "image/gif", "image/svg+xml")
MAX_BYTES = 12 * 1024 * 1024


def key(url):
    return hashlib.sha256(url.encode()).hexdigest()[:16]


CT_EXT = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp",
          "image/avif": ".avif", "image/gif": ".gif", "image/svg+xml": ".svg"}


def ext_for(url, content_type):
    """Content-Type first, URL path second.

    Not the other way round, which is the intuitive order and is wrong here.
    Of 4,966 existing entries, zero disagree with their Content-Type, while 216
    disagree with their URL path: servers hand back WebP from a .png path often
    enough to matter. A first cut of this script used the URL and wrote WebP
    bytes into .png names, which is how the rule got checked properly."""
    ct = (content_type or "").split(";")[0].strip().lower()
    if ct in CT_EXT:
        return CT_EXT[ct]
    e = os.path.splitext(url.split("?")[0])[1].lower()
    if e in (".jpg", ".jpeg", ".png", ".webp", ".avif", ".gif", ".svg"):
        return ".jpg" if e == ".jpeg" else e
    g = mimetypes.guess_extension(ct) if ct else None
    return {".jpe": ".jpg", ".jpeg": ".jpg"}.get(g, g) or ".jpg"


def urls_in_outputs():
    seen = {}
    for f in sorted(glob.glob(os.path.join(OUTPUTS, "*.csv"))):
        for r in csv.DictReader(open(f, newline="")):
            if not has_value(r, "label_image_url"):
                continue
            for u in re.split(r"[;\s|]+", r["label_image_url"].strip()):
                if u.startswith("http"):
                    seen.setdefault(u, os.path.basename(f))
    return seen


def cached():
    return {os.path.splitext(os.path.basename(p))[0]
            for p in glob.glob(os.path.join(LABELS, "*"))
            if not p.endswith(".DS_Store")}


def check_convention():
    """Re-derive the naming rule from the existing index and assert it."""
    idx = os.path.join(os.path.dirname(OUTPUTS), "_outputs", "_image_cache", "_index.json")
    if not os.path.exists(idx):
        idx = os.path.join(OUTPUTS, "_image_cache", "_index.json")
    if not os.path.exists(idx):
        print("  no _index.json found; cannot verify the naming convention")
        return False
    entries = [x for x in json.load(open(idx))["entries"]
               if x.get("ok") and x.get("local_filename")]
    bad = [x for x in entries
           if x["local_filename"] != key(x["url"]) + os.path.splitext(x["local_filename"])[1]]
    print(f"  naming convention: {len(entries) - len(bad):,}/{len(entries):,} index entries "
          f"reproduce under sha256(url)[:16] + ext")
    if bad:
        print("  MISMATCHES, do not run a download against this cache:")
        for x in bad[:5]:
            print(f"    {x['local_filename']}  <-  {x['url'][:70]}")
    return not bad


def fetch(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Accept": "image/avif,image/webp,image/*,*/*;q=0.8"})
    with urllib.request.urlopen(req, timeout=25) as r:
        ct = r.headers.get("Content-Type", "")
        if not any(t in ct for t in OK_TYPES):
            raise ValueError(f"content-type {ct.split(';')[0] or 'missing'}")
        data = r.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise ValueError("over size cap")
        if len(data) < 500:
            raise ValueError(f"only {len(data)} bytes")
        return data, ct


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="verify naming only")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--report", default=None)
    a = ap.parse_args()

    if not os.path.isdir(LABELS):
        sys.exit(f"labels directory not found: {LABELS}")

    ok = check_convention()
    if a.check:
        return 0 if ok else 1
    if not ok:
        sys.exit("refusing to download against an unverified naming convention")

    have, found = cached(), urls_in_outputs()
    todo = [u for u in found if key(u) not in have]
    todo.sort()
    if a.limit:
        todo = todo[:a.limit]

    hosts = collections.Counter(u.split("/")[2].lower() for u in todo)
    print(f"  cached {len(have):,} · referenced {len(found):,} · to fetch {len(todo):,}")
    if a.dry_run:
        for h, n in hosts.most_common(10):
            print(f"    {h:<38} {n}")
        return 0

    done, failed, lock_hosts = [], [], collections.defaultdict(float)

    def work(url):
        host = url.split("/")[2].lower()
        wait = lock_hosts[host] - time.time()
        if wait > 0:
            time.sleep(wait)
        lock_hosts[host] = time.time() + 0.6     # one request per host per 600ms
        try:
            data, ct = fetch(url)
        except Exception as e:
            return url, None, f"{type(e).__name__}: {e}"[:120]
        name = key(url) + ext_for(url, ct)
        tmp = os.path.join(LABELS, name + ".part")
        # Write then rename: Drive's file provider can expose a partial file,
        # and a half-written image under a final name is cache poisoning.
        with open(tmp, "wb") as fh:
            fh.write(data)
        os.replace(tmp, os.path.join(LABELS, name))
        return url, name, None

    with concurrent.futures.ThreadPoolExecutor(max_workers=a.workers) as ex:
        for i, (url, name, err) in enumerate(ex.map(work, todo), 1):
            (failed if err else done).append(
                {"url": url, "error": err} if err else {"url": url, "file": name})
            if i % 50 == 0 or i == len(todo):
                print(f"    {i}/{len(todo)}  ok {len(done)}  failed {len(failed)}")

    print(f"\n  downloaded {len(done):,}, failed {len(failed):,}")
    if failed:
        why = collections.Counter(f["error"].split(":")[0] for f in failed)
        for k, n in why.most_common(6):
            print(f"    {k}: {n}")

    report = a.report or os.path.join(LABELS, "_fetch_report.json")
    json.dump({"at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               "downloaded": done, "failed": failed},
              open(report, "w"), indent=1)
    print(f"  report: {report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
