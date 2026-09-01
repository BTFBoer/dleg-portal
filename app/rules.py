from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Dict, List, Optional, Tuple


# --- Data structures passed from DB layer to calculation layer ---


@dataclass
class YearInput:
    year: int

    # period
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    period_months_override: float = 0.0

    is_control_year: bool = False
    ytd_months: int = 0

    # IB
    saldo_fiscale_winst: float = 0.0
    net_result_no_ib: float = 0.0

    realized_income_ytd: float = 0.0
    extrapolated_income: float = 0.0
    prognose_income: float = 0.0

    box1_wage_before_start: float = 0.0
    box1_wage_during: float = 0.0
    box1_benefits: float = 0.0
    box1_row: float = 0.0
    other_box1_income: float = 0.0

    # corrections
    non_deductible_costs: float = 0.0
    special_tax_expenses: float = 0.0
    random_depreciation: float = 0.0
    investment_deduction: float = 0.0
    other_positive_fiscal: float = 0.0

    incidental_income: float = 0.0
    private_use_car: float = 0.0
    other_negative_fiscal: float = 0.0

    expired_rent_base: float = 0.0
    expired_rent_factor_pct: float = 85.0

    other_positive_avg: float = 0.0
    other_negative_avg: float = 0.0

    # DGA
    dga_salary: float = 0.0
    dividend: float = 0.0
    profit_after_corp_tax: float = 0.0

    # P&L / balance key numbers
    turnover_total: float = 0.0
    cogs_total: float = 0.0

    inventories: float = 0.0
    receivables: float = 0.0
    other_current_assets: float = 0.0
    cash: float = 0.0

    creditors: float = 0.0
    taxes_payable: float = 0.0
    other_current_liabilities: float = 0.0

    current_assets: float = 0.0
    current_liabilities: float = 0.0

    equity: float = 0.0
    total_assets: float = 0.0
    intangible_assets: float = 0.0


@dataclass
class CalcResult:
    income_years: Dict[int, float]
    base_income_avg: float
    capped_to_last_year: float
    interim_adjusted_income: float
    final_income: float
    notes: List[str]

    ratios: Dict[int, Dict[str, Optional[float]]]
    ratio_flags: Dict[int, Dict[str, str]]

    # extra values for reporting
    avg_months: float = 0.0
    control_year: Optional[int] = None
    control_year_extrapolated: float = 0.0
    control_year_prognose: float = 0.0


# --- Helpers ---


def _days_to_months(days: int) -> float:
    # 365/12 = 30.4167
    return days / 30.4166666667


def period_months(y: YearInput) -> float:
    if y.period_months_override and y.period_months_override > 0:
        return float(y.period_months_override)

    # Control year: prefer explicit ytd_months
    if y.is_control_year and y.ytd_months and y.ytd_months > 0:
        return float(y.ytd_months)

    if y.period_start and y.period_end and y.period_end >= y.period_start:
        days = (y.period_end - y.period_start).days + 1
        m = _days_to_months(days)
        # keep 2 decimals like 36,40
        return round(m, 2)

    # Default full year
    return 12.0


def safe_ratio(n: float, d: float) -> Optional[float]:
    try:
        n = float(n)
        d = float(d)
    except Exception:
        return None

    # In ViiZ-achtige rapporten wordt delen door 0 vaak pragmatisch behandeld.
    if d == 0:
        if n > 0:
            return 1.0
        return 0.0
    return n / d


def safe_pct(n: float, d: float) -> Optional[float]:
    r = safe_ratio(n, d)
    if r is None:
        return None
    return r * 100.0


def box1_income_after_corrections(y: YearInput, policy: Dict) -> float:
    """Box 1 (zakelijk) inkomen na jaarlijkse correcties.

    We volgen de logica uit de voorbeelden:
    - basis = saldo fiscale winst (IB) of netto resultaat
    - + positieve correcties
    - - negatieve correcties
    - + overige box 1
    """

    basis_mode = str(policy.get("ib_income_basis", "saldo_fiscale_winst"))
    if basis_mode in ("saldo_fiscale_winst", "fiscal_profit", "box1"):
        base = float(y.saldo_fiscale_winst)
        if base == 0.0 and y.net_result_no_ib:
            base = float(y.net_result_no_ib)
    else:
        base = float(y.net_result_no_ib) if y.net_result_no_ib else float(y.saldo_fiscale_winst)

    positives = (
        float(y.non_deductible_costs)
        + float(y.special_tax_expenses)
        + float(y.random_depreciation)
        + float(y.investment_deduction)
        + float(y.other_positive_fiscal)
        + (float(y.expired_rent_base) * (float(y.expired_rent_factor_pct) / 100.0))
    )
    negatives = float(y.incidental_income) + float(y.private_use_car) + float(y.other_negative_fiscal)

    return base + positives - negatives + float(y.other_box1_income)


def calc_ratios(y: YearInput) -> Dict[str, Optional[float]]:
    # fallback current assets/liabilities from components
    ca = float(y.current_assets) if y.current_assets else float(y.inventories + y.receivables + y.other_current_assets + y.cash)
    cl = float(y.current_liabilities) if y.current_liabilities else float(y.creditors + y.taxes_payable + y.other_current_liabilities)

    wc = ca - cl

    # quick ratio excludes inventories
    quick_assets = ca - float(y.inventories)

    cr = safe_ratio(ca, cl)
    qr = safe_ratio(quick_assets, cl)

    solv = safe_pct(float(y.equity), float(y.total_assets)) if (y.equity or y.total_assets) else None

    # debtor/creditor days (info)
    deb_days = None
    cred_days = None
    if y.turnover_total:
        deb_days = safe_ratio(float(y.receivables), float(y.turnover_total))
        if deb_days is not None:
            deb_days *= 365.0
    if y.cogs_total:
        cred_days = safe_ratio(float(y.creditors), float(y.cogs_total))
        if cred_days is not None:
            cred_days *= 365.0

    return {
        "current_assets": ca,
        "current_liabilities": cl,
        "current_ratio": cr,
        "quick_ratio": qr,
        "working_capital": wc,
        "solvability_pct": solv,
        "debtor_days": deb_days,
        "creditor_days": cred_days,
    }


def flag_ge(value: Optional[float], minimum: float) -> str:
    if value is None:
        return "n.v.t."
    return "Akkoord" if float(value) >= float(minimum) else "Niet akkoord"


# --- Calculations ---


def calculate_ib_income_viiz(
    years: List[YearInput],
    policy: Dict,
    current_month: int,
) -> Tuple[CalcResult, List[str]]:
    notes: List[str] = []
    ys = sorted([y for y in years if y.year], key=lambda x: x.year)
    if not ys:
        return (
            CalcResult(
                income_years={},
                base_income_avg=0.0,
                capped_to_last_year=0.0,
                interim_adjusted_income=0.0,
                final_income=0.0,
                notes=["Geen cijfers aangeleverd."],
                ratios={},
                ratio_flags={},
            ),
            notes,
        )

    # identify control year
    ctrl = next((y for y in ys if y.is_control_year), None)
    if ctrl is None:
        # heuristic
        last = ys[-1]
        if last.ytd_months or last.realized_income_ytd or last.prognose_income or last.extrapolated_income:
            ctrl = last

    control_year = ctrl.year if ctrl else None

    # per-year income (box1 after corrections)
    income_full: Dict[int, float] = {}
    income_for_avg: Dict[int, float] = {}
    months_for_avg: Dict[int, float] = {}

    for y in ys:
        inc = box1_income_after_corrections(y, policy)
        income_full[y.year] = inc

        m = period_months(y)
        months_for_avg[y.year] = m

        if ctrl and y.year == ctrl.year:
            # average uses realized ytd if available, else 'inc' as entered
            if y.realized_income_ytd:
                income_for_avg[y.year] = float(y.realized_income_ytd)
            else:
                income_for_avg[y.year] = inc
        else:
            income_for_avg[y.year] = inc

    total_months = sum(months_for_avg.values())
    if total_months <= 0:
        total_months = float(len(ys) * 12)

    sum_income_avg = sum(income_for_avg.values())
    avg_per_month = sum_income_avg / total_months
    avg_per_year = avg_per_month * 12.0

    # factor (starters/maatwerk) default 100%
    factor_pct = float(policy.get("income_factor_pct", 100.0))
    avg_per_year *= factor_pct / 100.0

    # last full year cap: pick last year with ~12 months and not control year
    last_full = None
    for y in reversed(ys):
        if ctrl and y.year == ctrl.year:
            continue
        if period_months(y) >= 11.5:
            last_full = y
            break
    capped = avg_per_year
    if last_full:
        ly = income_full.get(last_full.year, 0.0)
        capped = min(avg_per_year, ly)
        if avg_per_year > ly:
            notes.append("Gemiddelde is gemaximeerd op het laatste volledige boekjaar.")

    interim_adj = capped

    # control year extrapolation (for downward adjustment only)
    ctrl_extrap = 0.0
    ctrl_prognose = 0.0
    if ctrl:
        ctrl_prognose = float(ctrl.prognose_income or 0.0)
        if ctrl.extrapolated_income:
            ctrl_extrap = float(ctrl.extrapolated_income)
        else:
            # compute from ytd
            if ctrl.realized_income_ytd and ctrl.ytd_months:
                ctrl_extrap = float(ctrl.realized_income_ytd) * (12.0 / float(ctrl.ytd_months))

        # interim can only reduce
        req_from = int(policy.get("interim_required_from_month", 8))
        if current_month >= req_from and ctrl_extrap and ctrl_extrap < interim_adj:
            interim_adj = ctrl_extrap
            notes.append("Lopend jaar (geëxtrapoleerd) is lager; inkomen neerwaarts bijgesteld.")

        # prognose cap (also only reduce)
        if ctrl_prognose and ctrl_prognose < interim_adj:
            interim_adj = ctrl_prognose
            notes.append("Prognose is lager; inkomen neerwaarts bijgesteld op prognose.")

    # avg-level corrections
    interim_adj = interim_adj + float(ctrl.other_positive_avg if ctrl else 0.0) - float(ctrl.other_negative_avg if ctrl else 0.0)

    final = interim_adj

    # prepare ratios/flags
    ratios: Dict[int, Dict[str, Optional[float]]] = {y.year: calc_ratios(y) for y in ys}

    liq_min = float(policy.get("liquidity_min", 1.0))
    sol_min = float(policy.get("solvability_min_pct", 20.0))
    wk_min = float(policy.get("working_capital_min", 0.0))

    flags: Dict[int, Dict[str, str]] = {}
    for y in ys:
        r = ratios[y.year]
        flags[y.year] = {
            "Winstgevendheid": "Akkoord" if income_full[y.year] >= 0 else "Niet akkoord",
            "Current Ratio": flag_ge(r.get("current_ratio"), liq_min),
            "Quick Ratio": flag_ge(r.get("quick_ratio"), liq_min),
            "Werkkapitaal": "Akkoord" if r.get("working_capital") is not None and r.get("working_capital") >= wk_min else "Niet akkoord",
            "Solvabiliteit": flag_ge(r.get("solvability_pct"), sol_min),
        }

    calc = CalcResult(
        income_years=income_full,
        base_income_avg=round(avg_per_year, 2),
        capped_to_last_year=round(capped, 2),
        interim_adjusted_income=round(interim_adj, 2),
        final_income=round(final, 2),
        notes=notes,
        ratios=ratios,
        ratio_flags=flags,
        avg_months=round(total_months, 2),
        control_year=control_year,
        control_year_extrapolated=round(ctrl_extrap, 2),
        control_year_prognose=round(ctrl_prognose, 2),
    )

    return calc, notes


def calculate_dga_income(
    years: List[YearInput],
    policy: Dict,
    share_pct: float,
    current_month: int,
    dividend_share_pct: Optional[float] = None,
) -> Tuple[float, Dict[int, float], List[str]]:
    notes: List[str] = []
    ys = sorted([y for y in years if y.year], key=lambda x: x.year)
    required = int(policy.get("years_required", 3))
    lastN = ys[-required:] if ys else []
    if not lastN:
        return 0.0, {}, ["Geen cijfers aangeleverd."]

    salaries = {y.year: float(y.dga_salary) for y in lastN}
    avg_salary = sum(salaries.values()) / len(salaries)
    last_year = lastN[-1]

    max_last_year = float(last_year.dga_salary) + float(last_year.profit_after_corp_tax)
    base = min(avg_salary, max_last_year)
    if avg_salary > max_last_year:
        notes.append("Gemiddeld DGA-salaris gemaximeerd op salaris + winst na Vpb (laatste jaar).")

    dga_cfg = policy.get("dga", {})
    allow_dividend_share = float(dga_cfg.get("allow_dividend_if_share_pct_greater_than", 50.0))
    dividend_gate = float(dividend_share_pct) if dividend_share_pct is not None else float(share_pct)

    dividend_added = 0.0
    if dividend_gate > allow_dividend_share:
        divs = {y.year: float(y.dividend) for y in lastN}
        avg_div = sum(divs.values()) / len(divs)
        if dga_cfg.get("cap_dividend_to_last_year_profit_after_tax", True):
            avg_div = min(avg_div, float(last_year.profit_after_corp_tax))

        # Double balance test (latest year ratios)
        dbl = dga_cfg.get("double_balance_test", {})
        liq_min = float(dbl.get("liquidity_min", 1.0))
        sol_min = float(dbl.get("solvability_min_pct", 20.0))
        r = calc_ratios(last_year)
        if r.get("current_ratio") is not None and r["current_ratio"] < liq_min:
            notes.append("Dividend niet meegenomen: liquiditeit voldoet niet aan dubbele balanstoets.")
        elif r.get("solvability_pct") is not None and r["solvability_pct"] < sol_min:
            notes.append("Dividend niet meegenomen: solvabiliteit voldoet niet aan dubbele balanstoets.")
        else:
            dividend_added = avg_div
            notes.append("Dividend (gemiddelde) meegenomen conform DGA-regel en dubbele balanstoets.")
    else:
        notes.append("Dividend niet meegenomen: (dividend)belang onder drempel of niet dividendbevoegd.")

    total = base + dividend_added
    total = min(total, max_last_year)

    income_years = {y.year: float(y.dga_salary) + float(y.profit_after_corp_tax) for y in lastN}
    return total, income_years, notes


def calculate_case(
    entrepreneur_type: str,
    years: List[YearInput],
    policy: Dict,
    current_month: int,
    share_pct: float = 100.0,
    dividend_share_pct: Optional[float] = None,
) -> CalcResult:
    entrepreneur_type = (entrepreneur_type or "IB").upper()
    if entrepreneur_type in ("DGA", "BV", "NIET_IB", "NIET-IB"):
        final, income_years, notes = calculate_dga_income(years, policy, share_pct, current_month, dividend_share_pct)
        ratios = {y.year: calc_ratios(y) for y in years if y.year}
        flags = {y.year: {"Current Ratio": flag_ge(ratios[y.year].get("current_ratio"), float(policy.get("liquidity_min", 1.0)))} for y in years if y.year}
        if policy.get("profitability_rule") == "latest_and_one_prior":
            profit_values = [
                float(y.profit_after_corp_tax or y.net_result_no_ib or 0.0)
                for y in sorted(years, key=lambda item: item.year)[-3:]
            ]
            if not profit_values or profit_values[-1] <= 0 or not any(value > 0 for value in profit_values[:-1]):
                notes.append("NIET AKKOORD: laatste en minimaal één eerder toetsjaar moeten winstgevend zijn.")

        if policy.get("requires_manual_review"):
            notes.append(
                "BELEIDSVERIFICATIE VERPLICHT: "
                + str(policy.get("manual_review_reason") or "Handmatige beleidscontrole vereist.")
            )

        return CalcResult(
            income_years=income_years,
            base_income_avg=final,
            capped_to_last_year=final,
            interim_adjusted_income=final,
            final_income=final,
            notes=notes,
            ratios=ratios,
            ratio_flags=flags,
        )

    # IB
    calc, _ = calculate_ib_income_viiz(years, policy, current_month)
    if policy.get("profitability_rule") == "latest_and_one_prior":
        ordered = [calc.income_years[year] for year in sorted(calc.income_years)[-3:]]
        if not ordered or ordered[-1] <= 0 or not any(value > 0 for value in ordered[:-1]):
            calc.notes.append("NIET AKKOORD: laatste en minimaal één eerder toetsjaar moeten winstgevend zijn.")
    if policy.get("requires_manual_review"):
        calc.notes.append(
            "BELEIDSVERIFICATIE VERPLICHT: "
            + str(policy.get("manual_review_reason") or "Handmatige beleidscontrole vereist.")
        )
    if policy.get("quick_ratio_min") is not None:
        calc.notes.append(
            f"Handmatig controleren: quick ratio minimaal {float(policy['quick_ratio_min']):.2f}; voorraad moet afzonderlijk zijn vastgelegd."
        )
    return calc
