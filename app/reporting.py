from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen import canvas

from .rules import CalcResult


def euro(v: float) -> str:
    """Dutch formatting: 1.234,56"""
    try:
        x = float(v)
    except Exception:
        x = 0.0
    s = f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"€ {s}"


def fmt_num(v: Optional[float], *, decimals: int = 2, suffix: str = "") -> str:
    if v is None:
        return "n.v.t."
    try:
        x = float(v)
    except Exception:
        return "n.v.t."
    s = f"{x:.{decimals}f}".replace(".", ",")
    return f"{s}{suffix}"


def _wrap_lines(
    text: str,
    *,
    font_name: str,
    font_size: int,
    max_width_pt: float,
) -> List[str]:
    """Very small word-wrap helper for ReportLab canvas."""
    words = (text or "").split()
    if not words:
        return [""]
    lines: List[str] = []
    cur: List[str] = []
    for w in words:
        trial = (" ".join(cur + [w])).strip()
        if pdfmetrics.stringWidth(trial, font_name, font_size) <= max_width_pt:
            cur.append(w)
        else:
            if cur:
                lines.append(" ".join(cur))
                cur = [w]
            else:
                # single very long token
                lines.append(trial)
                cur = []
    if cur:
        lines.append(" ".join(cur))
    return lines


class PDF:
    def __init__(self, out_path: Path):
        self.out_path = out_path
        self.out_path.parent.mkdir(parents=True, exist_ok=True)
        self.c = canvas.Canvas(str(out_path), pagesize=A4)
        self.w, self.h = A4
        self.margin_x = 18 * mm
        self.top = self.h - 18 * mm
        self.y = self.top

    def new_page(self):
        self.c.showPage()
        self.y = self.top

    def title_block(self, *, title: str, subtitle: str = "", confidential: bool = True):
        self.c.setFont("Helvetica-Bold", 16)
        self.c.drawString(self.margin_x, self.y, title)
        self.y -= 7 * mm
        if subtitle:
            self.c.setFont("Helvetica", 10)
            self.c.drawString(self.margin_x, self.y, subtitle)
            self.y -= 6 * mm
        if confidential:
            self.c.setFont("Helvetica-Bold", 9)
            self.c.drawString(self.margin_x, self.y, "VERTROUWELIJK")
            self.y -= 4 * mm
            self.c.setFont("Helvetica", 8)
            self.c.drawString(
                self.margin_x,
                self.y,
                "Dit rapport is vertrouwelijk en uitsluitend bestemd voor intern gebruik. Verstrekking aan anderen is uitdrukkelijk niet toegestaan.",
            )
            self.y -= 8 * mm

    def h2(self, text: str):
        if self.y < 25 * mm:
            self.new_page()
        self.c.setFont("Helvetica-Bold", 12)
        self.c.drawString(self.margin_x, self.y, text)
        self.y -= 6 * mm

    def kv(self, label: str, value: str, *, col_x: float = 0.0, label_w: float = 45 * mm):
        if self.y < 20 * mm:
            self.new_page()
        x = self.margin_x + col_x
        self.c.setFont("Helvetica-Bold", 9)
        self.c.drawString(x, self.y, f"{label}")
        self.c.setFont("Helvetica", 9)
        self.c.drawString(x + label_w, self.y, value)
        self.y -= 4.7 * mm

    def bullet_list(self, lines: Iterable[str], *, indent: float = 2 * mm):
        self.c.setFont("Helvetica", 9)
        for ln in lines:
            if not ln:
                continue
            if self.y < 20 * mm:
                self.new_page()
                self.c.setFont("Helvetica", 9)
            wrapped = _wrap_lines(ln, font_name="Helvetica", font_size=9, max_width_pt=self.w - 2 * self.margin_x - 6 * mm)
            first = True
            for wln in wrapped:
                if self.y < 20 * mm:
                    self.new_page()
                    self.c.setFont("Helvetica", 9)
                prefix = "• " if first else "  "
                self.c.drawString(self.margin_x + indent, self.y, prefix + wln)
                self.y -= 4.6 * mm
                first = False

    def table(
        self,
        headers: List[str],
        rows: List[List[str]],
        col_widths: List[float],
        *,
        row_h: float = 5.2 * mm,
    ):
        if self.y < 25 * mm:
            self.new_page()

        x0 = self.margin_x
        y0 = self.y

        # header
        self.c.setFont("Helvetica-Bold", 9)
        x = x0
        for i, htxt in enumerate(headers):
            self.c.drawString(x, y0, htxt)
            x += col_widths[i]
        self.y -= row_h

        self.c.setFont("Helvetica", 9)
        for r in rows:
            if self.y < 20 * mm:
                self.new_page()
                # redraw header on new page
                y0 = self.y
                self.c.setFont("Helvetica-Bold", 9)
                x = x0
                for i, htxt in enumerate(headers):
                    self.c.drawString(x, y0, htxt)
                    x += col_widths[i]
                self.y -= row_h
                self.c.setFont("Helvetica", 9)

            x = x0
            for i, cell in enumerate(r):
                self.c.drawString(x, self.y, cell)
                x += col_widths[i]
            self.y -= row_h

    def image_fullwidth(self, image_path: str, *, max_h: float = 190 * mm):
        if not image_path:
            return
        self.new_page()
        x = self.margin_x
        y = 20 * mm
        w = self.w - 2 * self.margin_x
        h = min(max_h, self.h - 50 * mm)
        try:
            self.c.setFont("Helvetica-Bold", 12)
            self.c.drawString(self.margin_x, self.top, "Organogram")
            self.c.drawImage(image_path, x, y, width=w, height=h, preserveAspectRatio=True, anchor="sw")
        except Exception:
            pass

    def save(self):
        self.c.save()


def build_income_report_pdf(
    out_path: Path,
    *,
    case: Dict,
    enterprise: Dict,
    policy: Dict,
    calc: CalcResult,
    max_withdrawable: float = 0.0,
    extra_notes: Optional[List[str]] = None,
    organogram_png_path: str = "",
    sections: Optional[Dict[str, List[str]]] = None,
) -> None:
    """Generate a ViiZ-like PDF.

    This is still a lightweight ReportLab renderer, but the structure is aligned to the
    sample IKV sections: summary, enterprise data, income determination, ratios, controls.
    """

    pdf = PDF(out_path)

    dossier_nr = str(case.get("dossier_nr", ""))
    lender_name = str(case.get("lender_name", ""))
    handler = str(case.get("handler_name", ""))
    approver = str(case.get("approver_name", ""))
    calc_date = case.get("calculation_date")
    validity = case.get("validity_until")
    applicant_name = str(case.get("applicant_name", ""))
    applicant_dob = case.get("applicant_dob")
    applicant_addr = str(case.get("applicant_address", ""))
    applicant_pc_city = str(case.get("applicant_postcode_city", ""))

    policy_label = str(policy.get("label", ""))
    policy_key = str(policy.get("key", ""))

    # --- Page 1: Summary ---
    pdf.title_block(title="Inkomensverklaring", subtitle="Uitgebreide rapportage")
    pdf.h2("Samenvatting")

    pdf.kv("Dossiernummer", dossier_nr)
    pdf.kv("Bestemd voor", lender_name)
    pdf.kv("Behandelaar", handler or "-")
    pdf.kv("Fiatteur", approver or "-")
    pdf.kv("Datum", (calc_date.isoformat() if isinstance(calc_date, date) else str(calc_date or "-")))
    pdf.kv("Toetsinkomen", euro(calc.final_income))

    pdf.y -= 2 * mm
    pdf.h2("Aanvrager")
    pdf.kv("Naam", applicant_name or "-")
    pdf.kv("Geboortedatum", (applicant_dob.isoformat() if isinstance(applicant_dob, date) else str(applicant_dob or "-")))
    pdf.kv("Adres", applicant_addr or "-")
    pdf.kv("Postcode/plaats", applicant_pc_city or "-")

    pdf.y -= 2 * mm
    pdf.h2("Geldigheid")
    pdf.kv("Datum vaststelling", (calc_date.isoformat() if isinstance(calc_date, date) else str(calc_date or "-")))
    pdf.kv("Geldig t/m", (validity.isoformat() if isinstance(validity, date) else str(validity or "-")))

    pdf.y -= 2 * mm
    pdf.c.setFont("Helvetica", 8)
    pdf.c.drawString(pdf.margin_x, pdf.y, f"Toetskader/policy: {policy_label} ({policy_key})")
    pdf.y -= 6 * mm

    # --- Page 2: Enterprise data + income determination ---
    pdf.new_page()
    pdf.title_block(title="Onderneming(en)", subtitle="Bedrijfsgegevens")

    pdf.kv("Onderneming", str(enterprise.get("name", "-")))
    pdf.kv("Rechtsvorm", str(enterprise.get("legal_form", "-")))
    pdf.kv("KvK nummer", str(enterprise.get("kvk_nr", "-")))
    pdf.kv("Startdatum KvK", str(enterprise.get("start_date", "-") or "-"))
    pdf.kv("Adres", str(enterprise.get("address", "-")))
    pdf.kv("Postcode/plaats", str(enterprise.get("postcode_city", "-")))
    pdf.kv("SBI", str(enterprise.get("sbi_codes", "-")))

    pdf.y -= 2 * mm
    pdf.h2("Inkomensvaststelling")

    # income table
    years_sorted = sorted(calc.income_years.keys())
    rows = []
    for y in years_sorted:
        rows.append([str(y), euro(calc.income_years[y])])
    pdf.table(headers=["Jaar", "Inkomen (Box 1/DGA)"], rows=rows, col_widths=[25 * mm, 70 * mm])

    pdf.y -= 2 * mm
    pdf.kv("Gemiddelde (jaar)", euro(calc.base_income_avg))
    pdf.kv("Max laatste boekjaar", euro(calc.capped_to_last_year))
    pdf.kv("Na lopend-jaar toets", euro(calc.interim_adjusted_income))
    if calc.control_year:
        pdf.kv("Controlejaar", str(calc.control_year))
        pdf.kv("Controlejaar geëxtrapoleerd", euro(calc.control_year_extrapolated))
        pdf.kv("Prognose", euro(calc.control_year_prognose))

    if max_withdrawable:
        pdf.y -= 2 * mm
        pdf.h2("Maximaal te onttrekken aan de onderneming")
        pdf.c.setFont("Helvetica", 9)
        pdf.c.drawString(pdf.margin_x, pdf.y, f"Indicatief maximaal te onttrekken vlottende activa: {euro(max_withdrawable)}")
        pdf.y -= 6 * mm

    # --- Page 3: Ratio's ---
    pdf.new_page()
    pdf.title_block(title="Ratio's en voorwaarden", subtitle="Kengetallen (informatief)")

    r_rows: List[List[str]] = []
    for y in years_sorted:
        r = calc.ratios.get(y, {})
        f = calc.ratio_flags.get(y, {})
        r_rows.append(
            [
                str(y),
                fmt_num(r.get("current_ratio"), decimals=2),
                f.get("Current Ratio", "-"),
                fmt_num(r.get("quick_ratio"), decimals=2),
                f.get("Quick Ratio", "-"),
                fmt_num(r.get("working_capital"), decimals=0),
                f.get("Werkkapitaal", "-"),
                fmt_num(r.get("solvability_pct"), decimals=2, suffix="%"),
                f.get("Solvabiliteit", "-"),
            ]
        )

    pdf.table(
        headers=["Jaar", "CR", "", "QR", "", "WK", "", "SV", ""],
        rows=r_rows,
        col_widths=[14 * mm, 12 * mm, 18 * mm, 12 * mm, 18 * mm, 16 * mm, 18 * mm, 16 * mm, 18 * mm],
        row_h=5.0 * mm,
    )

    pdf.y -= 2 * mm
    pdf.h2("Notities")
    pdf.bullet_list(list(calc.notes) + (extra_notes or []))

    # --- Page 4: Controls / documents (sections) ---
    if sections:
        pdf.new_page()
        pdf.title_block(title="Dossierbijlagen", subtitle="Documenten en controles")
        for title, lines in sections.items():
            if not lines:
                continue
            pdf.h2(title)
            pdf.bullet_list(lines)
            pdf.y -= 2 * mm

    # --- Organogram ---
    if organogram_png_path:
        pdf.image_fullwidth(organogram_png_path)

    pdf.save()
