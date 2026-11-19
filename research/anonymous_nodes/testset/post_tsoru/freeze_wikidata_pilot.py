#!/usr/bin/env python3
"""Freeze a dated, auditable Wikidata evidence slice for the post-Tsoru pilot.

The capture is deliberately a relevant-claims slice, not a complete Wikidata dump.
For each article it saves the current Wikipedia revision metadata, the anchor QID,
selected kinship claims, selected English labels, retrieval timestamps and SHA-256
hashes of raw API responses. Requires only Python's standard library.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import os
import time
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse, unquote
from urllib.request import Request, urlopen

UA = "NEF-anonymous-node-benchmark/0.1 (research evidence capture)"
WIKI_API = "https://en.wikipedia.org/w/api.php"
WD_API = "https://www.wikidata.org/w/api.php"
REL_PROPS = ("P22", "P25", "P26", "P3373", "P40", "P1038")
# QIDs already checked from source-page Wikidata links; used only if pageprops
# cannot resolve the corresponding English Wikipedia title.
KNOWN = {
    "Indira Gandhi": "Q1149",
    "Alfred d’Orsay": "Q2622452",
    "Charles Martin Hall": "Q443131",
    "James Seth": "Q11309438",
    "Jennie Carter": "Q28777198",
}


def fetch_json(url, params, attempts=3):
    full = url + "?" + urlencode(params)
    last = None
    for i in range(attempts):
        try:
            req = Request(full, headers={"User-Agent": UA, "Accept": "application/json"})
            with urlopen(req, timeout=45) as response:
                raw = response.read()
                data = json.loads(raw.decode("utf-8"))
                time.sleep(1.0)
                return raw, data, full
        except HTTPError as exc:
            last = exc
            if exc.code == 429:
                retry_after = exc.headers.get("Retry-After", "")
                try:
                    delay = min(60, max(5, int(retry_after)))
                except ValueError:
                    delay = min(60, 5 * (2 ** i))
                time.sleep(delay)
                continue
            if i + 1 < attempts:
                time.sleep(min(30, 3 * (2 ** i)))
        except (URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            last = exc
            if i + 1 < attempts:
                time.sleep(min(30, 3 * (2 ** i)))
    raise RuntimeError(f"API request failed after {attempts} tries: {full}\n{last}")


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def article_title(article_url):
    path = urlparse(article_url).path.rstrip("/")
    return unquote(path.rsplit("/", 1)[-1]).replace("_", " ")


def resolve_anchor(row, outdir):
    title = article_title(row["source_url_or_id"])
    pageprops_params = {
        "action": "query", "format": "json", "prop": "pageprops",
        "ppprop": "wikibase_item", "redirects": 1, "titles": title,
    }
    pageprops_path = os.path.join(outdir, f"{row['item_id']}_wikipedia_pageprops.json")
    if os.path.exists(pageprops_path):
        raw = open(pageprops_path, "rb").read()
        data = json.loads(raw.decode("utf-8"))
        full = WIKI_API + "?" + urlencode(pageprops_params)
    else:
        raw, data, full = fetch_json(WIKI_API, pageprops_params)
        with open(pageprops_path, "wb") as handle:
            handle.write(raw)
    page = next(iter(data.get("query", {}).get("pages", {}).values()), {})
    qid = page.get("pageprops", {}).get("wikibase_item")
    method = "wikipedia_api_pageprops"
    if not qid and row["source_name"] in KNOWN:
        qid = KNOWN[row["source_name"]]
        method = "manual_fallback_from_reviewed_wikidata_link"
    if not qid:
        raise RuntimeError(f"No Wikidata QID resolved for {row['item_id']} ({title})")
    revision_params = {
        "action": "query", "format": "json", "prop": "revisions",
        "rvprop": "ids|timestamp|sha1", "rvlimit": 1, "redirects": 1,
        "titles": title,
    }
    revision_path = os.path.join(outdir, f"{row['item_id']}_wikipedia_revision.json")
    if os.path.exists(revision_path):
        revision_raw = open(revision_path, "rb").read()
        revision_data = json.loads(revision_raw.decode("utf-8"))
        revision_url = WIKI_API + "?" + urlencode(revision_params)
    else:
        revision_raw, revision_data, revision_url = fetch_json(WIKI_API, revision_params)
        with open(revision_path, "wb") as handle:
            handle.write(revision_raw)
    revpage = next(iter(revision_data.get("query", {}).get("pages", {}).values()), {})
    revision = (revpage.get("revisions") or [{}])[0]
    if not revision.get("revid"):
        raise RuntimeError(f"No source revision metadata for {title}")
    return {
        "title": title, "qid": qid, "resolution_method": method,
        "pageprops_api_url": full, "pageprops_response_sha256": sha256(raw),
        "revision_api_url": revision_url,
        "revision_response_sha256": sha256(revision_raw),
        "page_id": revpage.get("pageid"), "revision_id": revision["revid"],
        "revision_timestamp": revision.get("timestamp"),
        "revision_sha1": revision.get("sha1"),
    }


def item_capture(qids, outdir):
    captures, capture_meta = {}, {}
    raw_batches = []
    qids = sorted(set(qids))
    batch_number = 0
    for start in range(0, len(qids), 50):
        batch = qids[start:start + 50]
        batch_number += 1
        raw, data, full = fetch_json(WD_API, {
            "action": "wbgetentities", "format": "json",
            "ids": "|".join(batch), "props": "labels|claims", "languages": "en",
        })
        raw_name = f"wikidata_anchor_batch_{batch_number:03d}.json"
        with open(os.path.join(outdir, raw_name), "wb") as handle:
            handle.write(raw)
        capture_meta[full] = {"retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
                              "response_sha256": sha256(raw), "raw_file": raw_name}
        entities_data = data.get("entities", {})
        entity_list = list(entities_data.values()) if isinstance(entities_data, dict) else entities_data
        capture_meta[full]["returned_entities"] = len(entity_list)
        for entity in entity_list:
            if entity.get("missing") is not None:
                captures[entity.get("id")] = {"missing": True}
                continue
            claims = entity.get("claims", {})
            selected = {p: claims[p] for p in REL_PROPS if p in claims}
            labels = {"en": entity.get("labels", {}).get("en", {}).get("value")}
            captures[entity["id"]] = {"labels": labels, "claims": selected}
    target_qids = set()
    for entity in captures.values():
        for statements in entity.get("claims", {}).values():
            for statement in statements:
                value = statement.get("mainsnak", {}).get("datavalue", {}).get("value", {})
                if value.get("entity-type") == "item" and value.get("id"):
                    target_qids.add(value["id"])
    target_labels = {}
    label_batches = 0
    for start in range(0, len(sorted(target_qids)), 50):
        batch = sorted(target_qids)[start:start + 50]
        if not batch:
            continue
        label_batches += 1
        raw, data, full = fetch_json(WD_API, {
            "action": "wbgetentities", "format": "json", "ids": "|".join(batch),
            "props": "labels", "languages": "en",
        })
        raw_name = f"wikidata_target_labels_batch_{label_batches:03d}.json"
        with open(os.path.join(outdir, raw_name), "wb") as handle:
            handle.write(raw)
        capture_meta[full] = {"retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
                              "response_sha256": sha256(raw), "raw_file": raw_name}
        items = data.get("entities", {})
        item_list = list(items.values()) if isinstance(items, dict) else items
        capture_meta[full]["returned_entities"] = len(item_list)
        for entity in item_list:
            label = entity.get("labels", {}).get("en", {}).get("value")
            if label:
                target_labels[entity["id"]] = label
    return captures, target_labels, capture_meta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="pilot_candidates_v0.csv")
    ap.add_argument("--out", required=True, help="new output directory")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    if os.path.exists(os.path.join(args.out, "capture_manifest.json")):
        raise SystemExit("This capture folder already has a completed manifest; choose a new --out path.")
    with open(args.input, newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise SystemExit("Input CSV is empty")
    started = datetime.now(timezone.utc).isoformat()
    anchors = {}
    for i, row in enumerate(rows, 1):
        anchors[row["item_id"]] = resolve_anchor(row, args.out)
        print(f"resolved {i}/{len(rows)}: {row['item_id']} -> {anchors[row['item_id']]['qid']}", flush=True)
        time.sleep(1.0)
    entities, target_labels, batch_meta = item_capture([a["qid"] for a in anchors.values()], args.out)
    manifest = {
        "capture_started_at_utc": started,
        "capture_completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "capture_type": "dated Wikidata relevant-claims evidence slice; not a full dump",
        "source": "Wikidata wbgetentities API; anchor resolution via English Wikipedia API pageprops",
        "claim_properties": list(REL_PROPS),
        "source_rows": len(rows),
        "anchors": anchors,
        "wikidata_api_batches": batch_meta,
        "limitations": [
            "Wikidata is live and mutable; this capture freezes only the returned evidence slice.",
            "Only direct relationship claims listed in claim_properties are retained.",
            "A missing claim is not proof that a real-world relation does not exist.",
        ],
    }
    payload = {"manifest": manifest, "entities": entities, "target_labels_en": target_labels}
    encoded = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")
    outpath = os.path.join(args.out, "wikidata_evidence_slice.json")
    with open(outpath, "wb") as handle:
        handle.write(encoded)
    manifest["evidence_slice_sha256"] = sha256(encoded)
    with open(os.path.join(args.out, "capture_manifest.json"), "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2, sort_keys=True)
    summary_path = os.path.join(args.out, "relation_summary.csv")
    with open(summary_path, "w", newline="", encoding="utf-8") as handle:
        cols = ["item_id", "article_title", "anchor_qid", "article_revision_id", "article_revision_timestamp"] + list(REL_PROPS)
        writer = csv.DictWriter(handle, fieldnames=cols)
        writer.writeheader()
        for item_id, anchor in anchors.items():
            row = {"item_id": item_id, "article_title": anchor["title"], "anchor_qid": anchor["qid"],
                   "article_revision_id": anchor["revision_id"], "article_revision_timestamp": anchor["revision_timestamp"]}
            claims = entities.get(anchor["qid"], {}).get("claims", {})
            for prop in REL_PROPS:
                vals = []
                for statement in claims.get(prop, []):
                    value = statement.get("mainsnak", {}).get("datavalue", {}).get("value", {})
                    qid = value.get("id") if isinstance(value, dict) else None
                    if qid:
                        vals.append(f"{target_labels.get(qid, qid)} [{qid}]")
                row[prop] = " | ".join(vals)
            writer.writerow(row)
    print(f"saved {len(entities)} entities; slice sha256={manifest['evidence_slice_sha256']}", flush=True)
    print(outpath)

if __name__ == "__main__":
    main()
