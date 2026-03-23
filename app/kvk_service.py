from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests

TEST_API_KEY = "l7xx1f2691f2520d487b902f4e0b57a0b197"
TEST_BASE = "https://api.kvk.nl/test/api/v1/basisprofielen"
PROD_BASE = "https://api.kvk.nl/api/v1/basisprofielen"


def _pick_address(data: Dict[str, Any]) -> str:
    # Try hoofdvestiging first
    hv = data.get("_embedded", {}).get("hoofdvestiging") or data.get("hoofdvestiging") or {}
    for key in ("adres", "bezoekadres", "bezoekAdres", "vestigingsadres"):
        addr = hv.get(key)
        if isinstance(addr, dict):
            straat = addr.get("straatnaam") or addr.get("straat") or ""
            huisnummer = str(addr.get("huisnummer") or "").strip()
            toevoeging = str(addr.get("huisnummerToevoeging") or "").strip()
            pc = addr.get("postcode") or ""
            plaats = addr.get("plaats") or addr.get("woonplaats") or ""
            left = " ".join([x for x in [straat, huisnummer, toevoeging] if x])
            right = " ".join([x for x in [pc, plaats] if x])
            return ", ".join([x for x in [left, right] if x])
        if isinstance(addr, str) and addr.strip():
            return addr.strip()
    return ""


def _pick_sbi(data: Dict[str, Any]) -> List[str]:
    items = data.get("sbiActiviteiten") or []
    out: List[str] = []
    for x in items:
        code = x.get("sbiCode") or x.get("code") or ""
        oms = x.get("sbiOmschrijving") or x.get("omschrijving") or ""
        s = " ".join([str(code).strip(), str(oms).strip()]).strip()
        if s:
            out.append(s)
    return out


def fetch_kvk_profile(kvk_nr: str, *, use_test: bool = False, api_key: Optional[str] = None, timeout: int = 20) -> Dict[str, Any]:
    kvk_nr = "".join(ch for ch in str(kvk_nr or "") if ch.isdigit())
    if len(kvk_nr) != 8:
        raise ValueError("KVK-nummer moet uit 8 cijfers bestaan.")

    if use_test:
        base = TEST_BASE
        key = TEST_API_KEY
    else:
        base = PROD_BASE
        key = api_key or os.getenv("KVK_API_KEY", "")
        if not key:
            raise RuntimeError("Geen KVK_API_KEY gevonden. Gebruik de testomgeving of zet een echte API-key als omgevingsvariabele.")

    url = f"{base}/{kvk_nr}"
    resp = requests.get(url, headers={"apikey": key, "Accept": "application/json"}, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()

    owner = data.get("_embedded", {}).get("eigenaar") or data.get("eigenaar") or {}
    hv = data.get("_embedded", {}).get("hoofdvestiging") or data.get("hoofdvestiging") or {}

    handelsnamen = data.get("handelsnamen") or []
    if isinstance(handelsnamen, list):
        trade_names = ", ".join([str(x) for x in handelsnamen if str(x).strip()])
    else:
        trade_names = str(handelsnamen or "")

    # legal form is annoyingly nested / variant across versions
    legal_form = ""
    for src in (data, hv, owner):
        for key in ("rechtsvorm", "uitgebreideRechtsvorm", "legalForm"):
            val = src.get(key)
            if isinstance(val, dict):
                legal_form = val.get("omschrijving") or val.get("code") or ""
            elif isinstance(val, str):
                legal_form = val
            if legal_form:
                break
        if legal_form:
            break

    main_name = data.get("naam") or trade_names.split(",")[0].strip() if trade_names else ""
    stat_name = data.get("statutaireNaam") or ""
    reg_date = data.get("formeleRegistratiedatum") or hv.get("formeleRegistratiedatum") or ""
    materiele = data.get("materieleRegistratie") or {}
    start_date = materiele.get("datumAanvang") or reg_date or ""
    branch_number = hv.get("vestigingsnummer") or ""

    return {
        "name": main_name,
        "statutory_name": stat_name,
        "legal_form": legal_form,
        "registration_date": reg_date,
        "start_date": start_date,
        "address": _pick_address(data),
        "trade_names": trade_names,
        "sbi_lines": _pick_sbi(data),
        "branch_number": branch_number,
        "source_url": url,
        "fetched_at": datetime.utcnow().isoformat(timespec="seconds"),
        "raw": data,
    }
