#!/usr/bin/env python3
"""Import an sf_index_export.ndjson.gz produced by export_index.py into Redis.

Safe on a shared instance: writes only sf:* keys, never flushes anything.
Idempotent: HSET with identical values; re-running converges to the same state.
Verifies the imported key count against the export's trailing _count record.
"""
import argparse
import gzip
import json
import sys

import redis
from tqdm import tqdm

BATCH = 10_000


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("dump", help="path to sf_index_export.ndjson.gz")
    ap.add_argument("--port", type=int, default=6380)
    args = ap.parse_args()

    r = redis.Redis(port=args.port, decode_responses=True)
    r.ping()

    expected = None
    imported = 0
    pipe = r.pipeline(transaction=False)
    pending = 0

    with gzip.open(args.dump, "rt", encoding="utf-8") as f:
        for line in tqdm(f, desc="importing sf:*", unit=" keys", unit_scale=True):
            rec = json.loads(line)
            if "_meta" in rec:
                print(f"dump metadata: {rec['_meta']}")
                continue
            if "_count" in rec:
                expected = rec["_count"]
                continue
            pipe.hset(f"sf:{rec['s']}", mapping=rec["c"])
            imported += 1
            pending += 1
            if pending >= BATCH:
                pipe.execute()
                pending = 0
            if imported % 1_000_000 == 0:
                tqdm.write(f"  {imported:,} keys imported")
    if pending:
        pipe.execute()

    print(f"\nimported {imported:,} sf:* keys")
    if expected is None:
        sys.exit("WARNING: dump had no trailing _count record — file may be truncated")
    if imported != expected:
        sys.exit(f"MISMATCH: dump says {expected:,} keys, imported {imported:,}")
    print(f"count matches dump record ({expected:,}) ✓")


if __name__ == "__main__":
    main()
