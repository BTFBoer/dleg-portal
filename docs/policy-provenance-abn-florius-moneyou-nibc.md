# Policy provenance: ABN AMRO, Florius, MoneYou and NIBC

## Source boundary

The supplied archive contained 100 files. After excluding eight system-metadata files and grouping 19 sets of exact duplicates, 72 unique content objects remained. PDF, DOCX, XLSX, EML, HTML, TXT and URL content was reviewed. In addition, 103 unique images embedded in the unique Word files were OCR-checked; they contained no additional references to the four lenders. Customer dossiers and research notes informed workflow requirements only; no personal data or source documents are stored in this repository.

A file ending in `.pdf.crdownload` was technically a readable two-page PDF. It contains 2022 service terms, not lender policy. Its separation between an indicative software result and the lender's final decision is preserved as a design safeguard.

## Implemented profiles

| Profile | Supplied source | Status | Modelled controls |
| --- | --- | --- | --- |
| ABN AMRO | `Overzichtsformulier alle geldverstrekkers 05-08-2024.xlsx`, IB D/E and Niet-IB C/D | Historical; manual review required | 1-1-1, last-year cap, 75%/90% starter metadata, CR 1.0, manual QR 0.8, solvency 20% |
| Florius | Same matrix, IB V/W and Niet-IB K/L | Historical; manual review required | Explicit inheritance from the historical ABN route |
| MoneYou | Same matrix, IB AR/AS and Niet-IB Y/Z | Historical; manual review required | Explicit inheritance from the historical ABN route |
| NIBC | Same matrix, IB AX/AY and Niet-IB AE/AF; `Voorbeeld NIBC.pdf` dated 2023 | Historical; manual review required | NHG-derived 1-1-1 and latest plus one prior profitable year |

The matrix states that confirmation from ABN AMRO was still pending for ABN AMRO, Florius and MoneYou. These profiles are therefore calculation references, not representations of current acceptance policy. Every result carries a policy-verification note and the multi-lender comparison returns **Voorleggen**.

## Deliberate limits

- Quick ratio is not silently inferred: inventory must be recorded separately, so the historical 0.8 threshold is emitted as a manual control.
- NIBC same-business/same-sector experience and the goodwill exception are policy metadata and reviewer control points; they require dossier facts not present in the basic year record.
- No customer documents, identities, financial statements or KYC findings from the archive are committed.
- A qualified reviewer must verify the applicable lender policy and perform four-eyes approval before issuing an income declaration.
