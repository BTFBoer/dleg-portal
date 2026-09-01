from __future__ import annotations
import json
import os
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from .db import get_session, init_db
from .kvk_service import fetch_kvk_profile
from .field_catalogs import (
    BALANCE_GROUPS, PL_GROUPS, IB_GROUPS,
    BALANCE_TOTAL_FORMULAS, PL_TOTAL_FORMULAS, PL_COST_COMPONENTS, IB_TOTAL_FORMULAS,
    parse_json_blob, derive_core_from_detail,
)
from .models import (
    Case,
    ControlChecklistItem,
    ControlDecision,
    DocumentUsed,
    Enterprise,
    KYCCheck,
    LegalFormChange,
    Ownership,
    Policy,
    UploadedDoc,
    YearData,
)
from .reporting import build_income_report_pdf
from .rules import YearInput, calculate_case, box1_income_after_corrections, calc_ratios, period_months
from .risk_sectors import check_sbi_codes, load_excluded_sbi_from_knab_excel
from .structure import (
    OrgEdge,
    build_consolidation_groups,
    build_mermaid,
    max_withdrawable_working_capital,
    minority_participations,
    render_organogram_png,
)


def compute_beneficial_map(case_id: int, s: Session) -> Dict[int, Dict[str, float]]:
    """Bereken (indicatief) indirect economisch belang en stemrecht van de aanvrager.

    Resultaat per owned enterprise_id:
      - share_pct_total (0-100)
      - voting_pct_total (0-100)
      - dividend_share_pct_total (0-100)

    NB: Dit is een eenvoudige graf-analyse (MVP). Bij complexe statuten, soorten
    aandelen, certificering, prioriteitsaandelen, etc. is expert judgement nodig.
    """
    edges = s.exec(select(Ownership).where(Ownership.case_id == case_id)).all()
    if not edges:
        return {}

    # Build adjacency from either PERSON or enterprise_id
    adj: Dict[tuple, List[Ownership]] = {}
    for e in edges:
        key = (e.owner_kind, e.owner_enterprise_id or 0)
        adj.setdefault(key, []).append(e)

    # DFS from PERSON root
    out_share: Dict[int, float] = {}
    out_voting: Dict[int, float] = {}
    out_div_share: Dict[int, float] = {}

    stack = [("PERSON", 0, 1.0, 1.0, True)]  # (kind,id,share,voting,div_ok)
    visited = set()
    while stack:
        kind, oid, acc_share, acc_voting, acc_div = stack.pop()
        state = (kind, oid, round(acc_share, 6), round(acc_voting, 6), acc_div)
        if state in visited:
            continue
        visited.add(state)
        for edge in adj.get((kind, oid), []):
            s_pct = float(edge.share_pct) / 100.0
            v_pct = float(edge.voting_pct if edge.voting_pct else edge.share_pct) / 100.0
            n_share = acc_share * s_pct
            n_voting = acc_voting * v_pct
            n_div = acc_div and bool(edge.dividend_entitled)

            eid = int(edge.owned_enterprise_id)
            out_share[eid] = min(1.0, out_share.get(eid, 0.0) + n_share)
            out_voting[eid] = min(1.0, out_voting.get(eid, 0.0) + n_voting)
            if n_div:
                out_div_share[eid] = min(1.0, out_div_share.get(eid, 0.0) + n_share)

            # traverse further as ENTERPRISE owner
            stack.append(("ENTERPRISE", eid, n_share, n_voting, n_div))

    return {
        eid: {
            "share_pct_total": round(out_share.get(eid, 0.0) * 100.0, 4),
            "voting_pct_total": round(out_voting.get(eid, 0.0) * 100.0, 4),
            "dividend_share_pct_total": round(out_div_share.get(eid, 0.0) * 100.0, 4),
        }
        for eid in set(list(out_share.keys()) + list(out_voting.keys()) + list(out_div_share.keys()))
    }


def build_org_nodes_edges(case_id: int, s: Session, *, max_entities: int = 100) -> tuple[list[tuple[str, str]], list[OrgEdge]]:
    c = s.get(Case, case_id)
    enterprises = s.exec(select(Enterprise).where(Enterprise.case_id == case_id).order_by(Enterprise.id)).all()
    enterprises = enterprises[:max_entities]
    id_to_node = {e.id: f"E{e.id}" for e in enterprises}

    nodes: list[tuple[str, str]] = [("P", f"Aanvrager: {c.applicant_name if c else 'persoon'}")]
    nodes.extend([(id_to_node[e.id], f"{e.name} ({e.legal_form})") for e in enterprises])

    edges_db = s.exec(select(Ownership).where(Ownership.case_id == case_id)).all()
    edges: list[OrgEdge] = []
    for o in edges_db:
        if o.owned_enterprise_id not in id_to_node:
            continue
        owner_node = "P" if o.owner_kind == "PERSON" else id_to_node.get(o.owner_enterprise_id)
        if not owner_node:
            continue
        owned_node = id_to_node[o.owned_enterprise_id]
        sp = float(o.share_pct)
        vp = float(o.voting_pct) if float(o.voting_pct) else sp
        edges.append(
            OrgEdge(
                owner=owner_node,
                owned=owned_node,
                share_pct=sp,
                voting_pct=vp,
                dividend_entitled=bool(o.dividend_entitled),
            )
        )
    return nodes, edges


def build_consolidated_years(member_ids: list[int], s: Session) -> list[YearInput]:
    """Sum YearData across member enterprises by year.

    NB: periodevelden (start/eind) worden niet geconsolideerd; voor geconsolideerde
    berekeningen werken we met jaar-totalen en nemen we controlejaarinstellingen
    (ytd_months/is_control_year) conservatief over (max).
    """
    rows = s.exec(select(YearData).where(YearData.enterprise_id.in_(member_ids))).all()
    by_year: dict[int, YearInput] = {}
    for r in rows:
        y = by_year.get(r.year)
        if not y:
            y = YearInput(year=r.year)
            by_year[r.year] = y

        # carry control flags
        y.is_control_year = bool(y.is_control_year or getattr(r, 'is_control_year', False))
        y.ytd_months = max(int(getattr(r, 'ytd_months', 0) or 0), int(y.ytd_months or 0))

        # income bases
        y.saldo_fiscale_winst += float(getattr(r, 'saldo_fiscale_winst', 0.0) or 0.0)
        y.net_result_no_ib += float(getattr(r, 'net_result_no_ib', 0.0) or 0.0)
        y.realized_income_ytd += float(getattr(r, 'realized_income_ytd', 0.0) or 0.0)
        y.extrapolated_income = max(float(getattr(r, 'extrapolated_income', 0.0) or 0.0), float(y.extrapolated_income or 0.0))
        y.prognose_income = max(float(getattr(r, 'prognose_income', 0.0) or 0.0), float(y.prognose_income or 0.0))

        # corrections
        for f in [
            'non_deductible_costs','special_tax_expenses','random_depreciation','investment_deduction','other_positive_fiscal',
            'incidental_income','private_use_car','other_negative_fiscal','other_box1_income',
            'expired_rent_base','other_positive_avg','other_negative_avg',
        ]:
            setattr(y, f, float(getattr(y, f, 0.0) or 0.0) + float(getattr(r, f, 0.0) or 0.0))

        # other incomes
        for f in ['box1_wage_before_start','box1_wage_during','box1_benefits','box1_row']:
            setattr(y, f, float(getattr(y, f, 0.0) or 0.0) + float(getattr(r, f, 0.0) or 0.0))

        # dga
        y.dga_salary += float(getattr(r, 'dga_salary', 0.0) or 0.0)
        y.dividend += float(getattr(r, 'dividend', 0.0) or 0.0)
        y.profit_after_corp_tax += float(getattr(r, 'profit_after_corp_tax', 0.0) or 0.0)

        # p&l totals
        y.turnover_total += float(getattr(r, 'turnover_total', 0.0) or 0.0)
        y.cogs_total += float(getattr(r, 'cogs_total', 0.0) or 0.0)

        # balance components
        y.inventories += float(getattr(r, 'inventories', 0.0) or 0.0)
        y.receivables += float(getattr(r, 'receivables', 0.0) or 0.0)
        y.other_current_assets += float(getattr(r, 'other_current_assets', 0.0) or 0.0)
        y.cash += float(getattr(r, 'cash', 0.0) or 0.0)

        y.creditors += float(getattr(r, 'creditors', 0.0) or 0.0)
        y.taxes_payable += float(getattr(r, 'taxes_payable', 0.0) or 0.0)
        y.other_current_liabilities += float(getattr(r, 'other_current_liabilities', 0.0) or 0.0)

        y.current_assets += float(getattr(r, 'current_assets', 0.0) or 0.0)
        y.current_liabilities += float(getattr(r, 'current_liabilities', 0.0) or 0.0)
        y.equity += float(getattr(r, 'equity', 0.0) or 0.0)
        y.total_assets += float(getattr(r, 'total_assets', 0.0) or 0.0)
        y.intangible_assets += float(getattr(r, 'intangible_assets', 0.0) or 0.0)

    return list(sorted(by_year.values(), key=lambda z: z.year))


def yd_to_yearinput(yd: YearData) -> YearInput:
    return YearInput(
        year=int(yd.year),
        period_start=getattr(yd, 'period_start', None),
        period_end=getattr(yd, 'period_end', None),
        period_months_override=float(getattr(yd, 'period_months_override', 0.0) or 0.0),
        is_control_year=bool(getattr(yd, 'is_control_year', False)),
        ytd_months=int(getattr(yd, 'ytd_months', 0) or 0),
        saldo_fiscale_winst=float(getattr(yd, 'saldo_fiscale_winst', 0.0) or 0.0),
        net_result_no_ib=float(getattr(yd, 'net_result_no_ib', 0.0) or 0.0),
        realized_income_ytd=float(getattr(yd, 'realized_income_ytd', 0.0) or 0.0),
        extrapolated_income=float(getattr(yd, 'extrapolated_income', 0.0) or 0.0),
        prognose_income=float(getattr(yd, 'prognose_income', 0.0) or 0.0),
        box1_wage_before_start=float(getattr(yd, 'box1_wage_before_start', 0.0) or 0.0),
        box1_wage_during=float(getattr(yd, 'box1_wage_during', 0.0) or 0.0),
        box1_benefits=float(getattr(yd, 'box1_benefits', 0.0) or 0.0),
        box1_row=float(getattr(yd, 'box1_row', 0.0) or 0.0),
        other_box1_income=float(getattr(yd, 'other_box1_income', 0.0) or 0.0),
        non_deductible_costs=float(getattr(yd, 'non_deductible_costs', 0.0) or 0.0),
        special_tax_expenses=float(getattr(yd, 'special_tax_expenses', 0.0) or 0.0),
        random_depreciation=float(getattr(yd, 'random_depreciation', 0.0) or 0.0),
        investment_deduction=float(getattr(yd, 'investment_deduction', 0.0) or 0.0),
        other_positive_fiscal=float(getattr(yd, 'other_positive_fiscal', 0.0) or 0.0),
        incidental_income=float(getattr(yd, 'incidental_income', 0.0) or 0.0),
        private_use_car=float(getattr(yd, 'private_use_car', 0.0) or 0.0),
        other_negative_fiscal=float(getattr(yd, 'other_negative_fiscal', 0.0) or 0.0),
        expired_rent_base=float(getattr(yd, 'expired_rent_base', 0.0) or 0.0),
        expired_rent_factor_pct=float(getattr(yd, 'expired_rent_factor_pct', 85.0) or 85.0),
        other_positive_avg=float(getattr(yd, 'other_positive_avg', 0.0) or 0.0),
        other_negative_avg=float(getattr(yd, 'other_negative_avg', 0.0) or 0.0),
        dga_salary=float(getattr(yd, 'dga_salary', 0.0) or 0.0),
        dividend=float(getattr(yd, 'dividend', 0.0) or 0.0),
        profit_after_corp_tax=float(getattr(yd, 'profit_after_corp_tax', 0.0) or 0.0),
        turnover_total=float(getattr(yd, 'turnover_total', 0.0) or 0.0),
        cogs_total=float(getattr(yd, 'cogs_total', 0.0) or 0.0),
        operating_costs_total=float(getattr(yd, 'operating_costs_total', 0.0) or 0.0),
        depreciation_total=float(getattr(yd, 'depreciation_total', 0.0) or 0.0),
        financial_income_total=float(getattr(yd, 'financial_income_total', 0.0) or 0.0),
        financial_expense_total=float(getattr(yd, 'financial_expense_total', 0.0) or 0.0),
        extraordinary_income_total=float(getattr(yd, 'extraordinary_income_total', 0.0) or 0.0),
        extraordinary_expense_total=float(getattr(yd, 'extraordinary_expense_total', 0.0) or 0.0),
        inventories=float(getattr(yd, 'inventories', 0.0) or 0.0),
        receivables=float(getattr(yd, 'receivables', 0.0) or 0.0),
        other_current_assets=float(getattr(yd, 'other_current_assets', 0.0) or 0.0),
        cash=float(getattr(yd, 'cash', 0.0) or 0.0),
        creditors=float(getattr(yd, 'creditors', 0.0) or 0.0),
        taxes_payable=float(getattr(yd, 'taxes_payable', 0.0) or 0.0),
        other_current_liabilities=float(getattr(yd, 'other_current_liabilities', 0.0) or 0.0),
        current_assets=float(getattr(yd, 'current_assets', 0.0) or 0.0),
        current_liabilities=float(getattr(yd, 'current_liabilities', 0.0) or 0.0),
        equity=float(getattr(yd, 'equity', 0.0) or 0.0),
        total_assets=float(getattr(yd, 'total_assets', 0.0) or 0.0),
        intangible_assets=float(getattr(yd, 'intangible_assets', 0.0) or 0.0),
    )

APP_DIR = Path(__file__).resolve().parent
DATA_DIR = APP_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
REPORT_DIR = APP_DIR / "reports"
POLICY_DEFAULTS = APP_DIR / "policies" / "defaults.json"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="IKV Portal (MVP)")

app.mount("/static", StaticFiles(directory=str(APP_DIR / "static")), name="static")

templates = Jinja2Templates(directory=str(APP_DIR / "templates"))


@app.on_event("startup")
def _startup() -> None:
    init_db()
    seed_defaults()


def seed_defaults() -> None:
    if not POLICY_DEFAULTS.exists():
        return
    defaults = json.loads(POLICY_DEFAULTS.read_text(encoding="utf-8"))
    with get_session() as s:
        for key, cfg in defaults.items():
            existing = s.exec(select(Policy).where(Policy.key == key)).first()
            if existing:
                continue
            lender = cfg.get("lender_name") or ("NHG" if key.startswith("NHG") else ("Volksbank" if "VOLKSBANK" in key else ("BLG" if "BLG" in key else "Knab")))
            p = Policy(
                key=key,
                label=cfg.get("label", key),
                lender_name=lender,
                version=cfg.get("version", ""),
                json_text=json.dumps(cfg, ensure_ascii=False, indent=2),
                source_url=cfg.get("source_url", ""),
            )
            s.add(p)
        s.commit()


def sess() -> Session:
    with get_session() as s:
        yield s


@app.get("/", response_class=HTMLResponse)
def home(request: Request, s: Session = Depends(sess)):
    cases = s.exec(select(Case).order_by(Case.created_at.desc())).all()
    return templates.TemplateResponse("index.html", {"request": request, "cases": cases})


@app.get("/cases/search", response_class=HTMLResponse)
def case_search(
    request: Request,
    q: str = "",
    lender: str = "",
    with_nhg: str = "",
    entrepreneur_type: str = "",
    income_min: str = "",
    income_max: str = "",
    s: Session = Depends(sess),
):
    stmt = select(Case)
    if lender:
        stmt = stmt.where(Case.lender_name == lender)
    if with_nhg in ("true", "false"):
        stmt = stmt.where(Case.with_nhg == (with_nhg == "true"))
    if entrepreneur_type:
        stmt = stmt.where(Case.entrepreneur_type == entrepreneur_type)

    # free text across dossier/applicant
    if q:
        like = f"%{q}%"
        stmt = stmt.where((Case.dossier_nr.like(like)) | (Case.applicant_name.like(like)))

    try:
        if income_min:
            stmt = stmt.where(Case.last_income >= float(income_min))
        if income_max:
            stmt = stmt.where(Case.last_income <= float(income_max))
    except Exception:
        pass

    cases = s.exec(stmt.order_by(Case.created_at.desc())).all()
    lenders = sorted({p.lender_name for p in s.exec(select(Policy)).all()})
    return templates.TemplateResponse(
        "search.html",
        {
            "request": request,
            "cases": cases,
            "q": q,
            "lender": lender,
            "with_nhg": with_nhg,
            "entrepreneur_type": entrepreneur_type,
            "income_min": income_min,
            "income_max": income_max,
            "lenders": lenders,
        },
    )


@app.get("/cases/{case_id}/organogram", response_class=HTMLResponse)
def organogram(case_id: int, request: Request, s: Session = Depends(sess)):
    c = s.get(Case, case_id)
    if not c:
        raise HTTPException(404)
    nodes, edges = build_org_nodes_edges(case_id, s, max_entities=100)
    mermaid = build_mermaid(f"Dossier {c.dossier_nr}", nodes, edges)
    return templates.TemplateResponse(
        "organogram.html",
        {"request": request, "case": c, "mermaid": mermaid, "node_count": len(nodes) - 1, "edge_count": len(edges)},
    )


@app.get("/cases/{case_id}/multi", response_class=HTMLResponse)
def multi_lender(case_id: int, request: Request, enterprise_id: int = 0, scope: str = "auto", s: Session = Depends(sess)):
    c = s.get(Case, case_id)
    if not c:
        raise HTTPException(404)
    enterprises = s.exec(select(Enterprise).where(Enterprise.case_id == case_id)).all()
    if not enterprises:
        raise HTTPException(400, "Geen onderneming toegevoegd.")
    e = s.get(Enterprise, enterprise_id) if enterprise_id else enterprises[0]
    if e and e.case_id != case_id:
        e = enterprises[0]

    ownership_rows = s.exec(select(Ownership).where(Ownership.case_id == case_id)).all()
    groups = build_consolidation_groups([x.id for x in enterprises], ownership_rows)
    member_ids: List[int] = [e.id]
    years: List[YearInput]
    scope_used = "single"
    if scope in ("consolidated", "auto") and groups:
        grp = next((g for g in groups if e.id in g.member_enterprise_ids), None)
        if grp and len(grp.member_enterprise_ids) > 1:
            member_ids = grp.member_enterprise_ids
            years = build_consolidated_years(member_ids, s)
            scope_used = "consolidated"
        else:
            years = build_consolidated_years([e.id], s)
    else:
        years = build_consolidated_years([e.id], s)

    beneficial = compute_beneficial_map(case_id, s)
    eff = beneficial.get(e.id, {})
    effective_voting_pct = float(eff.get("voting_pct_total", c.share_pct))
    effective_dividend_pct = float(eff.get("dividend_share_pct_total", 0.0))

    policies = s.exec(select(Policy).order_by(Policy.lender_name, Policy.label)).all()
    current_month = date.today().month

    results = []
    for p in policies:
        pol = json.loads(p.json_text)
        calc = calculate_case(
            entrepreneur_type=c.entrepreneur_type,
            years=years,
            policy=pol,
            current_month=current_month,
            share_pct=effective_voting_pct,
            dividend_share_pct=effective_dividend_pct,
        )
        # Entity limits (optional)
        limits = pol.get("entity_limits", {}) if isinstance(pol, dict) else {}
        max_entities = int(limits.get("max_entities", 3))
        max_minority = int(limits.get("max_minority_participations", 2))
        enforce = bool(limits.get("enforce", False))
        status = "Voorleggen" if bool(pol.get("requires_manual_review", False)) else "Akkoord"

        if groups and len(groups) > max_entities:
            status = "Voorleggen"
            calc.notes.append(f"Structuur: {len(groups)} entiteiten(groepen) na 100%-consolidatie; policy-limiet is {max_entities}.")
            if enforce:
                status = "Niet mogelijk"
                calc.final_income = 0.0

        minorities = minority_participations(beneficial)
        if len(minorities) > max_minority:
            status = "Voorleggen"
            calc.notes.append(f"Structuur: {len(minorities)} minderheidsdeelnemingen; policy-limiet is {max_minority}.")
            if enforce:
                status = "Niet mogelijk"
                calc.final_income = 0.0

        # Simple decision rule: ratio’s
        for yf in calc.ratio_flags.values():
            if yf.get("current_ratio") == "niet akkoord" or yf.get("solvability") == "niet akkoord":
                status = "Voorleggen"
                break
        results.append({"policy": p, "status": status, "income": calc.final_income, "notes": calc.notes})

    return templates.TemplateResponse(
        "multi.html",
        {
            "request": request,
            "case": c,
            "enterprise": e,
            "enterprises": enterprises,
            "results": results,
            "scope_used": scope_used,
            "member_ids": member_ids,
        },
    )


@app.get("/cases/new", response_class=HTMLResponse)
def case_new(request: Request, s: Session = Depends(sess)):
    lenders = sorted({p.lender_name for p in s.exec(select(Policy)).all()})
    policies = s.exec(select(Policy).order_by(Policy.lender_name, Policy.label)).all()
    return templates.TemplateResponse(
        "case_new.html",
        {"request": request, "lenders": lenders, "policies": policies},
    )


@app.post("/cases/new")
def case_create(
    dossier_nr: str = Form(...),
    report_number: str = Form(""),
    client_number: str = Form(""),

    lender_name: str = Form(...),
    with_nhg: bool = Form(False),
    case_type: str = Form("IKV"),

    handler_name: str = Form(""),
    approver_name: str = Form(""),
    calculation_date: str = Form(""),
    validity_until: str = Form(""),

    # aanvrager
    applicant_lastname: str = Form(""),
    applicant_prefix: str = Form(""),
    applicant_initials: str = Form(""),
    applicant_gender: str = Form(""),
    applicant_dob: str = Form(""),
    applicant_birth_place: str = Form(""),
    applicant_street: str = Form(""),
    applicant_house_number: str = Form(""),
    applicant_postcode: str = Form(""),
    applicant_city: str = Form(""),
    applicant_phone: str = Form(""),
    applicant_email: str = Form(""),
    applicant_name: str = Form(""),

    # intermediair
    intermediary_office_name: str = Form(""),
    intermediary_afm_number: str = Form(""),
    intermediary_contact_name: str = Form(""),
    intermediary_email: str = Form(""),
    intermediary_phone: str = Form(""),

    entrepreneur_type: str = Form("IB"),
    share_pct: float = Form(100.0),
    years_category: str = Form(">=3"),
    years_category_reason: str = Form(""),

    expose_text: str = Form(""),
    notes: str = Form(""),
    assessment_result: str = Form(""),
    assessment_notes: str = Form(""),

    s: Session = Depends(sess),
):
    dob = date.fromisoformat(applicant_dob) if applicant_dob else None
    calc_dt = date.fromisoformat(calculation_date) if calculation_date else None
    valid_dt = date.fromisoformat(validity_until) if validity_until else None

    # display name fallback
    disp = applicant_name.strip()
    if not disp:
        parts = [applicant_initials.strip(), applicant_prefix.strip(), applicant_lastname.strip()]
        disp = " ".join([p for p in parts if p])

    c = Case(
        dossier_nr=dossier_nr,
        report_number=report_number,
        client_number=client_number,
        lender_name=lender_name,
        with_nhg=bool(with_nhg),
        case_type=case_type,
        handler_name=handler_name,
        approver_name=approver_name,
        calculation_date=calc_dt,
        validity_until=valid_dt,

        applicant_lastname=applicant_lastname,
        applicant_prefix=applicant_prefix,
        applicant_initials=applicant_initials,
        applicant_gender=applicant_gender,
        applicant_dob=dob,
        applicant_birth_place=applicant_birth_place,
        applicant_street=applicant_street,
        applicant_house_number=applicant_house_number,
        applicant_postcode=applicant_postcode,
        applicant_city=applicant_city,
        applicant_phone=applicant_phone,
        applicant_email=applicant_email,
        applicant_name=disp,

        intermediary_office_name=intermediary_office_name,
        intermediary_afm_number=intermediary_afm_number,
        intermediary_contact_name=intermediary_contact_name,
        intermediary_email=intermediary_email,
        intermediary_phone=intermediary_phone,

        entrepreneur_type=entrepreneur_type,
        share_pct=float(share_pct),
        years_category=years_category,
        years_category_reason=years_category_reason,

        expose_text=expose_text,
        notes=notes,
        assessment_result=assessment_result,
        assessment_notes=assessment_notes,
    )
    s.add(c)
    s.commit()
    s.refresh(c)
    return RedirectResponse(url=f"/cases/{c.id}", status_code=303)


@app.get("/cases/{case_id}", response_class=HTMLResponse)
def case_detail(case_id: int, request: Request, s: Session = Depends(sess)):
    c = s.get(Case, case_id)
    if not c:
        raise HTTPException(404)

    enterprises = s.exec(select(Enterprise).where(Enterprise.case_id == case_id).order_by(Enterprise.id)).all()
    docs = s.exec(select(UploadedDoc).where(UploadedDoc.case_id == case_id)).all()
    documents_used = s.exec(select(DocumentUsed).where(DocumentUsed.case_id == case_id).order_by(DocumentUsed.id)).all()
    checklist = s.exec(select(ControlChecklistItem).where(ControlChecklistItem.case_id == case_id).order_by(ControlChecklistItem.id)).all()
    decisions = s.exec(select(ControlDecision).where(ControlDecision.case_id == case_id).order_by(ControlDecision.id)).all()
    ownerships = s.exec(select(Ownership).where(Ownership.case_id == case_id).order_by(Ownership.id)).all()
    kyc = s.exec(select(KYCCheck).where(KYCCheck.case_id == case_id).order_by(KYCCheck.id)).all()

    # rechtsvormwijzigingen per onderneming
    legal_changes: Dict[int, List[LegalFormChange]] = {}
    if enterprises:
        ent_ids = [e.id for e in enterprises]
        rows = s.exec(select(LegalFormChange).where(LegalFormChange.enterprise_id.in_(ent_ids)).order_by(LegalFormChange.effective_date)).all()
        for r in rows:
            legal_changes.setdefault(r.enterprise_id, []).append(r)

    policies = s.exec(select(Policy).where(Policy.lender_name == c.lender_name)).all()
    # fallback: show all
    if not policies:
        policies = s.exec(select(Policy)).all()

    return templates.TemplateResponse(
        "case_detail.html",
        {
            "request": request,
            "case": c,
            "enterprises": enterprises,
            "docs": docs,
            "documents_used": documents_used,
            "checklist": checklist,
            "decisions": decisions,
            "ownerships": ownerships,
            "kyc": kyc,
            "legal_changes": legal_changes,
            "policies": policies,
        },
    )


@app.get("/cases/{case_id}/edit", response_class=HTMLResponse)
def case_edit(case_id: int, request: Request, s: Session = Depends(sess)):
    c = s.get(Case, case_id)
    if not c:
        raise HTTPException(404)
    lenders = sorted({p.lender_name for p in s.exec(select(Policy)).all()})
    return templates.TemplateResponse("case_edit.html", {"request": request, "case": c, "lenders": lenders})


@app.post("/cases/{case_id}/edit")
def case_edit_post(
    case_id: int,
    dossier_nr: str = Form(...),
    report_number: str = Form(""),
    client_number: str = Form(""),

    lender_name: str = Form(...),
    with_nhg: bool = Form(False),
    case_type: str = Form("IKV"),

    handler_name: str = Form(""),
    approver_name: str = Form(""),
    calculation_date: str = Form(""),
    validity_until: str = Form(""),

    applicant_lastname: str = Form(""),
    applicant_prefix: str = Form(""),
    applicant_initials: str = Form(""),
    applicant_gender: str = Form(""),
    applicant_dob: str = Form(""),
    applicant_birth_place: str = Form(""),
    applicant_street: str = Form(""),
    applicant_house_number: str = Form(""),
    applicant_postcode: str = Form(""),
    applicant_city: str = Form(""),
    applicant_phone: str = Form(""),
    applicant_email: str = Form(""),
    applicant_name: str = Form(""),

    intermediary_office_name: str = Form(""),
    intermediary_afm_number: str = Form(""),
    intermediary_contact_name: str = Form(""),
    intermediary_email: str = Form(""),
    intermediary_phone: str = Form(""),

    entrepreneur_type: str = Form("IB"),
    share_pct: float = Form(100.0),
    years_category: str = Form(">=3"),
    years_category_reason: str = Form(""),
    calc_enterprise_ids: str = Form(""),

    expose_text: str = Form(""),
    notes: str = Form(""),
    assessment_result: str = Form(""),
    assessment_notes: str = Form(""),

    s: Session = Depends(sess),
):
    c = s.get(Case, case_id)
    if not c:
        raise HTTPException(404)

    dob = date.fromisoformat(applicant_dob) if applicant_dob else None
    c.dossier_nr = dossier_nr
    c.report_number = report_number
    c.client_number = client_number

    c.lender_name = lender_name
    c.with_nhg = bool(with_nhg)
    c.case_type = case_type

    c.handler_name = handler_name
    c.approver_name = approver_name
    c.calculation_date = date.fromisoformat(calculation_date) if calculation_date else None
    c.validity_until = date.fromisoformat(validity_until) if validity_until else None

    c.applicant_lastname = applicant_lastname
    c.applicant_prefix = applicant_prefix
    c.applicant_initials = applicant_initials
    c.applicant_gender = applicant_gender
    c.applicant_dob = dob
    c.applicant_birth_place = applicant_birth_place
    c.applicant_street = applicant_street
    c.applicant_house_number = applicant_house_number
    c.applicant_postcode = applicant_postcode
    c.applicant_city = applicant_city
    c.applicant_phone = applicant_phone
    c.applicant_email = applicant_email

    disp = applicant_name.strip()
    if not disp:
        parts = [applicant_initials.strip(), applicant_prefix.strip(), applicant_lastname.strip()]
        disp = " ".join([p for p in parts if p])
    c.applicant_name = disp

    c.intermediary_office_name = intermediary_office_name
    c.intermediary_afm_number = intermediary_afm_number
    c.intermediary_contact_name = intermediary_contact_name
    c.intermediary_email = intermediary_email
    c.intermediary_phone = intermediary_phone

    c.entrepreneur_type = entrepreneur_type
    c.share_pct = float(share_pct)
    c.years_category = years_category
    c.years_category_reason = years_category_reason
    c.calc_enterprise_ids = calc_enterprise_ids

    c.expose_text = expose_text
    c.notes = notes
    c.assessment_result = assessment_result
    c.assessment_notes = assessment_notes

    s.add(c)
    s.commit()
    return RedirectResponse(url=f"/cases/{case_id}", status_code=303)


@app.get("/cases/{case_id}/enterprises/new", response_class=HTMLResponse)
def enterprise_new(case_id: int, request: Request, s: Session = Depends(sess)):
    c = s.get(Case, case_id)
    if not c:
        raise HTTPException(404)
    return templates.TemplateResponse("enterprise_new.html", {"request": request, "case": c})


@app.post("/cases/{case_id}/enterprises/new")
def enterprise_create(
    case_id: int,
    name: str = Form(...),
    statutory_name: str = Form(""),
    legal_form: str = Form(...),
    kvk_nr: str = Form(""),
    sbi_codes: str = Form(""),
    start_date: str = Form(""),

    address: str = Form(""),
    postcode_city: str = Form(""),
    incorporation_date: str = Form(""),
    registration_date: str = Form(""),

    websites: str = Form(""),
    activities: str = Form(""),

    kvk_address_check_private: str = Form(""),
    kvk_address_check_notes: str = Form(""),

    organogram: str = Form(""),

    corona_affected: bool = Form(False),
    corona_notes: str = Form(""),
    foreign_ok: bool = Form(True),
    foreign_notes: str = Form(""),

    google_check_done: bool = Form(False),
    google_check_date: str = Form(""),
    google_check_website: str = Form(""),
    google_check_company_pages: str = Form(""),
    google_check_social: str = Form(""),
    google_check_revenue_source: str = Form(""),
    google_check_conclusion: str = Form(""),

    accountant_name: str = Form(""),
    accountant_email: str = Form(""),

    enterprise_notes: str = Form(""),
    s: Session = Depends(sess),
):
    if not s.get(Case, case_id):
        raise HTTPException(404)

    dt = date.fromisoformat(start_date) if start_date else None
    inc_dt = date.fromisoformat(incorporation_date) if incorporation_date else None
    reg_dt = date.fromisoformat(registration_date) if registration_date else None
    g_dt = date.fromisoformat(google_check_date) if google_check_date else None

    e = Enterprise(
        case_id=case_id,
        name=name,
        statutory_name=statutory_name,
        legal_form=legal_form,
        kvk_nr=kvk_nr,
        sbi_codes=sbi_codes,
        start_date=dt,
        address=address,
        postcode_city=postcode_city,
        incorporation_date=inc_dt,
        registration_date=reg_dt,
        websites=websites,
        activities=activities,
        kvk_address_check_private=kvk_address_check_private,
        kvk_address_check_notes=kvk_address_check_notes,
        organogram=organogram,
        corona_affected=bool(corona_affected),
        corona_notes=corona_notes,
        foreign_ok=bool(foreign_ok),
        foreign_notes=foreign_notes,
        google_check_done=bool(google_check_done),
        google_check_date=g_dt,
        google_check_website=google_check_website,
        google_check_company_pages=google_check_company_pages,
        google_check_social=google_check_social,
        google_check_revenue_source=google_check_revenue_source,
        google_check_conclusion=google_check_conclusion,
        accountant_name=accountant_name,
        accountant_email=accountant_email,
        enterprise_notes=enterprise_notes,
    )
    s.add(e)
    s.commit()
    s.refresh(e)
    return RedirectResponse(url=f"/cases/{case_id}", status_code=303)


@app.get("/enterprises/{enterprise_id}/edit", response_class=HTMLResponse)
def enterprise_edit(enterprise_id: int, request: Request, s: Session = Depends(sess)):
    e = s.get(Enterprise, enterprise_id)
    if not e:
        raise HTTPException(404)
    c = s.get(Case, e.case_id)
    return templates.TemplateResponse("enterprise_edit.html", {"request": request, "case": c, "enterprise": e})


@app.post("/enterprises/{enterprise_id}/edit")
def enterprise_edit_post(
    enterprise_id: int,
    name: str = Form(...),
    statutory_name: str = Form(""),
    legal_form: str = Form(...),
    kvk_nr: str = Form(""),
    sbi_codes: str = Form(""),
    start_date: str = Form(""),

    address: str = Form(""),
    postcode_city: str = Form(""),
    incorporation_date: str = Form(""),
    registration_date: str = Form(""),

    websites: str = Form(""),
    activities: str = Form(""),

    kvk_address_check_private: str = Form(""),
    kvk_address_check_notes: str = Form(""),

    organogram: str = Form(""),

    corona_affected: bool = Form(False),
    corona_notes: str = Form(""),
    foreign_ok: bool = Form(True),
    foreign_notes: str = Form(""),

    google_check_done: bool = Form(False),
    google_check_date: str = Form(""),
    google_check_website: str = Form(""),
    google_check_company_pages: str = Form(""),
    google_check_social: str = Form(""),
    google_check_revenue_source: str = Form(""),
    google_check_conclusion: str = Form(""),

    accountant_name: str = Form(""),
    accountant_email: str = Form(""),

    enterprise_notes: str = Form(""),
    s: Session = Depends(sess),
):
    e = s.get(Enterprise, enterprise_id)
    if not e:
        raise HTTPException(404)

    e.name = name
    e.statutory_name = statutory_name
    e.legal_form = legal_form
    e.kvk_nr = kvk_nr
    e.sbi_codes = sbi_codes
    e.start_date = date.fromisoformat(start_date) if start_date else None

    e.address = address
    e.postcode_city = postcode_city
    e.incorporation_date = date.fromisoformat(incorporation_date) if incorporation_date else None
    e.registration_date = date.fromisoformat(registration_date) if registration_date else None

    e.websites = websites
    e.activities = activities

    e.kvk_address_check_private = kvk_address_check_private
    e.kvk_address_check_notes = kvk_address_check_notes

    e.organogram = organogram

    e.corona_affected = bool(corona_affected)
    e.corona_notes = corona_notes
    e.foreign_ok = bool(foreign_ok)
    e.foreign_notes = foreign_notes

    e.google_check_done = bool(google_check_done)
    e.google_check_date = date.fromisoformat(google_check_date) if google_check_date else None
    e.google_check_website = google_check_website
    e.google_check_company_pages = google_check_company_pages
    e.google_check_social = google_check_social
    e.google_check_revenue_source = google_check_revenue_source
    e.google_check_conclusion = google_check_conclusion

    e.accountant_name = accountant_name
    e.accountant_email = accountant_email

    e.enterprise_notes = enterprise_notes

    s.add(e)
    s.commit()
    return RedirectResponse(url=f"/cases/{e.case_id}", status_code=303)




@app.post("/enterprises/{enterprise_id}/kvk/prefill")
def enterprise_kvk_prefill(
    enterprise_id: int,
    use_test_env: bool = Form(False),
    s: Session = Depends(sess),
):
    e = s.get(Enterprise, enterprise_id)
    if not e:
        raise HTTPException(404)
    if not e.kvk_nr:
        raise HTTPException(400, "Geen KvK-nummer ingevuld.")
    try:
        prof = fetch_kvk_profile(e.kvk_nr, use_test=bool(use_test_env))
    except Exception as exc:
        raise HTTPException(400, f"KvK-ophalen mislukt: {exc}")

    if prof.get("name"):
        e.name = prof["name"]
    if prof.get("statutory_name"):
        e.statutory_name = prof["statutory_name"]
    if prof.get("legal_form") and not e.legal_form:
        e.legal_form = prof["legal_form"]
    if prof.get("registration_date") and not e.registration_date:
        try:
            e.registration_date = date.fromisoformat(str(prof["registration_date"])[:10])
        except Exception:
            pass
    if prof.get("start_date") and not e.start_date:
        try:
            e.start_date = date.fromisoformat(str(prof["start_date"])[:10])
        except Exception:
            pass
    if prof.get("address") and not e.address:
        e.address = prof["address"]
    sbi_lines = prof.get("sbi_lines") or []
    if sbi_lines and not e.sbi_codes:
        e.sbi_codes = "\n".join(sbi_lines)
    e.kvk_sync_source_url = str(prof.get("source_url", ""))
    e.kvk_sync_last_at = datetime.utcnow()
    s.add(e)
    s.commit()
    return RedirectResponse(url=f"/enterprises/{enterprise_id}/edit", status_code=303)


@app.get("/enterprises/{enterprise_id}/years/new", response_class=HTMLResponse)
def year_new(enterprise_id: int, request: Request, s: Session = Depends(sess)):
    e = s.get(Enterprise, enterprise_id)
    if not e:
        raise HTTPException(404)
    c = s.get(Case, e.case_id)
    years = s.exec(select(YearData).where(YearData.enterprise_id == enterprise_id).order_by(YearData.year.desc())).all()

    selected_year = request.query_params.get("year")
    selected = None
    if selected_year:
        try:
            sy = int(selected_year)
            selected = next((y for y in years if y.year == sy), None)
        except Exception:
            selected = None
    if selected is None and years:
        selected = years[0]

    year_detail = {"bs": {}, "pl": {}, "ib": {}}
    if selected:
        year_detail = {
            "bs": parse_json_blob(selected.bs_json),
            "pl": parse_json_blob(selected.pl_json),
            "ib": parse_json_blob(getattr(selected, "ib_json", "")),
        }

    return templates.TemplateResponse(
        "year_new.html",
        {
            "request": request,
            "case": c,
            "enterprise": e,
            "years": years,
            "selected": selected,
            "selected_year": selected.year if selected else None,
            "balance_groups": BALANCE_GROUPS,
            "pl_groups": PL_GROUPS,
            "ib_groups": IB_GROUPS,
            "year_detail": year_detail,
            "balance_formulas": BALANCE_TOTAL_FORMULAS,
            "pl_formulas": PL_TOTAL_FORMULAS,
            "pl_cost_components": PL_COST_COMPONENTS,
            "ib_formulas": IB_TOTAL_FORMULAS,
        },
    )


@app.post("/enterprises/{enterprise_id}/years/new")
def year_create(
    enterprise_id: int,
    year: int = Form(...),

    # periode
    period_start: str = Form(""),
    period_end: str = Form(""),
    period_months_override: float = Form(0.0),

    is_control_year: bool = Form(False),
    ytd_months: int = Form(0),

    # IB basis / kern
    saldo_fiscale_winst: float = Form(0.0),
    net_result_no_ib: float = Form(0.0),

    # controlejaar
    realized_income_ytd: float = Form(0.0),
    extrapolated_income: float = Form(0.0),
    prognose_income: float = Form(0.0),

    # overige box 1
    box1_wage_before_start: float = Form(0.0),
    box1_wage_during: float = Form(0.0),
    box1_benefits: float = Form(0.0),
    box1_row: float = Form(0.0),
    other_box1_income: float = Form(0.0),

    # correcties
    non_deductible_costs: float = Form(0.0),
    special_tax_expenses: float = Form(0.0),
    random_depreciation: float = Form(0.0),
    investment_deduction: float = Form(0.0),
    other_positive_fiscal: float = Form(0.0),
    incidental_income: float = Form(0.0),
    private_use_car: float = Form(0.0),
    other_negative_fiscal: float = Form(0.0),

    expired_rent_base: float = Form(0.0),
    expired_rent_factor_pct: float = Form(85.0),

    other_positive_avg: float = Form(0.0),
    other_negative_avg: float = Form(0.0),

    # DGA
    dga_salary: float = Form(0.0),
    dividend: float = Form(0.0),
    profit_after_corp_tax: float = Form(0.0),

    # P&L kern
    turnover_total: float = Form(0.0),
    cogs_total: float = Form(0.0),
    operating_costs_total: float = Form(0.0),
    depreciation_total: float = Form(0.0),
    financial_income_total: float = Form(0.0),
    financial_expense_total: float = Form(0.0),
    extraordinary_income_total: float = Form(0.0),
    extraordinary_expense_total: float = Form(0.0),

    # Balans kern
    inventories: float = Form(0.0),
    receivables: float = Form(0.0),
    other_current_assets: float = Form(0.0),
    cash: float = Form(0.0),

    creditors: float = Form(0.0),
    taxes_payable: float = Form(0.0),
    other_current_liabilities: float = Form(0.0),

    current_assets: float = Form(0.0),
    current_liabilities: float = Form(0.0),
    equity: float = Form(0.0),
    total_assets: float = Form(0.0),
    intangible_assets: float = Form(0.0),

    # vrije JSON detailopslag
    pl_json: str = Form(""),
    bs_json: str = Form(""),
    ib_json: str = Form(""),

    s: Session = Depends(sess),
):
    e = s.get(Enterprise, enterprise_id)
    if not e:
        raise HTTPException(404)

    ps = date.fromisoformat(period_start) if period_start else None
    pe = date.fromisoformat(period_end) if period_end else None

    existing = s.exec(select(YearData).where(YearData.enterprise_id == enterprise_id, YearData.year == year)).first()
    if existing:
        yd = existing
    else:
        yd = YearData(enterprise_id=enterprise_id, year=int(year))
        s.add(yd)

    bs_map = parse_json_blob(bs_json)
    pl_map = parse_json_blob(pl_json)
    ib_map = parse_json_blob(ib_json)
    derived = derive_core_from_detail(bs_map, pl_map, ib_map)

    yd.period_start = ps
    yd.period_end = pe
    yd.period_months_override = float(period_months_override or 0.0)

    yd.is_control_year = bool(is_control_year)
    yd.ytd_months = int(ytd_months or 0)

    yd.saldo_fiscale_winst = float(saldo_fiscale_winst or derived.get("saldo_fiscale_winst") or 0.0)
    yd.net_result_no_ib = float(net_result_no_ib or derived.get("net_result_no_ib") or 0.0)

    yd.realized_income_ytd = float(realized_income_ytd or 0.0)
    yd.extrapolated_income = float(extrapolated_income or 0.0)
    yd.prognose_income = float(prognose_income or derived.get("prognose_income") or 0.0)

    yd.box1_wage_before_start = float(box1_wage_before_start or derived.get("box1_wage_before_start") or 0.0)
    yd.box1_wage_during = float(box1_wage_during or derived.get("box1_wage_during") or 0.0)
    yd.box1_benefits = float(box1_benefits or derived.get("box1_benefits") or 0.0)
    yd.box1_row = float(box1_row or derived.get("box1_row") or 0.0)
    yd.other_box1_income = float(other_box1_income or derived.get("other_box1_income") or 0.0)

    yd.non_deductible_costs = float(non_deductible_costs or 0.0)
    yd.special_tax_expenses = float(special_tax_expenses or 0.0)
    yd.random_depreciation = float(random_depreciation or 0.0)
    yd.investment_deduction = float(investment_deduction or 0.0)
    yd.other_positive_fiscal = float(other_positive_fiscal or 0.0)
    yd.incidental_income = float(incidental_income or 0.0)
    yd.private_use_car = float(private_use_car or derived.get("private_use_car") or 0.0)
    yd.other_negative_fiscal = float(other_negative_fiscal or 0.0)

    yd.expired_rent_base = float(expired_rent_base or 0.0)
    yd.expired_rent_factor_pct = float(expired_rent_factor_pct or 85.0)

    yd.other_positive_avg = float(other_positive_avg or 0.0)
    yd.other_negative_avg = float(other_negative_avg or 0.0)

    yd.dga_salary = float(dga_salary or 0.0)
    yd.dividend = float(dividend or derived.get("dividend") or 0.0)
    yd.profit_after_corp_tax = float(profit_after_corp_tax or 0.0)

    yd.turnover_total = float(turnover_total or derived.get("turnover_total") or 0.0)
    yd.cogs_total = float(cogs_total or derived.get("cogs_total") or 0.0)
    yd.operating_costs_total = float(operating_costs_total or derived.get("operating_costs_total") or 0.0)
    yd.depreciation_total = float(depreciation_total or derived.get("depreciation_total") or 0.0)
    yd.financial_income_total = float(financial_income_total or derived.get("financial_income_total") or 0.0)
    yd.financial_expense_total = float(financial_expense_total or derived.get("financial_expense_total") or 0.0)
    yd.extraordinary_income_total = float(extraordinary_income_total or derived.get("extraordinary_income_total") or 0.0)
    yd.extraordinary_expense_total = float(extraordinary_expense_total or derived.get("extraordinary_expense_total") or 0.0)

    yd.inventories = float(inventories or derived.get("inventories") or 0.0)
    yd.receivables = float(receivables or derived.get("receivables") or 0.0)
    yd.other_current_assets = float(other_current_assets or derived.get("other_current_assets") or 0.0)
    yd.cash = float(cash or derived.get("cash") or 0.0)

    yd.creditors = float(creditors or derived.get("creditors") or 0.0)
    yd.taxes_payable = float(taxes_payable or derived.get("taxes_payable") or 0.0)
    yd.other_current_liabilities = float(other_current_liabilities or derived.get("other_current_liabilities") or 0.0)

    yd.current_assets = float(current_assets or derived.get("current_assets") or 0.0)
    yd.current_liabilities = float(current_liabilities or derived.get("current_liabilities") or 0.0)
    yd.equity = float(equity or derived.get("equity") or 0.0)
    yd.total_assets = float(total_assets or derived.get("total_assets") or 0.0)
    yd.intangible_assets = float(intangible_assets or derived.get("intangible_assets") or 0.0)

    yd.pl_json = pl_json or ""
    yd.bs_json = bs_json or ""
    yd.ib_json = ib_json or ""

    s.commit()
    return RedirectResponse(url=f"/enterprises/{enterprise_id}/years/new?year={year}", status_code=303)

@app.post("/cases/{case_id}/upload")
def upload_doc(case_id: int, file: UploadFile = File(...), enterprise_id: int = Form(0), category: str = Form(""), s: Session = Depends(sess)):
    c = s.get(Case, case_id)
    if not c:
        raise HTTPException(404)

    dest = UPLOAD_DIR / f"case_{case_id}"
    dest.mkdir(parents=True, exist_ok=True)

    safe_name = file.filename.replace("/", "_").replace("\\", "_")
    out_path = dest / safe_name

    with out_path.open("wb") as f:
        f.write(file.file.read())

    doc = UploadedDoc(case_id=case_id, enterprise_id=(enterprise_id or None), filename=safe_name, stored_path=str(out_path), category=category or "")
    s.add(doc)
    s.commit()

    return RedirectResponse(url=f"/cases/{case_id}", status_code=303)


@app.get("/cases/{case_id}/ownership/new", response_class=HTMLResponse)
def ownership_new(case_id: int, request: Request, s: Session = Depends(sess)):
    c = s.get(Case, case_id)
    if not c:
        raise HTTPException(404)
    enterprises = s.exec(select(Enterprise).where(Enterprise.case_id == case_id).order_by(Enterprise.name)).all()
    return templates.TemplateResponse("ownership_new.html", {"request": request, "case": c, "enterprises": enterprises})


@app.post("/cases/{case_id}/ownership/new")
def ownership_create(
    case_id: int,
    owner_kind: str = Form("PERSON"),
    owner_enterprise_id: int = Form(0),
    owner_label: str = Form(""),
    owned_enterprise_id: int = Form(...),
    share_pct: float = Form(0.0),
    voting_pct: float = Form(0.0),
    dividend_entitled: bool = Form(True),
    notes: str = Form(""),
    s: Session = Depends(sess),
):
    c = s.get(Case, case_id)
    if not c:
        raise HTTPException(404)
    o = Ownership(
        case_id=case_id,
        owner_kind=owner_kind,
        owner_enterprise_id=(int(owner_enterprise_id) if owner_kind == "ENTERPRISE" and int(owner_enterprise_id) else None),
        owner_label=(owner_label or c.applicant_name),
        owned_enterprise_id=int(owned_enterprise_id),
        share_pct=float(share_pct),
        voting_pct=float(voting_pct),
        dividend_entitled=bool(dividend_entitled),
        notes=notes,
    )
    s.add(o)
    s.commit()
    return RedirectResponse(url=f"/cases/{case_id}", status_code=303)


@app.post("/ownership/{ownership_id}/delete")
def ownership_delete(ownership_id: int, s: Session = Depends(sess)):
    o = s.get(Ownership, ownership_id)
    if not o:
        raise HTTPException(404)
    case_id = o.case_id
    s.delete(o)
    s.commit()
    return RedirectResponse(url=f"/cases/{case_id}", status_code=303)


@app.get("/enterprises/{enterprise_id}/legal_changes/new", response_class=HTMLResponse)
def legal_change_new(enterprise_id: int, request: Request, s: Session = Depends(sess)):
    e = s.get(Enterprise, enterprise_id)
    if not e:
        raise HTTPException(404)
    c = s.get(Case, e.case_id)
    changes = s.exec(select(LegalFormChange).where(LegalFormChange.enterprise_id == enterprise_id).order_by(LegalFormChange.effective_date)).all()
    return templates.TemplateResponse("legal_change_new.html", {"request": request, "case": c, "enterprise": e, "changes": changes})


@app.post("/enterprises/{enterprise_id}/legal_changes/new")
def legal_change_create(
    enterprise_id: int,
    effective_date: str = Form(""),
    from_legal_form: str = Form(""),
    to_legal_form: str = Form(""),
    kvk_nr_old: str = Form(""),
    kvk_nr_new: str = Form(""),
    notes: str = Form(""),
    s: Session = Depends(sess),
):
    e = s.get(Enterprise, enterprise_id)
    if not e:
        raise HTTPException(404)
    ch = LegalFormChange(
        enterprise_id=enterprise_id,
        effective_date=(date.fromisoformat(effective_date) if effective_date else None),
        from_legal_form=from_legal_form,
        to_legal_form=to_legal_form,
        kvk_nr_old=kvk_nr_old,
        kvk_nr_new=kvk_nr_new,
        notes=notes,
    )
    s.add(ch)
    s.commit()
    return RedirectResponse(url=f"/enterprises/{enterprise_id}/legal_changes/new", status_code=303)


@app.post("/legal_changes/{change_id}/delete")
def legal_change_delete(change_id: int, s: Session = Depends(sess)):
    ch = s.get(LegalFormChange, change_id)
    if not ch:
        raise HTTPException(404)
    enterprise_id = ch.enterprise_id
    s.delete(ch)
    s.commit()
    return RedirectResponse(url=f"/enterprises/{enterprise_id}/legal_changes/new", status_code=303)


@app.get("/cases/{case_id}/kyc/new", response_class=HTMLResponse)
def kyc_new(case_id: int, request: Request, s: Session = Depends(sess)):
    c = s.get(Case, case_id)
    if not c:
        raise HTTPException(404)
    checks = s.exec(select(KYCCheck).where(KYCCheck.case_id == case_id).order_by(KYCCheck.id)).all()
    return templates.TemplateResponse("kyc_new.html", {"request": request, "case": c, "checks": checks})


@app.post("/cases/{case_id}/kyc/new")
def kyc_create(
    case_id: int,
    check_type: str = Form(...),
    checked_on: str = Form(""),
    input_data: str = Form(""),
    result: str = Form(""),
    source_url: str = Form(""),
    notes: str = Form(""),
    s: Session = Depends(sess),
):
    c = s.get(Case, case_id)
    if not c:
        raise HTTPException(404)
    row = KYCCheck(
        case_id=case_id,
        check_type=check_type,
        checked_on=(date.fromisoformat(checked_on) if checked_on else None),
        input_data=input_data,
        result=result,
        source_url=source_url,
        notes=notes,
    )
    s.add(row)
    s.commit()
    return RedirectResponse(url=f"/cases/{case_id}", status_code=303)


@app.post("/kyc/{check_id}/delete")
def kyc_delete(check_id: int, s: Session = Depends(sess)):
    row = s.get(KYCCheck, check_id)
    if not row:
        raise HTTPException(404)
    case_id = row.case_id
    s.delete(row)
    s.commit()
    return RedirectResponse(url=f"/cases/{case_id}", status_code=303)


@app.get("/cases/{case_id}/documents/new", response_class=HTMLResponse)
def documents_used_new(case_id: int, request: Request, s: Session = Depends(sess)):
    c = s.get(Case, case_id)
    if not c:
        raise HTTPException(404)
    enterprises = s.exec(select(Enterprise).where(Enterprise.case_id == case_id).order_by(Enterprise.id)).all()
    rows = s.exec(select(DocumentUsed).where(DocumentUsed.case_id == case_id).order_by(DocumentUsed.id)).all()
    return templates.TemplateResponse(
        "documents_new.html",
        {"request": request, "case": c, "enterprises": enterprises, "documents_used": rows},
    )


@app.post("/cases/{case_id}/documents/new")
def documents_used_create(
    case_id: int,
    category: str = Form("Privé/Algemeen"),
    enterprise_id: str = Form(""),
    doc_type: str = Form(""),
    filename: str = Form(""),
    notes: str = Form(""),
    s: Session = Depends(sess),
):
    c = s.get(Case, case_id)
    if not c:
        raise HTTPException(404)
    eid = int(enterprise_id) if enterprise_id else None
    row = DocumentUsed(
        case_id=case_id,
        enterprise_id=eid,
        category=category or "Privé/Algemeen",
        doc_type=doc_type or "",
        filename=filename or "",
        notes=notes or "",
    )
    s.add(row)
    s.commit()
    return RedirectResponse(url=f"/cases/{case_id}", status_code=303)


@app.post("/documents/{doc_id}/delete")
def documents_used_delete(doc_id: int, s: Session = Depends(sess)):
    row = s.get(DocumentUsed, doc_id)
    if not row:
        raise HTTPException(404)
    case_id = row.case_id
    s.delete(row)
    s.commit()
    return RedirectResponse(url=f"/cases/{case_id}", status_code=303)


@app.get("/cases/{case_id}/controls/checklist/new", response_class=HTMLResponse)
def controls_checklist_new(case_id: int, request: Request, s: Session = Depends(sess)):
    c = s.get(Case, case_id)
    if not c:
        raise HTTPException(404)
    return templates.TemplateResponse("controls_checklist_new.html", {"request": request, "case": c})


@app.post("/cases/{case_id}/controls/checklist/new")
def controls_checklist_create(
    case_id: int,
    control_point: str = Form(...),
    result: str = Form("N.v.t."),
    handler_name: str = Form(""),
    notes: str = Form(""),
    s: Session = Depends(sess),
):
    c = s.get(Case, case_id)
    if not c:
        raise HTTPException(404)
    row = ControlChecklistItem(
        case_id=case_id,
        control_point=control_point,
        result=result or "N.v.t.",
        checked_at=datetime.utcnow(),
        handler_name=handler_name or c.handler_name,
        notes=notes or "",
    )
    s.add(row)
    s.commit()
    return RedirectResponse(url=f"/cases/{case_id}", status_code=303)


@app.post("/controls/checklist/{item_id}/delete")
def controls_checklist_delete(item_id: int, s: Session = Depends(sess)):
    row = s.get(ControlChecklistItem, item_id)
    if not row:
        raise HTTPException(404)
    case_id = row.case_id
    s.delete(row)
    s.commit()
    return RedirectResponse(url=f"/cases/{case_id}", status_code=303)


@app.get("/cases/{case_id}/controls/decisions/new", response_class=HTMLResponse)
def controls_decision_new(case_id: int, request: Request, s: Session = Depends(sess)):
    c = s.get(Case, case_id)
    if not c:
        raise HTTPException(404)
    return templates.TemplateResponse("controls_decision_new.html", {"request": request, "case": c})


@app.post("/cases/{case_id}/controls/decisions/new")
def controls_decision_create(
    case_id: int,
    step_nr: int = Form(1),
    status: str = Form(""),
    handler_name: str = Form(""),
    notes: str = Form(""),
    s: Session = Depends(sess),
):
    c = s.get(Case, case_id)
    if not c:
        raise HTTPException(404)
    row = ControlDecision(
        case_id=case_id,
        step_nr=int(step_nr or 0),
        status=status or "",
        decided_at=datetime.utcnow(),
        handler_name=handler_name or c.handler_name,
        notes=notes or "",
    )
    s.add(row)
    s.commit()
    return RedirectResponse(url=f"/cases/{case_id}", status_code=303)


@app.post("/controls/decisions/{decision_id}/delete")
def controls_decision_delete(decision_id: int, s: Session = Depends(sess)):
    row = s.get(ControlDecision, decision_id)
    if not row:
        raise HTTPException(404)
    case_id = row.case_id
    s.delete(row)
    s.commit()
    return RedirectResponse(url=f"/cases/{case_id}", status_code=303)


@app.get("/policies", response_class=HTMLResponse)
def policies(request: Request, s: Session = Depends(sess)):
    items = s.exec(select(Policy).order_by(Policy.lender_name, Policy.label)).all()
    return templates.TemplateResponse("policies.html", {"request": request, "policies": items})


@app.get("/policies/new", response_class=HTMLResponse)
def policy_new(request: Request):
    return templates.TemplateResponse("policy_new.html", {"request": request})


@app.post("/policies/new")
def policy_create(
    key: str = Form(...),
    label: str = Form(...),
    lender_name: str = Form(...),
    version: str = Form(""),
    source_url: str = Form(""),
    json_text: str = Form(...),
    s: Session = Depends(sess),
):
    # validate json
    try:
        json.loads(json_text)
    except Exception as e:
        raise HTTPException(400, f"Ongeldige JSON: {e}")

    p = Policy(key=key, label=label, lender_name=lender_name, version=version, source_url=source_url, json_text=json_text)
    s.add(p)
    s.commit()
    return RedirectResponse(url="/policies", status_code=303)


@app.get("/cases/{case_id}/calculate", response_class=HTMLResponse)
def calculate(
    case_id: int,
    request: Request,
    policy_key: str = "",
    enterprise_id: int = 0,
    scope: str = "auto",  # single / consolidated / auto
    s: Session = Depends(sess),
):
    c = s.get(Case, case_id)
    if not c:
        raise HTTPException(404)

    enterprises = s.exec(select(Enterprise).where(Enterprise.case_id == case_id)).all()
    if not enterprises:
        raise HTTPException(400, "Geen onderneming toegevoegd.")

    # kies onderneming
    e = None
    if enterprise_id:
        e = s.get(Enterprise, int(enterprise_id))
        if e and e.case_id != case_id:
            e = None
    if not e:
        e = enterprises[0]

    # Optioneel: risicosector check (voorbeeld: Knab SBI-lijst).
    # Plaats het Excel-bestand in app/data/ als je deze check wilt activeren.
    knab_excel = APP_DIR / "data" / "Knab_Hypotheek_Risicosectoren_Zakelijk_inkomen.xlsx"
    excluded = load_excluded_sbi_from_knab_excel(knab_excel) if knab_excel.exists() else set()
    risk_result = check_sbi_codes(e.sbi_codes, excluded) if excluded else None
    # pick policy

    # pick policy
    pol = None
    if policy_key:
        pol = s.exec(select(Policy).where(Policy.key == policy_key)).first()
    if not pol:
        pol = s.exec(select(Policy).where(Policy.lender_name == c.lender_name)).first()
    if not pol:
        pol = s.exec(select(Policy)).first()

    policy = json.loads(pol.json_text)

    # Structuur: consolidation groups + minority participations
    ownership_rows = s.exec(select(Ownership).where(Ownership.case_id == case_id)).all()
    groups = build_consolidation_groups([x.id for x in enterprises], ownership_rows)

    # bepaal effectief belang uit ownership-structuur (indien aanwezig)
    beneficial = compute_beneficial_map(case_id, s)
    eff = beneficial.get(e.id, {})
    effective_voting_pct = float(eff.get("voting_pct_total", c.share_pct))
    effective_dividend_pct = float(eff.get("dividend_share_pct_total", 0.0))

    # years: single vs consolidated
    years: List[YearInput]
    scope_used = scope
    member_ids: List[int] = [e.id]
    if scope in ("consolidated", "auto") and groups:
        # find group containing selected enterprise
        grp = next((g for g in groups if e.id in g.member_enterprise_ids), None)
        if grp and len(grp.member_enterprise_ids) > 1:
            member_ids = grp.member_enterprise_ids
            years = build_consolidated_years(member_ids, s)
            scope_used = "consolidated"
        else:
            years_db = s.exec(select(YearData).where(YearData.enterprise_id == e.id)).all()
            years = [yd_to_yearinput(yd) for yd in years_db]
            scope_used = "single"
    else:
        years_db = s.exec(select(YearData).where(YearData.enterprise_id == e.id)).all()
        years = [yd_to_yearinput(yd) for yd in years_db]
        scope_used = "single"

    # current month (can be overridden later via UI)
    current_month = date.today().month

    calc = calculate_case(
        entrepreneur_type=c.entrepreneur_type,
        years=years,
        policy=policy,
        current_month=current_month,
        share_pct=effective_voting_pct,
        dividend_share_pct=effective_dividend_pct,
    )

    # entity limit rules (policy-configurable)
    limits = policy.get("entity_limits", {}) if isinstance(policy, dict) else {}
    max_entities = int(limits.get("max_entities", 3))
    max_minority = int(limits.get("max_minority_participations", 2))
    enforce = bool(limits.get("enforce", False))
    notes_extra: List[str] = []

    if groups and len(groups) > max_entities:
        notes_extra.append(f"Structuur: {len(groups)} entiteiten(groepen) na 100%-consolidatie; policy-limiet is {max_entities}.")
        if enforce:
            calc.final_income = 0.0
            notes_extra.append("Beleid: inkomen op nihil gezet i.v.m. overschrijding max entiteiten.")

    minorities = minority_participations(beneficial)
    if len(minorities) > max_minority:
        notes_extra.append(f"Structuur: {len(minorities)} minderheidsdeelnemingen; policy-limiet is {max_minority}.")
        if enforce:
            calc.final_income = 0.0
            notes_extra.append("Beleid: inkomen op nihil gezet i.v.m. te veel minderheidsdeelnemingen.")

    if bool(policy.get("requires_manual_review", False)):
        notes_extra.append(
            "BELEIDSVERIFICATIE VERPLICHT: "
            + str(policy.get("manual_review_reason") or "Dit profiel kan niet automatisch worden gefiatteerd.")
        )
    calc.notes.extend(notes_extra)

    year_breakdowns = []
    for y in sorted(years, key=lambda z: z.year):
        base = float(y.saldo_fiscale_winst or y.net_result_no_ib or 0.0)
        positives = float(y.non_deductible_costs) + float(y.special_tax_expenses) + float(y.random_depreciation) + float(y.investment_deduction) + float(y.other_positive_fiscal) + (float(y.expired_rent_base) * (float(y.expired_rent_factor_pct or 85.0) / 100.0))
        negatives = float(y.incidental_income) + float(y.private_use_car) + float(y.other_negative_fiscal)
        total = box1_income_after_corrections(y, policy)
        ratios_one = calc_ratios(y)
        year_breakdowns.append({
            "year": y.year,
            "period_months": period_months(y),
            "is_control_year": bool(y.is_control_year),
            "base": base,
            "positives": positives,
            "negatives": negatives,
            "other_box1_income": float(y.other_box1_income),
            "total": total,
            "realized_income_ytd": float(y.realized_income_ytd or 0.0),
            "extrapolated_income": float(y.extrapolated_income or 0.0),
            "prognose_income": float(y.prognose_income or 0.0),
            "turnover_total": float(y.turnover_total or 0.0),
            "cogs_total": float(y.cogs_total or 0.0),
            "ratios": ratios_one,
        })

    core_points = [
        f"Toetsinkomen: € {calc.final_income:,.2f}".replace(',', 'X').replace('.', ',').replace('X','.'),
        f"Gemiddelde na periodemeting: € {calc.base_income_avg:,.2f}".replace(',', 'X').replace('.', ',').replace('X','.'),
        f"Maximering laatste volledige jaar: € {calc.capped_to_last_year:,.2f}".replace(',', 'X').replace('.', ',').replace('X','.'),
    ]
    if calc.control_year:
        core_points.append(f"Controlejaar {calc.control_year}: geëxtrapoleerd € {calc.control_year_extrapolated:,.2f} / prognose € {calc.control_year_prognose:,.2f}".replace(',', 'X').replace('.', ',').replace('X','.'))

    # Store last calculation on Case for search/filtering
    c.last_income = float(calc.final_income)
    c.last_policy_key = pol.key
    c.last_calc_at = datetime.utcnow()
    s.add(c)
    s.commit()
    return templates.TemplateResponse(
        "calculate.html",
        {
            "request": request,
            "case": c,
            "enterprise": e,
            "enterprises": enterprises,
            "policy": pol,
            "calc": calc,
            "current_month": current_month,
            "risk_result": risk_result,
            "beneficial": beneficial,
            "effective_voting_pct": effective_voting_pct,
            "effective_dividend_pct": effective_dividend_pct,
            "scope_used": scope_used,
            "member_ids": member_ids,
            "groups": groups,
            "year_breakdowns": year_breakdowns,
            "core_points": core_points,
        },
    )


@app.get("/cases/{case_id}/report.pdf")
def report_pdf(case_id: int, policy_key: str = "", enterprise_id: int = 0, scope: str = "auto", s: Session = Depends(sess)):
    c = s.get(Case, case_id)
    if not c:
        raise HTTPException(404)

    enterprises = s.exec(select(Enterprise).where(Enterprise.case_id == case_id)).all()
    if not enterprises:
        raise HTTPException(400, "Geen onderneming toegevoegd.")
    e = None
    if enterprise_id:
        e = s.get(Enterprise, int(enterprise_id))
        if e and e.case_id != case_id:
            e = None
    if not e:
        e = enterprises[0]
    ownership_rows = s.exec(select(Ownership).where(Ownership.case_id == case_id)).all()
    groups = build_consolidation_groups([x.id for x in enterprises], ownership_rows)
    member_ids: List[int] = [e.id]
    scope_used = scope
    if scope in ("consolidated", "auto") and groups:
        grp = next((g for g in groups if e.id in g.member_enterprise_ids), None)
        if grp and len(grp.member_enterprise_ids) > 1:
            member_ids = grp.member_enterprise_ids
            years = build_consolidated_years(member_ids, s)
            scope_used = "consolidated"
        else:
            years_db = s.exec(select(YearData).where(YearData.enterprise_id == e.id)).all()
            years = [yd_to_yearinput(yd) for yd in years_db]
            scope_used = "single"
    else:
        years_db = s.exec(select(YearData).where(YearData.enterprise_id == e.id)).all()
        years = [yd_to_yearinput(yd) for yd in years_db]
        scope_used = "single"

    pol = None
    if policy_key:
        pol = s.exec(select(Policy).where(Policy.key == policy_key)).first()
    if not pol:
        pol = s.exec(select(Policy).where(Policy.lender_name == c.lender_name)).first()
    if not pol:
        pol = s.exec(select(Policy)).first()

    policy = json.loads(pol.json_text)
    current_month = date.today().month

    beneficial = compute_beneficial_map(case_id, s)
    eff = beneficial.get(e.id, {})
    effective_voting_pct = float(eff.get("voting_pct_total", c.share_pct))
    effective_dividend_pct = float(eff.get("dividend_share_pct_total", 0.0))

    calc = calculate_case(
        entrepreneur_type=c.entrepreneur_type,
        years=years,
        policy=policy,
        current_month=current_month,
        share_pct=effective_voting_pct,
        dividend_share_pct=effective_dividend_pct,
    )

    # 'maximaal te onttrekken' op basis van laatste jaar in years
    if years:
        latest = sorted(years, key=lambda z: z.year)[-1]
        w = max_withdrawable_working_capital(
            current_assets=latest.current_assets,
            current_liabilities=latest.current_liabilities,
            equity=latest.equity,
            total_assets=latest.total_assets,
            liquidity_min=float(policy.get("liquidity_min", 1.0)),
            solvability_min=float(policy.get("solvability_min", 0.25)),
        )
    else:
        w = 0.0

    # Organogram image for PDF
    org_nodes, org_edges = build_org_nodes_edges(case_id, s, max_entities=int(policy.get("organogram_max_entities", 100)))
    org_png = REPORT_DIR / f"case_{case_id}_organogram.png"
    try:
        render_organogram_png(out_path=org_png, nodes=org_nodes, edges=org_edges, title=f"Organogram – dossier {c.dossier_nr}")
        org_png_path = str(org_png)
    except Exception:
        org_png_path = ""

    out = REPORT_DIR / f"case_{case_id}_inkomensanalyse.pdf"

    # Build extra sections similar to uitgebreide IKV
    kyc_rows = s.exec(select(KYCCheck).where(KYCCheck.case_id == case_id).order_by(KYCCheck.id)).all()
    kyc_lines = [
        f"{r.check_type} ({r.checked_on or '-'}) → {r.result or 'Onbekend'}" + (f" | {r.source_url}" if r.source_url else "")
        for r in kyc_rows
    ]

    legal_rows = s.exec(
        select(LegalFormChange).where(LegalFormChange.enterprise_id.in_([x.id for x in enterprises])).order_by(LegalFormChange.effective_date)
    ).all()
    legal_lines = [
        f"Enterprise #{r.enterprise_id}: {r.from_legal_form} → {r.to_legal_form} ({r.effective_date or '-'})" for r in legal_rows
    ]

    struct_lines = []
    for o in ownership_rows:
        owner = c.applicant_name if o.owner_kind == "PERSON" else f"Enterprise #{o.owner_enterprise_id}"
        owned = f"Enterprise #{o.owned_enterprise_id}"
        vp = float(o.voting_pct) if float(o.voting_pct) else float(o.share_pct)
        struct_lines.append(
            f"{owner} → {owned}: {o.share_pct:.2f}% belang / {vp:.2f}% stem" + (" (geen dividend)" if not o.dividend_entitled else "")
        )
    if groups:
        struct_lines.append(f"Consolidatiegroepen (100%): {len(groups)}")
        for g in groups:
            struct_lines.append(f"Groep root {g.root_enterprise_id}: {', '.join(str(i) for i in g.member_enterprise_ids)}")

    ent_lines = []
    for ent in enterprises:
        ent_lines.append(f"{ent.name} ({ent.legal_form}) KvK {ent.kvk_nr or '-'} | SBI {ent.sbi_codes or '-'}")
        if not ent.foreign_ok or ent.foreign_notes:
            ent_lines.append(f"  Buitenland: {'Akkoord' if ent.foreign_ok else 'Niet akkoord'}. {ent.foreign_notes or ''}".strip())
        if ent.corona_affected:
            ent_lines.append(f"  Corona: impact gemeld. {ent.corona_notes or ''}".strip())

    # Documentenlijst + controles
    docs_used_rows = s.exec(select(DocumentUsed).where(DocumentUsed.case_id == case_id).order_by(DocumentUsed.id)).all()
    docs_used_lines = [f"{d.category}: {d.doc_type} — {d.filename}" + (f" ({d.notes})" if d.notes else "") for d in docs_used_rows]

    checklist_rows = s.exec(select(ControlChecklistItem).where(ControlChecklistItem.case_id == case_id).order_by(ControlChecklistItem.id)).all()
    checklist_lines = [
        f"{r.control_point}: {r.result}" + (f" ({r.handler_name})" if r.handler_name else "") + (f" — {r.notes}" if r.notes else "")
        for r in checklist_rows
    ]

    decision_rows = s.exec(select(ControlDecision).where(ControlDecision.case_id == case_id).order_by(ControlDecision.step_nr, ControlDecision.id)).all()
    decision_lines = [
        f"Stap {r.step_nr}: {r.status}" + (f" ({r.handler_name})" if r.handler_name else "") + (f" — {r.notes}" if r.notes else "")
        for r in decision_rows
    ]

    case_meta = {
        "dossier_nr": c.dossier_nr,
        "lender_name": c.lender_name,
        "handler_name": c.handler_name,
        "approver_name": c.approver_name,
        "calculation_date": c.calculation_date,
        "validity_until": c.validity_until,
        "applicant_name": c.applicant_name,
        "applicant_dob": c.applicant_dob,
        "applicant_address": f"{(c.applicant_street or '').strip()} {(c.applicant_house_number or '').strip()}".strip(),
        "applicant_postcode_city": f"{(c.applicant_postcode or '').strip()} {(c.applicant_city or '').strip()}".strip(),
    }
    enterprise_meta = {
        "name": e.name,
        "legal_form": e.legal_form,
        "kvk_nr": e.kvk_nr,
        "start_date": e.start_date,
        "address": e.address,
        "postcode_city": e.postcode_city,
        "sbi_codes": e.sbi_codes,
    }
    policy_meta = {"label": pol.label, "key": pol.key}

    build_income_report_pdf(
        out,
        case=case_meta,
        enterprise=enterprise_meta,
        policy=policy_meta,
        calc=calc,
        max_withdrawable=w,
        extra_notes=[
            f"Effectief stemrecht (indicatief) voor '{e.name}': {effective_voting_pct:.2f}% (op basis van ingevoerde structuur).",
            f"Effectief dividendbelang (indicatief) voor '{e.name}': {effective_dividend_pct:.2f}%.",
            f"Berekeningsscope: {scope_used} (entiteiten: {', '.join(str(i) for i in member_ids)}).",
            "Bronnen/acceptatiegidsen moeten per maatschappij worden gekoppeld in Policies.",
        ],
        organogram_png_path=org_png_path,
        sections={
            "Ondernemingen": ent_lines,
            "Structuur / belangen": struct_lines,
            "Rechtsvormwijzigingen": legal_lines,
            "KYC / broncontroles": kyc_lines,
            "Documentenlijst": docs_used_lines,
            "Maatschappij specifieke controles": checklist_lines,
            "Beslissingen inkomensvaststelling": decision_lines,
        },
    )

    return FileResponse(path=str(out), filename=out.name, media_type="application/pdf")
