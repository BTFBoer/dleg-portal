"""Import JSON policies into the SQLite DB.

Usage:
  python scripts/import_policies.py --dir app/policies/hypotheekcompany

"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from sqlmodel import Session

from app.db import engine, init_db
from app.models import Policy


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    args = ap.parse_args()

    init_db()

    d = Path(args.dir)
    files = sorted(d.glob("*.json"))
    if not files:
        raise SystemExit("No JSON files found")

    with Session(engine) as s:
        for f in files:
            data = json.loads(f.read_text(encoding="utf-8"))
            key = f.stem
            label = data.get("label", key)
            lender = data.get("lender_name") or label.split("(")[0].strip() or "Onbekend"
            version = data.get("version", "")
            source_url = data.get("source_url", "")

            existing = s.query(Policy).filter(Policy.key == key).first()
            if existing:
                existing.label = label
                existing.lender_name = lender
                existing.version = version
                existing.source_url = source_url
                existing.json_text = json.dumps(data, ensure_ascii=False, indent=2)
            else:
                p = Policy(
                    key=key,
                    label=label,
                    lender_name=lender,
                    version=version,
                    source_url=source_url,
                    json_text=json.dumps(data, ensure_ascii=False, indent=2),
                )
                s.add(p)
        s.commit()

    print(f"Imported {len(files)} policies")


if __name__ == "__main__":
    main()
