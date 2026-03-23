"""Download acceptatiegidsen/voorwaarden PDFs vanaf HypotheekCompany.

Gebruik:
  python scripts/sync_hypotheekcompany.py --out app/data/policy_sources

Wat het doet:
- haalt de pagina 'acceptatievoorwaarden per maatschappij' op;
- extraheert alle links;
- downloadt PDFs naar de output directory;
- schrijft index.json met metadata.

Let op:
- Dit script is bedoeld voor intern archief/doe‑het‑zelf policy mapping.
- Respecteer de gebruiksvoorwaarden van de bron.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

PAGE_URL = "https://hypotheekcompany.nl/hypotheekcompany-extranet/support-center/voor-de-adviseur/acceptatievoorwaarden-per-maatschappij/"


def is_pdf(url: str) -> bool:
    p = urlparse(url)
    return p.path.lower().endswith(".pdf")


def safe_filename(url: str) -> str:
    name = Path(urlparse(url).path).name
    name = re.sub(r"[^a-zA-Z0-9._-]+", "_", name)
    return name[:180] or "file.pdf"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="Output directory")
    ap.add_argument("--timeout", type=int, default=30)
    args = ap.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    r = requests.get(PAGE_URL, timeout=args.timeout)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "lxml")

    links = []
    for a in soup.select("a[href]"):
        href = a.get("href")
        if not href:
            continue
        url = urljoin(PAGE_URL, href)
        if is_pdf(url):
            links.append({"url": url, "text": (a.get_text() or "").strip()})

    # de-dupe
    seen = set()
    uniq = []
    for x in links:
        if x["url"] in seen:
            continue
        seen.add(x["url"])
        uniq.append(x)

    index = []
    for i, item in enumerate(uniq, 1):
        url = item["url"]
        fn = safe_filename(url)
        dest = out_dir / fn

        print(f"[{i}/{len(uniq)}] {fn}")
        try:
            pr = requests.get(url, timeout=args.timeout)
            pr.raise_for_status()
            dest.write_bytes(pr.content)
            index.append({"url": url, "filename": fn, "bytes": dest.stat().st_size, "anchor_text": item.get("text", "")})
        except Exception as e:
            index.append({"url": url, "filename": fn, "error": str(e), "anchor_text": item.get("text", "")})

    (out_dir / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Done. Downloaded: {sum(1 for x in index if 'error' not in x)} / {len(index)}")


if __name__ == "__main__":
    main()
