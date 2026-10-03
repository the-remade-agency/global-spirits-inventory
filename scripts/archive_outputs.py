#!/usr/bin/env python3
"""Archive the validated outputs to Drive, keeping the vault working copy thin.

Runs are written locally and stay local through the gate: Google Drive's file
provider can present a partially synced file as a complete one, and a checksum
gate that reads a half-written CSV reports a clean pass on data nobody has.
Drive is therefore downstream of validation, never upstream.

    python3 scripts/archive_outputs.py --dry-run
    python3 scripts/archive_outputs.py
    python3 scripts/archive_outputs.py --clear-local   # after verification

Never run this while a research pass is in flight. The vault copy is the live
working set until the run closes and the gate passes.
"""

import argparse
import glob
import hashlib
import os
import shutil
import sys

LOCAL = os.path.expanduser(os.environ.get(
    "SPIRITS_OUTPUTS",
    "~/Documents/_local_drive/markdown_lib/inventory_research/_outputs"))
DRIVE = os.path.expanduser(os.environ.get(
    "SPIRITS_ARCHIVE",
    "~/Library/CloudStorage/GoogleDrive-ericpace7@gmail.com/My Drive/x_code/inventory_research/_outputs"))


def sha(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for b in iter(lambda: fh.read(chunk), b""):
            h.update(b)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--clear-local", action="store_true",
                    help="delete the vault CSVs once every file verifies")
    a = ap.parse_args()

    if not os.path.isdir(LOCAL):
        sys.exit(f"local outputs not found: {LOCAL}")

    srcs = sorted(glob.glob(os.path.join(LOCAL, "*.csv")))
    if not srcs:
        sys.exit("no CSVs in the local outputs; refusing to archive nothing")

    print(f"  from {LOCAL}\n    to {DRIVE}\n  {len(srcs)} file(s)")
    if a.dry_run:
        same = new = changed = 0
        for s in srcs:
            d = os.path.join(DRIVE, os.path.basename(s))
            if not os.path.exists(d):
                new += 1
            elif sha(s) == sha(d):
                same += 1
            else:
                changed += 1
        print(f"  would copy {new} new, {changed} changed; {same} already identical")
        return 0

    os.makedirs(DRIVE, exist_ok=True)
    copied, verified, failed = 0, 0, []
    for s in srcs:
        d = os.path.join(DRIVE, os.path.basename(s))
        want = sha(s)
        if os.path.exists(d) and sha(d) == want:
            verified += 1
            continue
        # Copy to a temp name and rename, so a reader never sees a partial file
        # under the real one. Drive syncs the rename as its own event.
        tmp = d + ".part"
        shutil.copy2(s, tmp)
        os.replace(tmp, d)
        copied += 1
        if sha(d) == want:
            verified += 1
        else:
            failed.append(os.path.basename(s))

    print(f"  copied {copied}, verified {verified}/{len(srcs)}")
    if failed:
        print("  FAILED verification, local copies left untouched:")
        for f in failed[:10]:
            print(f"    {f}")
        return 1

    # What this does and does not prove. The checksum confirms the bytes Drive's
    # file provider hands back locally. It does not confirm Google has them;
    # upload is asynchronous and nothing here can see that queue. Treat a clean
    # run as "staged correctly", and let Drive's own UI confirm the sync before
    # clearing anything irreplaceable.
    print("  note: verified against the local Drive mount, not against Google's"
          " copy. Upload is asynchronous.")

    if a.clear_local:
        if failed:
            sys.exit("not clearing local with failures outstanding")
        for s in srcs:
            os.remove(s)
        print(f"  cleared {len(srcs)} CSV(s) from the vault working copy")
    return 0


if __name__ == "__main__":
    sys.exit(main())
