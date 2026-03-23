from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Set, Tuple

import pandas as pd


@dataclass
class RiskSectorResult:
    hit: bool
    matched_codes: List[str]
    note: str


def load_excluded_sbi_from_knab_excel(excel_path: Path) -> Set[str]:
    """Load a rough set of excluded/risico SBI codes from the provided Knab spreadsheet.

    The file structure may change; this loader is intentionally defensive.
    """
    if not excel_path.exists():
        return set()

    xl = pd.ExcelFile(excel_path)
    codes: Set[str] = set()
    for sheet in xl.sheet_names:
        df = xl.parse(sheet)
        # find any column containing 'SBI'
        sbi_cols = [c for c in df.columns if str(c).lower().strip().startswith('sbi') or 'sbi' in str(c).lower()]
        if not sbi_cols:
            continue
        col = sbi_cols[0]
        for v in df[col].dropna().astype(str).tolist():
            v = v.strip()
            if not v:
                continue
            codes.add(v)
    return codes


def normalize_sbi(code: str) -> str:
    return code.strip().replace(' ', '').replace(',', '.').upper()


def sbi_match(input_code: str, excluded: str) -> bool:
    """Prefix match: excluded '06.10' should match '06.10.1' etc."""
    ic = normalize_sbi(input_code)
    ex = normalize_sbi(excluded)
    if not ic or not ex:
        return False
    return ic == ex or ic.startswith(ex + ".") or ic.startswith(ex)


def check_sbi_codes(sbi_codes: str, excluded_codes: Iterable[str]) -> RiskSectorResult:
    if not sbi_codes:
        return RiskSectorResult(False, [], "Geen SBI-codes opgegeven.")

    inp = [normalize_sbi(x) for x in sbi_codes.replace(';', ',').split(',') if x.strip()]
    excluded = [normalize_sbi(x) for x in excluded_codes if str(x).strip()]

    matched: List[str] = []
    for ic in inp:
        for ex in excluded:
            if sbi_match(ic, ex):
                matched.append(ex)

    matched = sorted(set(matched))
    if matched:
        return RiskSectorResult(True, matched, "SBI match met (mogelijk) uitgesloten/risico sector(en).")
    return RiskSectorResult(False, [], "Geen match met risicosector-lijst.")
