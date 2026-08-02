#!/usr/bin/env python3
"""Export the sf:* surface-form index to a single compressed file for transfer.

Format: gzipped newline-delimited JSON (portable, inspectable with zcat):
    line 1:     {"_meta": {"format": "dbpedia-sf-index", "version": 1, ...}}
    lines 2..N: {"s": "<surface form>", "c": {"<local name>": "<tier|final>", ...}}
    last line:  {"_count": <number of sf:* keys exported>}

Import with import_index.py on the target machine.
"""
import argparse
import gzip
import json
import os

import redis
from tqdm import tqdm

BATCH = 5_000
DEFAULT_OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sf_index_export.ndjson.gz")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--port", type=int, default=6380)
    ap.add_argument("--out", default=DEFAULT_OUT)
    args = ap.parse_args()

    r = redis.Redis(port=args.port, decode_responses=True)
    r.ping()

    exported = 0
    with gzip.open(args.out, "wt", encoding="utf-8") as out:
        meta = {"_meta": {"format": "dbpedia-sf-index", "version": 1,
                          "release": "2022.12.01", "value_format": "tier|final"}}
        out.write(json.dumps(meta) + "\n")

        batch: list[str] = []

        def flush() -> None:
            nonlocal exported
            pipe = r.pipeline(transaction=False)
            for key in batch:
                pipe.hgetall(key)
            for key, h in zip(batch, pipe.execute()):
                if h:
                    out.write(json.dumps({"s": key[3:], "c": h}, ensure_ascii=False) + "\n")
                    exported += 1
            batch.clear()

        for key in tqdm(r.scan_iter(match="sf:*", count=10_000),
                        desc="exporting sf:*", unit=" keys", unit_scale=True):
            batch.append(key)
            if len(batch) >= BATCH:
                flush()
                if exported % 1_000_000 < BATCH:
                    tqdm.write(f"  {exported:,} keys exported")
        flush()
        out.write(json.dumps({"_count": exported}) + "\n")

    size = os.path.getsize(args.out)
    print(f"\nexported {exported:,} sf:* keys -> {args.out}")
    print(f"file size: {size:,} bytes ({size / 2**20:.1f} MiB)")


if __name__ == "__main__":
    main()
