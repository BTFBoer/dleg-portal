# IKV Portal (MVP) – Website/software voor zakelijk inkomen (ondernemers)

Dit is een **werkend MVP** (minimum viable product) van een webapplicatie waarmee geldverstrekkers/servicers/rekendeskundigen:

- dossiers kunnen aanmaken;
- ondernemingen + jaarcijfers/balansen kunnen vastleggen;
- **toetsinkomen** kunnen berekenen op basis van een **configureerbare policy** (per geldverstrekker);
- kengetallen (liquiditeit/solvabiliteit) en trends kunnen beoordelen;
- een **PDF‑rapport** kunnen genereren (samenvatting + rekenstappen, vergelijkbaar in stijl met inkomensanalyses).

Belangrijk:
- Beleidsregels verschillen per maatschappij en wijzigen regelmatig. Deze software is daarom gebouwd met een **policy‑engine**: regels staan in JSON en zijn per geldverstrekker te onderhouden.
- Er is een **policy sync script** dat de acceptatiegids‑links van HypotheekCompany kan ophalen en PDFs kan downloaden (zodat je ze intern kunt archiveren). De daadwerkelijke “mapping” van een PDF‑acceptatiegids naar JSON‑regels blijft (in MVP) een beheerderstaak.

## Quickstart (lokaal)

### 1) Installeren

```bash
cd ikv_portal
python -m venv .venv
# Windows PowerShell:
#   .venv\Scripts\Activate.ps1
# Windows CMD:
#   .venv\Scripts\activate.bat
# macOS/Linux:
#   source .venv/bin/activate
pip install -r requirements.txt
```

### 2) Starten

```bash
python -m uvicorn app.main:app --reload --port 8080
```

Open: http://localhost:8080

### Database reset (bij schema-updates)

Als je na een update meldingen ziet als `sqlite3.OperationalError: no such column ...`, verwijder dan de lokale database:

```
ikv_portal/app/data/ikv_portal.db
```

Start daarna opnieuw; de tabellen worden opnieuw aangemaakt.

### 3) (Optioneel) Acceptatiegidsen ophalen

```bash
python scripts/sync_hypotheekcompany.py --out app/data/policy_sources
```

Daarna kun je in de UI per geldverstrekker een policy (JSON) aanmaken en de gedownloade PDFs als “bron” koppelen.

## Kernconcept

- **Case/Dossier**: de hypotheekaanvraag (met gekozen geldverstrekker + NHG ja/nee).
- **Enterprise/Onderneming**: juridische vorm, KvK, SBI, startdatum.
- **YearData**: winst/box‑1, salaris (DGA), dividend, en (optioneel) lopend‑jaar extrapolatie.
- **BalanceData**: vlottende activa, kort vreemd vermogen, eigen vermogen, balanstotaal, immateriële VA, rekening‑courant DGA.
- **Policy (JSON)**: regels voor berekening + ratio‑grenzen + cap‑logica + interim‑regels.


## Geldverstrekkerprofielen uit bronarchief

De policy-engine bevat nu ook versiegebonden profielen voor **ABN AMRO, Florius, MoneYou en NIBC**. Deze zijn afgeleid uit de aangeleverde vergelijkingsmatrix van 5 augustus 2024 en, voor NIBC, het rekenvoorbeeld uit 2023.

Omdat de matrix bij ABN AMRO, Florius en MoneYou nog op bevestiging van ABN wachtte en geen actuele afzonderlijke kredietgidsen bevat, zijn alle vier profielen technisch gemarkeerd als **historisch** en **altijd voorleggen**. De berekening is reproduceerbaar, maar de applicatie presenteert de uitkomst niet als automatisch fiatteerbaar.

Zie [de beleidsherkomst en implementatiegrenzen](docs/policy-provenance-abn-florius-moneyou-nibc.md).

## Risicosectoren (SBI) – optioneel

MVP kan optioneel een **SBI risicosector‑check** doen (voorbeeld: Knab spreadsheet). 

Plaats het Excelbestand als:

```
ikv_portal/app/data/Knab_Hypotheek_Risicosectoren_Zakelijk_inkomen.xlsx
```

Daarna verschijnt in het berekenscherm een waarschuwing bij matches.

## Security/AVG

MVP bevat nog geen volledige auth/rollen. Voor productie:
- SSO/OIDC;
- versleutelde opslag;
- audit logging;
- dataminimalisatie + bewaartermijnen;
- DPIA/Wwft procesinrichting.

## Licentie

Gebruik vrij voor prototyping. Voor productie is een juridische review nodig.
