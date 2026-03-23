"""Create placeholder policy JSON files per downloaded acceptatiegids.

Input: index.json produced by sync_hypotheekcompany.py
Output: a folder with JSON policy skeletons you can edit.

Usage:
  python scripts/bootstrap_policies_from_index.py --index app/data/policy_sources/index.json --out app/policies/hypotheekcompany

"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def slug(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"[^a-z0-9_]+", "", s)
    return s[:60] or "policy"


def infer_lender(anchor_text: str, filename: str) -> str:
    # crude heuristic; user can correct
    raw = anchor_text or filename
    raw = raw.strip()
    raw = re.sub(r"\s+", " ", raw)
    # take first chunk before ':' or 'voor'
    for sep in [":", "–", "-", "voor"]:
        if sep in raw:
            raw = raw.split(sep)[0]
            break
    raw = raw.strip()
    return raw[:80] or "Onbekend"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    idx = json.loads(Path(args.index).read_text(encoding="utf-8"))
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    for item in idx:
        if "error" in item:
            continue
        lender = infer_lender(item.get("anchor_text", ""), item.get("filename", ""))
        key = slug(lender) + "_UNMAPPED"
        policy = {
            "label": f"{lender} (UNMAPPED – koppel regels handmatig)",
            "years_required": 3,
            "method": "111",
            "ib_income_basis": "box1_from_business",
            "cap_last_year": True,
            "liquidity_min": 1.0,
            "solvability_min": 0.25,
            "interim_required_from_month": 8,
            "interim_can_only_reduce": True,
            "source_url": item.get("url", "")
        }
        (out_dir / f"{key}.json").write_text(json.dumps(policy, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Wrote skeleton policies to {out_dir}")


if __name__ == "__main__":
    main()
