from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class Policy(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    key: str = Field(index=True, unique=True)
    label: str
    lender_name: str = Field(index=True)
    version: str = ""
    json_text: str
    source_url: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Case(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    # Rapport/meta
    dossier_nr: str = Field(index=True)
    report_number: str = ""  # bv. BL749317
    client_number: str = ""  # bv. 28009

    lender_name: str = Field(index=True)
    with_nhg: bool = False
    case_type: str = "IKV"  # IKV / Inkomensanalyse / Overig

    handler_name: str = ""  # Behandelaar
    approver_name: str = ""  # Fiatteur
    calculation_date: Optional[date] = None
    validity_until: Optional[date] = None

    # Aanvrager (samenvatting + basisgegevens)
    applicant_lastname: str = ""
    applicant_prefix: str = ""
    applicant_initials: str = ""
    applicant_gender: str = ""  # M/V/X
    applicant_dob: Optional[date] = None
    applicant_birth_place: str = ""

    applicant_street: str = ""
    applicant_house_number: str = ""
    applicant_postcode: str = ""
    applicant_city: str = ""

    applicant_phone: str = ""
    applicant_email: str = ""

    # Convenience: weergegeven naam
    applicant_name: str = ""  # optioneel (kan automatisch uit onderdelen)

    # Intermediair
    intermediary_office_name: str = ""
    intermediary_afm_number: str = ""
    intermediary_contact_name: str = ""
    intermediary_email: str = ""
    intermediary_phone: str = ""

    # Ondernemersprofiel
    entrepreneur_type: str = "IB"  # IB / DGA
    share_pct: float = 100.0  # fallback; gebruik Structuur voor holdings

    years_category: str = ">=3"  # <1 / 1-3 / >=3
    years_category_reason: str = ""

    # Welke ondernemingen tellen mee in de berekening (komma-gescheiden ids). Leeg = auto.
    calc_enterprise_ids: str = ""

    # Laatst berekende waarden (handig voor zoeken/filters).
    last_income: float = 0.0
    last_policy_key: str = ""
    last_calc_at: Optional[datetime] = None

    # Narratief / Exposé
    expose_text: str = ""
    notes: str = ""  # dossiernotities / expert judgement
    assessment_result: str = ""  # Akkoord / Voorleggen / Niet akkoord / Definitief akkoord
    assessment_notes: str = ""

    created_at: datetime = Field(default_factory=datetime.utcnow)


class Enterprise(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    case_id: int = Field(index=True)

    name: str
    statutory_name: str = ""  # statutaire naam

    legal_form: str  # EenmZk/VOF/BV/etc
    kvk_nr: str = ""
    start_date: Optional[date] = None  # startdatum KvK

    address: str = ""
    postcode_city: str = ""
    incorporation_date: Optional[date] = None  # oprichtingsdatum
    registration_date: Optional[date] = None  # registratiedatum

    websites: str = ""
    activities: str = ""  # bedrijfsactiviteiten
    sbi_codes: str = ""  # comma/newline separated

    # KVK adres check
    kvk_address_check_private: str = ""  # zakelijk+privé adres volgens check
    kvk_address_check_notes: str = ""

    # Structuur
    organogram: str = ""  # vrije tekst

    # Corona / buitenland
    corona_affected: bool = False
    corona_notes: str = ""
    foreign_ok: bool = True
    foreign_notes: str = ""

    # Google check (KYC)
    google_check_done: bool = False
    google_check_date: Optional[date] = None
    google_check_website: str = ""
    google_check_company_pages: str = ""  # links
    google_check_social: str = ""  # links
    google_check_revenue_source: str = ""  # waar komt omzet vandaan
    google_check_conclusion: str = ""

    # Boekhouder/accountant
    accountant_name: str = ""
    accountant_email: str = ""

    kvk_sync_source_url: str = ""
    kvk_sync_last_at: Optional[datetime] = None

    enterprise_notes: str = ""


class YearData(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    enterprise_id: int = Field(index=True)
    year: int = Field(index=True)

    # Periode (handig voor deeljaren en controlejaar)
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    period_months_override: float = 0.0  # als je exact wilt sturen (bv. 7,40)

    is_control_year: bool = False
    ytd_months: int = 0  # voor controlejaar (01-01 t/m 31-05 => 5)

    # Box 1 basis
    saldo_fiscale_winst: float = 0.0  # volgens IB-aangifte
    net_result_no_ib: float = 0.0  # als geen IB beschikbaar

    # Realisatie controlejaar (deeljaar)
    realized_income_ytd: float = 0.0  # gerealiseerd (na corr/contr) in deeljaar
    extrapolated_income: float = 0.0  # naar volledig jaar
    prognose_income: float = 0.0

    # Overige Box 1
    box1_wage_before_start: float = 0.0
    box1_wage_during: float = 0.0
    box1_benefits: float = 0.0
    box1_row: float = 0.0
    other_box1_income: float = 0.0

    # Correcties (jaarlijks)
    non_deductible_costs: float = 0.0
    special_tax_expenses: float = 0.0
    random_depreciation: float = 0.0
    investment_deduction: float = 0.0
    other_positive_fiscal: float = 0.0

    incidental_income: float = 0.0
    private_use_car: float = 0.0
    other_negative_fiscal: float = 0.0

    # Huurlasten (voorbeeld: 0 x 85%)
    expired_rent_base: float = 0.0
    expired_rent_factor_pct: float = 85.0

    # Correcties op het gemiddelde (na het middelen)
    other_positive_avg: float = 0.0
    other_negative_avg: float = 0.0

    # DGA (voor BV)
    dga_salary: float = 0.0
    dividend: float = 0.0
    profit_after_corp_tax: float = 0.0

    # W&V kern (voor ratio- en trendpagina)
    turnover_total: float = 0.0
    cogs_total: float = 0.0
    operating_costs_total: float = 0.0
    depreciation_total: float = 0.0
    financial_income_total: float = 0.0
    financial_expense_total: float = 0.0
    extraordinary_income_total: float = 0.0
    extraordinary_expense_total: float = 0.0

    # Balans kern (voor ratio's)
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

    # Specifieke correcties (R/C DGA etc.)
    rc_dga: float = 0.0

    # Vrije opslag (volledige ViiZ-postenset)
    pl_json: str = ""
    bs_json: str = ""
    ib_json: str = ""


class Ownership(SQLModel, table=True):
    """Eigendom/Belang-relaties binnen een dossier.

    OWNER -> OWNED.
    OWNER kan de aanvrager (PERSON) zijn of een Enterprise.
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    case_id: int = Field(index=True)

    owner_kind: str = "PERSON"  # PERSON / ENTERPRISE
    owner_enterprise_id: Optional[int] = Field(default=None, index=True)
    owner_label: str = ""  # gebruikt bij PERSON

    owned_enterprise_id: int = Field(index=True)

    share_pct: float = 0.0
    voting_pct: float = 0.0  # 0 = gelijk aan share_pct
    dividend_entitled: bool = True
    notes: str = ""


class LegalFormChange(SQLModel, table=True):
    """Rechtsvormwijzigingen per onderneming."""

    id: Optional[int] = Field(default=None, primary_key=True)
    enterprise_id: int = Field(index=True)
    effective_date: Optional[date] = None
    from_legal_form: str = ""
    to_legal_form: str = ""
    kvk_nr_old: str = ""
    kvk_nr_new: str = ""
    notes: str = ""


class KYCCheck(SQLModel, table=True):
    """KYC/Wwft broncontroles (insolventie/BIG/LRK/etc.)."""

    id: Optional[int] = Field(default=None, primary_key=True)
    case_id: int = Field(index=True)
    check_type: str
    checked_on: Optional[date] = None
    input_data: str = ""
    result: str = ""  # Ja/Nee/Onbekend
    source_url: str = ""
    notes: str = ""


class DocumentUsed(SQLModel, table=True):
    """Documentenlijst zoals in uitgebreide IKV's."""

    id: Optional[int] = Field(default=None, primary_key=True)
    case_id: int = Field(index=True)
    enterprise_id: Optional[int] = Field(default=None, index=True)
    category: str = "Privé/Algemeen"  # of ondernemingsnaam
    doc_type: str = ""  # bv. 'Aangifte IB 2023 (definitief)'
    filename: str = ""
    notes: str = ""


class ControlChecklistItem(SQLModel, table=True):
    """Maatschappij specifieke controles (checklist)."""

    id: Optional[int] = Field(default=None, primary_key=True)
    case_id: int = Field(index=True)
    control_point: str
    result: str = "N.v.t."  # Ja/Nee/N.v.t.
    checked_at: Optional[datetime] = None
    handler_name: str = ""
    notes: str = ""


class ControlDecision(SQLModel, table=True):
    """Overzicht controles inkomensvaststelling (stappen + fiattering)."""

    id: Optional[int] = Field(default=None, primary_key=True)
    case_id: int = Field(index=True)
    step_nr: int = 0
    status: str = ""  # Akkoord / Definitief akkoord / etc.
    decided_at: Optional[datetime] = None
    handler_name: str = ""
    notes: str = ""


class UploadedDoc(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    case_id: int = Field(index=True)
    enterprise_id: Optional[int] = Field(default=None, index=True)
    filename: str
    stored_path: str
    category: str = ""
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
