#!/usr/bin/env python3
"""
NEF 1.0 on OUR index and OUR model — the controlled method comparison.

Why this exists
---------------
NEF 1.0's published 0.6391 used their own Redis (bare surface keys in db0,
redirects in db1) and GPT-4o. NEF 2.0's 0.6317 used our surface-form index and
Luna. Comparing those two changes THREE things at once: method, index, model.

This script holds two of them fixed. It runs NEF 1.0's pipeline unmodified, but
points its entity linking at OUR index via `surface_index.lookup()` — the exact
function NEF 2.0 uses — and at whatever model you pass. Result:

    NEF 1.0 method + our index + Luna     <- this script
    NEF 2.0 method + our index + Luna     <- results/final_clean, 0.6317
                                             method is the ONLY variable

Honesty note: the number this produces is NOT comparable to their published
0.6391, because the index differs. Report it as "NEF 1.0 re-run on our index".

Usage
-----
    export OPENROUTER_API_KEY=...
    export TEXT2KGBENCH_PATH=~/Text2KGBench
    python scripts/run_nef1_local_index.py --nef1 ~/Desktop/DBpedia/liberai-nef1 \
        --model openai/gpt-5.6-luna --domain 1_university --limit 10   # pilot
    python scripts/run_nef1_local_index.py --nef1 ~/Desktop/DBpedia/liberai-nef1 \
        --model openai/gpt-5.6-luna --out predictions_nef1_luna         # full
"""
import argparse, os, sys

ap = argparse.ArgumentParser()
ap.add_argument("--nef1", required=True, help="path to the LiberAI neural-extraction-framework clone")
ap.add_argument("--model", default="openai/gpt-5.6-luna")
ap.add_argument("--out", default="predictions_nef1_luna")
ap.add_argument("--domain", default=None)
ap.add_argument("--limit", type=int, default=None)
ap.add_argument("--parallel", type=int, default=8)
args, passthrough = ap.parse_known_args()

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))     # our surface_index
sys.path.insert(0, os.path.abspath(args.nef1))    # their pipeline

from surface_index import lookup as nef2_lookup   # noqa: E402


class LocalIndexLinking:
    """Drop-in replacement for NEF 1.0's RedisEntityLinking.

    Same contract: lookup(surface) -> [(entity_name, normalised_score)], highest
    first. Their `_redis_candidates` keeps only the names, and those names become
    the emitted triple's sub/obj — which is exactly the shape our index returns
    (local names like `Aaron_Deer`), so no URI translation is needed.

    Redirect chasing is not reimplemented: our index already resolves redirects
    at build time (that is what the `rd:` artifacts were folded in for), so
    following them again here would double-apply the same normalisation."""

    def __init__(self, *_, **__):
        self.available = True
        probe = nef2_lookup("Paraguay", k=1)
        if not probe:
            raise SystemExit("surface_index returned nothing for 'Paraguay' — "
                             "is Redis up on 6380 with the sf:* index loaded?")
        print(f"✓ NEF 1.0 linking redirected to our index (probe: {probe[0][0]})")

    def lookup(self, surface_form, top_k=5, thr=0.01):
        if not surface_form or not surface_form.strip():
            return []
        hits = nef2_lookup(surface_form.strip(), k=top_k)
        if not hits:
            return []
        mx = max(s for _, s in hits) or 1.0
        out = [(name, s / mx) for name, s in hits if (s / mx) >= thr]
        out.sort(key=lambda x: x[1], reverse=True)   # their contract: best first
        return out[:top_k]


def main():
    import redis_index                      # their module
    redis_index.RedisEntityLinking = LocalIndexLinking

    import run as nef1_run                  # their benchmark driver
    nef1_run.RedisEntityLinking = LocalIndexLinking
    if hasattr(nef1_run, "make_redis"):
        nef1_run.make_redis = lambda: LocalIndexLinking()

    # llm.py routes non-`local/` prefixes to OpenRouter
    os.environ["OPENAI_MODEL"] = args.model
    os.environ.setdefault("REDIS_HOST", "127.0.0.1")   # unused, keeps env checks happy
    os.environ.setdefault("REDIS_PORT", "6380")

    argv = ["run.py", "--eval", "--ground", "--out", args.out,
            "--parallel", str(args.parallel)]
    if args.domain:
        argv += ["--domain", args.domain]
    if args.limit:
        argv += ["--limit", str(args.limit)]
    argv += passthrough
    sys.argv = argv

    print(f"model={args.model}  out={args.out}  "
          f"{'domain=' + args.domain if args.domain else 'all 19 domains'}")
    raise SystemExit(nef1_run.main())


if __name__ == "__main__":
    main()
