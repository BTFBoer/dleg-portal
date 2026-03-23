from __future__ import annotations

import json
from typing import Dict, List

# UI catalogs for one enterprise in one year.
# Keys are kept stable so they can safely be stored in JSON.

BALANCE_GROUPS: List[dict] = [
    {
        "title": "ACTIVA · Immateriële Vaste Activa",
        "fields": [
            ("goodwill_totaal", "Goodwill Totaal"),
            ("goodwill_niet_tot_ev", "Goodwill (niet tot EV behorend)"),
            ("goodwill_tot_ev", "Goodwill (tot EV behorend)"),
            ("onderzoek_en_ontwikkeling", "Onderzoek en ontwikkeling"),
            ("investeringen_ontwikkelingskosten", "Investeringen en ontwikkelingskosten"),
            ("licenties_octrooien_patenten", "Licenties, octrooien en patenten"),
            ("overig_onderzoek_ontwikkeling", "Overig Onderzoek en ontwikkeling"),
            ("overige_immateriele_vaste_activa", "Overige Immateriële Vaste Activa"),
            ("totaal_immateriele_vaste_activa", "Totaal Immateriële Vaste Activa"),
        ],
        "total_key": "totaal_immateriele_vaste_activa",
    },
    {
        "title": "ACTIVA · Materiële Vaste Activa",
        "fields": [
            ("onroerend_goed", "Onroerend goed"),
            ("terreinen", "Terreinen"),
            ("gebouwen", "Gebouwen"),
            ("overig_onroerend_goed", "Overig onroerend goed"),
            ("overige_materiele_vaste_activa", "Overige Materiële Vaste Activa"),
            ("machines_installaties", "Machines en installaties"),
            ("inventaris_gereedschappen_productie", "Inventaris en gereedschappen productie"),
            ("inventaris_kantoor", "Inventaris kantoor"),
            ("automatisering", "Automatisering"),
            ("vervoermiddelen", "Vervoermiddelen"),
            ("andere_materiele_vaste_activa", "Andere Materiële Vaste Activa"),
            ("totaal_materiele_vaste_activa", "Totaal Materiële Vaste Activa"),
        ],
        "total_key": "totaal_materiele_vaste_activa",
    },
    {
        "title": "ACTIVA · Financiële Vaste Activa",
        "fields": [
            ("deelnemingen", "Deelnemingen"),
            ("deelnemingen_groepsmaatschappijen", "Deelnemingen groepsmaatschappijen"),
            ("overige_deelnemingen", "Overige deelnemingen"),
            ("vorderingen_langlopend", "Vorderingen (langlopend)"),
            ("vorderingen_niet_op_dir_ahr_groep_participanten_lang", "Vorderingen (niet op dir, ahr's, groep of participanten)(langlopend)"),
            ("totaal_vorderingen_dir_ahr_groep_participanten_lang", "Totaal vorderingen op dir, ahr's, groep of participanten (langlopend)"),
            ("vorderingen_ahr_groepsmij_participanten_niet_achtergesteld_lang", "Vorderingen op ahr's, groepsmij, participanten (niet achtergesteld, langlopend)"),
            ("andere_vorderingen_dir_ahr_groep_participanten_lang", "Andere vorderingen op dir, ahr's, groep of participanten (langlopend)"),
            ("overige_vorderingen_lang", "Overige vorderingen (langlopend)"),
            ("latente_belastingvorderingen_lang", "Latente belastingvorderingen (langlopend)"),
            ("andere_vorderingen_lang", "Andere vorderingen (langlopend)"),
            ("overige_financiele_vaste_activa", "Overige Financiële Vaste Activa"),
            ("effecten", "Effecten"),
            ("waarborgsommen", "Waarborgsommen"),
            ("andere_financiele_vaste_activa", "Andere Financiële Vaste Activa"),
            ("totaal_financiele_vaste_activa", "Totaal Financiële Vaste Activa"),
            ("totaal_vaste_activa", "Totaal Vaste Activa"),
        ],
        "total_key": "totaal_financiele_vaste_activa",
    },
    {
        "title": "ACTIVA · Vlottende Activa",
        "fields": [
            ("voorraden_totaal", "Voorraden Totaal"),
            ("voorraden", "Voorraden"),
            ("grond_hulpstoffen", "Grond- en hulpstoffen"),
            ("inkopen_onderdelen", "Inkopen en onderdelen"),
            ("gereed_product", "Gereed product"),
            ("onderhanden_werk", "Onderhanden werk"),
            ("vooruitbetaling_voorraden", "Vooruitbetaling op voorraden"),
            ("totaal_overige_voorraden", "Totaal Overige Voorraden"),
            ("incourante_voorraden", "Incourante voorraden"),
            ("andere_voorraden", "Andere voorraden"),
            ("debiteuren_vorderingen", "Debiteuren / Vorderingen"),
            ("totaal_debiteuren", "Totaal Debiteuren"),
            ("debiteuren_standaard", "Debiteuren (standaard)"),
            ("dubieuze_debiteuren", "Dubieuze debiteuren"),
            ("overige_debiteuren", "Overige debiteuren"),
            ("totaal_vorderingen", "Totaal Vorderingen"),
            ("vorderingen_ahr_groepsmij_participanten_kort_niet_achtergesteld", "Vorderingen op ahr's, groepsmij, participanten (kort, niet achtergesteld)"),
            ("overige_vorderingen_ahr_groepsmaatschappijen_participanten_kort", "Overige vorderingen op ahr's (excl. DGA), groepsmaatschappijen en participanten (kortlopend)"),
            ("latente_belastingvorderingen_kort", "Latente belastingvorderingen (kortlopend)"),
            ("overige_vorderingen", "Overige Vorderingen"),
            ("overige_vlottende_activa", "Overige Vlottende Activa"),
            ("te_vorderen_omzetbelasting", "Te vorderen omzet belasting"),
            ("vooruitbetaalde_bedragen", "Vooruitbetaalde bedragen"),
            ("nog_te_ontvangen_bedragen", "Nog te ontvangen bedragen"),
            ("nog_te_factureren_gereed_product", "Nog te factureren gereed product"),
            ("te_ontvangen_rente", "Te ontvangen rente"),
            ("overlopende_activa", "Overlopende activa"),
            ("andere_vlottende_activa", "Andere vlottende activa"),
            ("liquide_middelen", "Liquide middelen"),
            ("kas", "Kas"),
            ("bankrekeningen", "Bankrekeningen"),
            ("spaarrekeningen", "Spaarrekeningen"),
            ("depositorekeningen", "Depositorekeningen"),
            ("beleggingsrekeningen", "Beleggingsrekeningen"),
            ("kruisposten", "Kruisposten"),
            ("overige_liquide_middelen", "Overige liquide middelen"),
            ("totaal_vlottende_activa", "Totaal Vlottende Activa"),
            ("totaal_activa", "TOTAAL ACTIVA"),
        ],
    },
    {
        "title": "PASSIVA · Eigen Vermogen",
        "fields": [
            ("kapitaal_eenmanszaak", "Kapitaal (ZZP/Eenmanszaak)"),
            ("kapitaal_begin_saldo", "Kapitaal Begin saldo"),
            ("winstsaldo_lopend_boekjaar", "Winstsaldo lopend boekjaar"),
            ("prive_stortingen", "Privé stortingen"),
            ("prive_onttrekkingen_privegebruik_auto", "Privé onttrekkingen privé gebruik auto"),
            ("overige_prive_onttrekkingen", "Overige Privé onttrekkingen"),
            ("wettelijke_statutaire_reserves", "Wettelijke en statutaire reserves"),
            ("overige_reserves", "Overige reserves"),
            ("algemene_reserve", "Algemene reserve"),
            ("dividenduitkering_boekjaar", "Dividenduitkering boekjaar"),
            ("resultaatbestemming_boekjaar", "Resultaatbestemming boekjaar"),
            ("andere_reserves", "Andere reserves"),
            ("onverdeelde_winst", "Onverdeelde winst"),
            ("totaal_eigen_vermogen", "Totaal Eigen Vermogen"),
        ],
        "total_key": "totaal_eigen_vermogen",
    },
    {
        "title": "PASSIVA · Voorzieningen",
        "fields": [
            ("for_aanvrager", "Fiscale Oudedag Reserve (aanvrager)"),
            ("voorzieningen_latente_belastingen", "Voorzieningen Latente Belastingen"),
            ("voorzieningen_dubieuze_debiteuren", "Voorzieningen Dubieuze Debiteuren"),
            ("overige_voorzieningen", "Overige voorzieningen"),
            ("onderhoudsvoorziening", "Onderhoudsvoorziening"),
            ("garantievoorziening", "Garantievoorziening"),
            ("assurantievoorziening", "Assurantievoorziening"),
            ("voorziening_incourante_goederen", "Voorziening incourante goederen"),
            ("voorziening_reorganisatie_kosten", "Voorziening reorganisatie kosten"),
            ("pensioenvoorziening_personeel", "Pensioenvoorziening (personeel)"),
            ("stamrechtvoorziening", "Stamrechtvoorziening"),
            ("andere_voorzieningen", "Andere voorzieningen"),
            ("totaal_voorzieningen", "Totaal Voorzieningen"),
        ],
        "total_key": "totaal_voorzieningen",
    },
    {
        "title": "PASSIVA · Langlopende schulden (> 1 jaar)",
        "fields": [
            ("achtergestelde_leningen_langlopend", "Achtergestelde leningen (langlopend)"),
            ("achtergestelde_leningen_lang", "Achtergestelde leningen (lang)"),
            ("achtergestelde_leningen_lang_kredietinstellingen", "Achtergestelde leningen (lang) kredietinstellingen"),
            ("achtergestelde_leningen_lang_dga_eigenaar", "Achtergestelde leningen (lang) DGA / Eigenaar"),
            ("achtergestelde_leningen_lang_ahr_groepmij", "Achtergestelde leningen (lang) ahr's, groepmij"),
            ("overige_achtergestelde_leningen_lang", "Overige achtergestelde leningen (lang)"),
            ("schulden_kredietinstellingen_lang_niet_achtergesteld", "Schulden aan kredietinstellingen (niet achtergest, lang)"),
            ("hypothecaire_leningen", "Hypothecaire leningen"),
            ("converteerbare_leningen", "Converteerbare leningen"),
            ("obligatieleningen_onderhandse_leningen", "Obligatieleningen en onderhandse leningen"),
            ("leaseverplichtingen", "Leaseverplichtingen"),
            ("schulden_directie_ahr_groepmij_lang_niet_achtergesteld", "Schulden aan directie, ahr's, groepmij (niet achtergest, lang)"),
            ("schulden_ahr_groepsmij_participanten_lang_niet_achtergesteld", "Schulden aan ahr's, groepsmij, participanten (niet achtergesteld, langlopend)"),
            ("overige_langlopende_leningen", "Overige langlopende leningen"),
            ("schulden_leveranciers_handelskredieten_lang", "Schulden aan leveranciers/handelskredieten"),
            ("andere_langlopende_leningen", "Andere langlopende leningen"),
            ("totaal_langlopende_schulden", "Totaal langlopende schulden"),
        ],
        "total_key": "totaal_langlopende_schulden",
    },
    {
        "title": "PASSIVA · Kortlopende schulden (= 1 jaar)",
        "fields": [
            ("achtergestelde_leningen_kort", "Achtergestelde leningen (kort)"),
            ("achtergestelde_leningen_kort_kredietinstellingen", "Achtergestelde leningen (kort) kredietinstellingen"),
            ("achtergestelde_leningen_kort_dga_eigenaar", "Achtergestelde leningen (kort) DGA / Eigenaar"),
            ("overige_achtergestelde_leningen_kort", "Overige achtergestelde leningen (kort)"),
            ("crediteuren", "Crediteuren"),
            ("schulden_kredietinstellingen_kort_niet_achtergesteld", "Schulden aan kredietinstellingen (niet achtergest, kort)"),
            ("schulden_directie_ahr_groepmij_kort_niet_achtergesteld", "Schulden aan directie, ahr's, groepmij (niet achtergest, kort)"),
            ("schulden_ahr_groepsmij_participanten_kort_niet_achtergesteld", "Schulden aan ahr's, groepsmij, participanten (kort, niet achtergesteld)"),
            ("belastingen_en_premies", "Belastingen en premies"),
            ("te_betalen_omzetbelasting", "Te betalen Omzet belasting"),
            ("te_betalen_vennootschapsbelasting", "Te betalen vennootschapsbelasting"),
            ("te_betalen_loonbelasting", "Te betalen loonbelasting"),
            ("te_betalen_premies_sociale_verzekeringen", "Te betalen premies sociale verzekeringen"),
            ("andere_belastingen_premies", "Andere Belastingen en premies"),
            ("te_betalen_pensioenen", "Te betalen pensioenen"),
            ("overige_kortlopende_schulden", "Overige kortlopende schulden"),
            ("accountantskosten", "Accountantskosten"),
            ("reservering_vakantiegeld_vakantiedagen", "Reservering vakantiegeld en vakantiedagen"),
            ("aflossingsverplichtingen", "Aflossingsverplichtingen"),
            ("andere_schulden_kort", "Andere schulden (kort)"),
            ("totaal_kortlopende_schulden", "Totaal kortlopende schulden"),
            ("totaal_passiva", "TOTAAL PASSIVA"),
        ],
    },
]

PL_GROUPS: List[dict] = [
    {
        "title": "Omzet",
        "fields": [
            ("omzet_basisomzet", "Omzet (basisomzet)"),
            ("omzet_uitbesteed_werk_derden", "Omzet uitbesteed werk derden"),
            ("kortingen_bonussen", "Kortingen en bonussen"),
            ("andere_omzet", "Andere omzet"),
            ("wijziging_voorraden_gereed_product", "Wijziging in voorraden gereed product"),
            ("wijziging_onderhanden_werk", "Wijziging in onderhanden werk"),
            ("overige_bedrijfsopbrengsten", "Overige bedrijfsopbrengsten"),
            ("doorbelastingen", "Doorbelastingen"),
            ("huuropbrengsten", "Huuropbrengsten"),
            ("andere_bedrijfsopbrengsten", "Andere bedrijfsopbrengsten"),
            ("totale_omzet", "Totale omzet"),
        ],
        "total_key": "totale_omzet",
    },
    {
        "title": "Inkoopwaarde omzet",
        "fields": [
            ("inkopen", "Inkopen"),
            ("verbruik_grondstoffen", "Verbruik grondstoffen"),
            ("verbruik_onderdelen", "Verbruik onderdelen"),
            ("verbruik_hulpstoffen", "Verbruik hulpstoffen"),
            ("voorraadmutatie", "Voorraadmutatie"),
            ("kosten_uitbesteed_werk_externe", "Kosten uitbesteed werk en andere externe kosten"),
            ("prive_gebruik_goederen", "Privé gebruik goederen"),
            ("andere_inkoopwaarde_omzet", "Andere inkoopwaarde omzet"),
            ("totaal_inkoopwaarde_omzet", "Totaal inkoopwaarde omzet"),
            ("totaal_bruto_bedrijfsresultaat", "Totaal Bruto bedrijfsresultaat"),
        ],
        "total_key": "totaal_inkoopwaarde_omzet",
    },
    {
        "title": "Bedrijfskosten · Afschrijvingen en huisvesting",
        "fields": [
            ("afschrijvingen", "Afschrijvingen"),
            ("totaal_afschrijvingen_immateriele_activa", "Totaal Afschrijvingen immateriële activa"),
            ("afschrijving_onderzoek_ontwikkeling", "Afschrijving onderzoek en ontwikkeling"),
            ("afschrijving_goodwill", "Afschrijving goodwill"),
            ("willekeurige_afschrijvingen_immateriele_activa", "Willekeurige afschrijvingen immateriële activa"),
            ("overige_afschrijvingen_immateriele_activa", "Overige afschrijvingen immateriële activa"),
            ("totaal_afschrijvingen_materiele_activa", "Totaal Afschrijvingen materiële activa"),
            ("afschrijvingen_gebouwen_terreinen", "Afschrijvingen gebouwen en terreinen"),
            ("afschrijvingen_machines_installatie", "Afschrijvingen machines en installatie"),
            ("afschrijvingen_inventaris_gereedschappen", "Afschrijvingen inventaris en gereedschappen"),
            ("afschrijvingen_kantoorinventaris", "Afschrijvingen kantoorinventaris"),
            ("afschrijvingen_vervoermiddelen_bestel_vrachtauto", "Afschrijvingen vervoermiddelen bestel-, vrachtauto's"),
            ("afschrijvingen_vervoermiddelen_personenautos", "Afschrijvingen vervoermiddelen personen auto's"),
            ("willekeurige_afschrijvingen_materiele_vaste_activa", "Willekeurige afschrijvingen materiële vaste activa"),
            ("overige_afschrijvingen_materiele_activa", "Overige afschrijvingen materiële activa"),
            ("huisvestingskosten", "Huisvestingskosten"),
            ("huurkosten", "Huurkosten"),
            ("energie_water", "Energie (gas en elektra) en water"),
            ("ozb", "Onroerend Zaak Belasting"),
            ("onderhoud_reparatie_huisvesting", "Onderhouds- en reparatiekosten"),
            ("verzekeringskosten_huisvesting", "Verzekeringskosten huisvesting"),
            ("overige_huisvestingskosten", "Overige huisvestingskosten"),
        ],
    },
    {
        "title": "Bedrijfskosten · Vervoer en personeel",
        "fields": [
            ("autokosten", "Autokosten"),
            ("kosten_vervoermiddelen", "Kosten vervoermiddelen"),
            ("leasekosten", "Leasekosten"),
            ("onderhoud_reparatie_vervoer", "Onderhouds- en reparatiekosten vervoer"),
            ("brandstoffen_vervoer", "Brandstoffen vervoer"),
            ("verzekeringen_vervoer", "Verzekeringen vervoer"),
            ("belastingen_vervoer", "Belastingen vervoer"),
            ("boetes_vervoer", "Boetes vervoer"),
            ("overige_kosten_vervoermiddelen", "Overige kosten vervoermiddelen"),
            ("privegebruik_auto_negatieve_autokosten", "Privégebruik auto (negatieve autokosten)"),
            ("btw_privegebruik_auto", "BTW privégebruik auto"),
            ("kosten_openbaar_vervoer", "Kosten openbaar vervoer"),
            ("kilometervergoeding", "Kilometervergoeding"),
            ("overige_autokosten", "Overige autokosten"),
            ("personeelskosten", "Personeelskosten"),
            ("loonkosten", "Loonkosten"),
            ("management_vergoeding", "Management vergoeding"),
            ("meewerk_vergoeding", "Meewerk vergoeding"),
            ("arbeidsvergoeding", "Arbeidsvergoeding"),
            ("sociale_lasten", "Sociale lasten"),
            ("pensioen_lasten", "Pensioen lasten"),
            ("doorberekende_personeelskosten", "Doorberekende personeelskosten"),
            ("ziekengeld_verzekering", "Ziekengeld verzekering"),
            ("overige_personeelskosten", "Overige personeelskosten"),
        ],
    },
    {
        "title": "Bedrijfskosten · Overige kosten",
        "fields": [
            ("andere_bedrijfskosten", "Andere bedrijfskosten"),
            ("machine_exploitatiekosten", "Machine- en exploitatiekosten"),
            ("onderhoud_reparaties_machines", "Onderhoud en reparaties machines"),
            ("lease_huurkosten_machines", "Lease en huurkosten machines"),
            ("kleine_aanschaffingen", "Kleine aanschaffingen"),
            ("verzekeringen", "Verzekeringen"),
            ("overige_machine_exploitatiekosten", "Overige machine- en exploitatiekosten"),
            ("verkoop_advertentiekosten", "Verkoop en advertentie kosten"),
            ("reclame_advertentiekosten", "Reclame en advertentiekosten"),
            ("kosten_sponsoring", "Kosten sponsoring"),
            ("relatiegeschenken_representatiekosten", "Relatiegeschenken en representatiekosten"),
            ("reis_verblijfskosten", "Reis- en verblijfskosten"),
            ("dotatie_voorziening_dubieuze_debiteuren", "Dotatie voorziening dubieuze debiteuren"),
            ("overige_verkoopkosten", "Overige verkoopkosten"),
            ("kantoorkosten", "Kantoorkosten"),
            ("kantoorbenodigdheden", "Kantoorbenodigdheden"),
            ("telecommunicatie_internet", "Telecommunicatie en internet kosten"),
            ("onderhoud_reparaties_kantoor", "Onderhoud en reparaties"),
            ("porti", "Porti"),
            ("drukwerk", "Drukwerk"),
            ("kosten_automatisering", "Kosten automatisering"),
            ("kantoorverzekering", "Kantoorverzekering"),
            ("overige_kantoorkosten", "Overige kantoorkosten"),
            ("algemene_kosten", "Algemene kosten"),
            ("algemene_verzekeringen", "Algemene verzekeringen"),
            ("contributies_abonnementen", "Contributies en abonnementen"),
            ("accountancy_kosten", "Accountancy kosten"),
            ("advieskosten", "Advieskosten"),
            ("af_te_boeken_verschillen", "Af te boeken verschillen"),
            ("overige_bedrijfskosten_overig", "Overige bedrijfskosten"),
            ("totaal_bedrijfskosten", "Totaal bedrijfskosten"),
            ("netto_bedrijfsresultaat", "(Netto) Bedrijfsresultaat"),
        ],
        "total_key": "totaal_bedrijfskosten",
    },
    {
        "title": "Financiële baten en lasten",
        "fields": [
            ("financiele_baten", "Financële Baten"),
            ("rentebaten_banktegoeden", "Rentebaten banktegoeden"),
            ("rentebaten_vorderingen_directie", "Rentebaten vorderingen op Directie"),
            ("rentebaten_vorderingen_ahr_participanten_groepmij_deelnemingen", "Rentebaten vorderingen ahr's, participanten, groepmij en deelnemingen"),
            ("rentebaten_hypotheken", "Rentebaten hypotheken"),
            ("rentebaten_lease", "Rentebaten lease"),
            ("rentebaten_belastingen", "Rentebaten belastingen"),
            ("opbrengst_financiele_vaste_activa_excl_deelnemingen", "Opbrengst van (financiële) vaste activa (excl. deelnemingen)"),
            ("overige_rentebaten", "Overige rentebaten"),
            ("financiele_lasten", "Financiële Lasten"),
            ("rentelasten_banktegoeden", "Rentelasten banktegoeden"),
            ("rentelasten_vorderingen_directie", "Rentelasten vorderingen op Directie"),
            ("rentelasten_vorderingen_ahr_participanten_groepmij_deelnemingen", "Rentelasten vorderingen ahr's, participanten, groepmij en deelnemingen"),
            ("rentelasten_hypotheken", "Rentelasten hypotheken"),
            ("rentelasten_lease", "Rentelasten lease"),
            ("rentelasten_belastingen", "Rentelasten belastingen"),
            ("waardedaling_financiele_vaste_activa_excl_deelnemingen", "Waardedaling (financiële) vaste activa (excl. deelnemingen)"),
            ("overige_rentelasten", "Overige rentelasten"),
            ("som_financiele_baten_en_lasten", "Som van Financiële Baten en Lasten"),
        ],
    },
    {
        "title": "Buitengewone baten en lasten",
        "fields": [
            ("buitengewone_baten", "Buitengewone baten"),
            ("waarvan_kor", "waarvan KOR"),
            ("buitengewone_baten_niet_fiscaal", "Buitengewone baten (niet fiscaal van aard)"),
            ("buitengewone_baten_fiscaal", "Buitengewone baten (fiscaal van aard)"),
            ("buitengewone_lasten", "Buitengewone lasten"),
            ("buitengewone_lasten_niet_fiscaal", "Buitengewone lasten (niet fiscaal van aard)"),
            ("buitengewone_lasten_fiscaal", "Buitengewone lasten (fiscaal van aard)"),
            ("som_buitengewone_baten_en_lasten", "Som van Buitengewone Baten en Lasten"),
            ("netto_winst_voor_belasting", "Netto winst voor belasting"),
        ],
    },
    {
        "title": "Deelnemingen en prognose",
        "fields": [
            ("totaal_resultaat_deelnemingen", "Totaal Resultaat deelnemingen"),
            ("netto_winst_resultaat", "Netto winst / Resultaat"),
            ("prognose_volledig_jaar", "Prognose volledig jaar"),
        ],
    },
]

IB_GROUPS: List[dict] = [
    {
        "title": "IB · Basis ondernemersinkomen",
        "fields": [
            ("saldo_fiscale_winst", "Saldo Fiscale Winst"),
            ("privegebruik_auto", "Privégebruik auto"),
        ],
    },
    {
        "title": "IB · VOF / Maatschap resultaatverdeling",
        "fields": [
            ("arbeidsvergoeding_ondernemer", "Arbeidsvergoeding ondernemer"),
            ("privegebruik_auto_ondernemer", "Privégebruik auto ondernemer"),
            ("rentevergoeding_ondernemer", "Rentevergoeding ondernemer"),
            ("overige_vergoedingen_ondernemer", "Overige vergoedingen ondernemer"),
            ("totaal_vergoedingen_ondernemer", "Totaal vergoedingen ondernemer"),
            ("arbeidsvergoeding_overige_vennoten_maten", "Arbeidsvergoeding Overige Vennoten / Maten"),
            ("privegebruik_auto_overige_vennoten_maten", "Privégebruik auto Overige Vennoten / Maten"),
            ("rentevergoeding_overige_vennoten_maten", "Rentevergoeding Overige Vennoten / Maten"),
            ("overige_vergoedingen_overige_vennoten_maten", "Overige vergoedingen Overige Vennoten / Maten"),
            ("totaal_vergoedingen_overige_vennoten_maten", "Totaal vergoedingen Overige Vennoten / Maten vóór resultaatverdeling"),
            ("totaal_vergoedingen_alle_vennoten_maten", "Totaal vergoedingen aan alle Vennoten / Maten vóór resultaatverdeling"),
            ("resultaat_vof_maatschap_voor_correcties", "Resultaat Vof / Maatschap vóór correcties (uit V&W-rek)"),
            ("te_verdelen_resultaat_voor_correcties", "Te verdelen resultaat vóór correcties"),
            ("percentage_recht_op_resultaat_ondernemer", "Percentage recht op resultaat ondernemer"),
            ("deel_resultaat_ondernemer", "Deel resultaat ondernemer"),
            ("percentage_recht_op_resultaat_overige_vennoten_maten", "Percentage recht op resultaat Overige Vennoten / Maten"),
            ("deel_resultaat_overige_vennoten_maten", "Deel resultaat Overige Vennoten / Maten"),
            ("totaal_inkomsten_ondernemer_voor_correcties", "Totaal inkomsten ondernemer vóór correcties"),
            ("totaal_inkomsten_overige_vennoten_maten_voor_correcties", "Totaal inkomsten Overige Vennoten / Maten vóór correcties"),
        ],
    },
    {
        "title": "IB · Overige Box 1 inkomsten",
        "fields": [
            ("looninkomsten_voor_starten_onderneming", "Looninkomsten vóór starten onderneming"),
            ("looninkomen_naast_tijdens_ondernemerschap", "Looninkomen naast/tijdens ondernemerschap"),
            ("inkomensvervangende_uitkeringen", "Inkomensvervangende uitkeringen"),
            ("inkomsten_uit_overige_werkzaamheden", "Inkomsten uit overige werkzaamheden"),
            ("overige_box1_inkomsten", "Overige Box 1 inkomsten"),
            ("totaal_overige_box1_inkomsten", "Totaal Overige Box 1 inkomsten"),
        ],
    },
    {
        "title": "IB · Kapitaalsvergelijking en Box 2",
        "fields": [
            ("som_prive_stortingen_onttrekkingen", "Som van de privé stortingen en onttrekkingen"),
            ("prive_stortingen_ib", "Privé stortingen"),
            ("prive_onttrekkingen_ib", "Privé onttrekkingen"),
            ("totaal_genoten_dividend", "Totaal Genoten Dividend"),
            ("overig_box2_inkomen", "Overig Box 2 inkomen"),
            ("ontvangen_intercompany_dividend", "Ontvangen intercompany dividend"),
        ],
    },
    {
        "title": "IB · Box 3 inkomen en vermogen",
        "fields": [
            ("inkomen_verhuurd_onroerend_goed", "Inkomen uit verhuurd onroerend goed"),
            ("inkomen_uit_vermogen", "Inkomen uit vermogen"),
            ("overig_box3_inkomen", "Overig Box 3 inkomen"),
            ("totaal_vrij_beschikbaar_vermogen_3112", "Totaal vrij beschikbaar vermogen per 31-12"),
            ("deel_box3_inzetten_bij_onderneming", "Deel Box 3 inzetten bij deze onderneming"),
            ("surplus_werkkapitaal", "Surplus Werkkaptaal (SrplWK)"),
            ("totaal_ontvangen_surplus", "Totaal ontvangen surplus"),
        ],
    },
]


def parse_json_blob(value: str) -> Dict[str, float]:
    if not value:
        return {}
    try:
        obj = json.loads(value)
        if isinstance(obj, dict):
            out = {}
            for k, v in obj.items():
                try:
                    out[str(k)] = float(v or 0)
                except Exception:
                    out[str(k)] = 0.0
            return out
    except Exception:
        pass
    return {}


def derive_core_from_detail(bs: Dict[str, float], pl: Dict[str, float], ib: Dict[str, float]) -> Dict[str, float]:
    current_assets = bs.get("totaal_vlottende_activa", 0.0) or (
        bs.get("voorraden_totaal", 0.0) + bs.get("debiteuren_vorderingen", 0.0) + bs.get("overige_vlottende_activa", 0.0) + bs.get("liquide_middelen", 0.0)
    )
    current_liabilities = bs.get("totaal_kortlopende_schulden", 0.0)
    other_cl = max(0.0, current_liabilities - bs.get("crediteuren", 0.0) - bs.get("belastingen_en_premies", 0.0))

    turnover = pl.get("totale_omzet", 0.0)
    cogs = pl.get("totaal_inkoopwaarde_omzet", 0.0)
    op_costs = pl.get("totaal_bedrijfskosten", 0.0)
    depreciation = pl.get("afschrijvingen", 0.0) or (
        pl.get("totaal_afschrijvingen_immateriele_activa", 0.0) + pl.get("totaal_afschrijvingen_materiele_activa", 0.0)
    )
    fin_income = pl.get("financiele_baten", 0.0)
    fin_expense = pl.get("financiele_lasten", 0.0)
    extraordinary_income = pl.get("buitengewone_baten", 0.0)
    extraordinary_expense = pl.get("buitengewone_lasten", 0.0)
    net_result = pl.get("netto_winst_resultaat", 0.0) or pl.get("netto_winst_voor_belasting", 0.0)
    prognose = pl.get("prognose_volledig_jaar", 0.0)

    saldo_fiscale_winst = ib.get("saldo_fiscale_winst", 0.0)
    private_use_car = ib.get("privegebruik_auto", 0.0)
    box1_before = ib.get("looninkomsten_voor_starten_onderneming", 0.0)
    box1_during = ib.get("looninkomen_naast_tijdens_ondernemerschap", 0.0)
    box1_benefits = ib.get("inkomensvervangende_uitkeringen", 0.0)
    box1_row = ib.get("inkomsten_uit_overige_werkzaamheden", 0.0)
    other_box1_income = ib.get("overige_box1_inkomsten", 0.0)
    dividend = ib.get("totaal_genoten_dividend", 0.0)

    return {
        "inventories": bs.get("voorraden_totaal", 0.0),
        "receivables": bs.get("debiteuren_vorderingen", 0.0),
        "other_current_assets": bs.get("overige_vlottende_activa", 0.0),
        "cash": bs.get("liquide_middelen", 0.0),
        "creditors": bs.get("crediteuren", 0.0),
        "taxes_payable": bs.get("belastingen_en_premies", 0.0),
        "other_current_liabilities": other_cl,
        "current_assets": current_assets,
        "current_liabilities": current_liabilities,
        "equity": bs.get("totaal_eigen_vermogen", 0.0),
        "total_assets": bs.get("totaal_activa", 0.0) or bs.get("totaal_passiva", 0.0),
        "intangible_assets": bs.get("totaal_immateriele_vaste_activa", 0.0),
        "turnover_total": turnover,
        "cogs_total": cogs,
        "operating_costs_total": op_costs,
        "depreciation_total": depreciation,
        "financial_income_total": fin_income,
        "financial_expense_total": fin_expense,
        "extraordinary_income_total": extraordinary_income,
        "extraordinary_expense_total": extraordinary_expense,
        "net_result_no_ib": net_result,
        "prognose_income": prognose,
        "saldo_fiscale_winst": saldo_fiscale_winst,
        "private_use_car": private_use_car,
        "box1_wage_before_start": box1_before,
        "box1_wage_during": box1_during,
        "box1_benefits": box1_benefits,
        "box1_row": box1_row,
        "other_box1_income": other_box1_income,
        "dividend": dividend,
    }


BALANCE_TOTAL_FORMULAS = {
    "totaal_immateriele_vaste_activa": [
        "goodwill_niet_tot_ev", "goodwill_tot_ev", "onderzoek_en_ontwikkeling", "investeringen_ontwikkelingskosten",
        "licenties_octrooien_patenten", "overig_onderzoek_ontwikkeling", "overige_immateriele_vaste_activa"
    ],
    "totaal_materiele_vaste_activa": [
        "onroerend_goed", "terreinen", "gebouwen", "overig_onroerend_goed", "overige_materiele_vaste_activa",
        "machines_installaties", "inventaris_gereedschappen_productie", "inventaris_kantoor", "automatisering", "vervoermiddelen", "andere_materiele_vaste_activa"
    ],
    "totaal_financiele_vaste_activa": [
        "deelnemingen", "deelnemingen_groepsmaatschappijen", "overige_deelnemingen", "vorderingen_langlopend",
        "vorderingen_niet_op_dir_ahr_groep_participanten_lang", "totaal_vorderingen_dir_ahr_groep_participanten_lang",
        "vorderingen_ahr_groepsmij_participanten_niet_achtergesteld_lang", "andere_vorderingen_dir_ahr_groep_participanten_lang",
        "overige_vorderingen_lang", "latente_belastingvorderingen_lang", "andere_vorderingen_lang",
        "overige_financiele_vaste_activa", "effecten", "waarborgsommen", "andere_financiele_vaste_activa"
    ],
    "totaal_vaste_activa": ["totaal_immateriele_vaste_activa", "totaal_materiele_vaste_activa", "totaal_financiele_vaste_activa"],
    "voorraden_totaal": ["voorraden", "grond_hulpstoffen", "inkopen_onderdelen", "gereed_product", "onderhanden_werk", "vooruitbetaling_voorraden", "totaal_overige_voorraden", "incourante_voorraden", "andere_voorraden"],
    "totaal_debiteuren": ["debiteuren_standaard", "dubieuze_debiteuren", "overige_debiteuren"],
    "totaal_vorderingen": ["vorderingen_ahr_groepsmij_participanten_kort_niet_achtergesteld", "overige_vorderingen_ahr_groepsmaatschappijen_participanten_kort", "latente_belastingvorderingen_kort", "overige_vorderingen"],
    "debiteuren_vorderingen": ["totaal_debiteuren", "totaal_vorderingen"],
    "overige_vlottende_activa": ["te_vorderen_omzetbelasting", "vooruitbetaalde_bedragen", "nog_te_ontvangen_bedragen", "nog_te_factureren_gereed_product", "te_ontvangen_rente", "overlopende_activa", "andere_vlottende_activa"],
    "liquide_middelen": ["kas", "bankrekeningen", "spaarrekeningen", "depositorekeningen", "beleggingsrekeningen", "kruisposten", "overige_liquide_middelen"],
    "totaal_vlottende_activa": ["voorraden_totaal", "debiteuren_vorderingen", "overige_vlottende_activa", "liquide_middelen"],
    "totaal_activa": ["totaal_vaste_activa", "totaal_vlottende_activa"],
    "totaal_eigen_vermogen": ["kapitaal_eenmanszaak", "kapitaal_begin_saldo", "winstsaldo_lopend_boekjaar", "prive_stortingen", "prive_onttrekkingen_privegebruik_auto", "overige_prive_onttrekkingen", "wettelijke_statutaire_reserves", "overige_reserves", "algemene_reserve", "dividenduitkering_boekjaar", "resultaatbestemming_boekjaar", "andere_reserves", "onverdeelde_winst"],
    "totaal_voorzieningen": ["for_aanvrager", "voorzieningen_latente_belastingen", "voorzieningen_dubieuze_debiteuren", "overige_voorzieningen", "onderhoudsvoorziening", "garantievoorziening", "assurantievoorziening", "voorziening_incourante_goederen", "voorziening_reorganisatie_kosten", "pensioenvoorziening_personeel", "stamrechtvoorziening", "andere_voorzieningen"],
    "totaal_langlopende_schulden": ["achtergestelde_leningen_langlopend", "achtergestelde_leningen_lang", "achtergestelde_leningen_lang_kredietinstellingen", "achtergestelde_leningen_lang_dga_eigenaar", "achtergestelde_leningen_lang_ahr_groepmij", "overige_achtergestelde_leningen_lang", "schulden_kredietinstellingen_lang_niet_achtergesteld", "hypothecaire_leningen", "converteerbare_leningen", "obligatieleningen_onderhandse_leningen", "leaseverplichtingen", "schulden_directie_ahr_groepmij_lang_niet_achtergesteld", "schulden_ahr_groepsmij_participanten_lang_niet_achtergesteld", "overige_langlopende_leningen", "schulden_leveranciers_handelskredieten_lang", "andere_langlopende_leningen"],
    "totaal_kortlopende_schulden": ["achtergestelde_leningen_kort", "achtergestelde_leningen_kort_kredietinstellingen", "achtergestelde_leningen_kort_dga_eigenaar", "overige_achtergestelde_leningen_kort", "crediteuren", "schulden_kredietinstellingen_kort_niet_achtergesteld", "schulden_directie_ahr_groepmij_kort_niet_achtergesteld", "schulden_ahr_groepsmij_participanten_kort_niet_achtergesteld", "belastingen_en_premies", "te_betalen_omzetbelasting", "te_betalen_vennootschapsbelasting", "te_betalen_loonbelasting", "te_betalen_premies_sociale_verzekeringen", "andere_belastingen_premies", "te_betalen_pensioenen", "overige_kortlopende_schulden", "accountantskosten", "reservering_vakantiegeld_vakantiedagen", "aflossingsverplichtingen", "andere_schulden_kort"],
    "totaal_passiva": ["totaal_eigen_vermogen", "totaal_voorzieningen", "totaal_langlopende_schulden", "totaal_kortlopende_schulden"],
}

PL_TOTAL_FORMULAS = {
    "totale_omzet": ["omzet_basisomzet", "omzet_uitbesteed_werk_derden", "kortingen_bonussen", "andere_omzet", "wijziging_voorraden_gereed_product", "wijziging_onderhanden_werk", "overige_bedrijfsopbrengsten", "doorbelastingen", "huuropbrengsten", "andere_bedrijfsopbrengsten"],
    "totaal_inkoopwaarde_omzet": ["inkopen", "verbruik_grondstoffen", "verbruik_onderdelen", "verbruik_hulpstoffen", "voorraadmutatie", "kosten_uitbesteed_werk_externe", "prive_gebruik_goederen", "andere_inkoopwaarde_omzet"],
    "financiele_baten": ["rentebaten_banktegoeden", "rentebaten_vorderingen_directie", "rentebaten_vorderingen_ahr_participanten_groepmij_deelnemingen", "rentebaten_hypotheken", "rentebaten_lease", "rentebaten_belastingen", "opbrengst_financiele_vaste_activa_excl_deelnemingen", "overige_rentebaten"],
    "financiele_lasten": ["rentelasten_banktegoeden", "rentelasten_vorderingen_directie", "rentelasten_vorderingen_ahr_participanten_groepmij_deelnemingen", "rentelasten_hypotheken", "rentelasten_lease", "rentelasten_belastingen", "waardedaling_financiele_vaste_activa_excl_deelnemingen", "overige_rentelasten"],
    "buitengewone_baten": ["waarvan_kor", "buitengewone_baten_niet_fiscaal", "buitengewone_baten_fiscaal"],
    "buitengewone_lasten": ["buitengewone_lasten_niet_fiscaal", "buitengewone_lasten_fiscaal"],
}

PL_COST_COMPONENTS = [
    "afschrijvingen", "totaal_afschrijvingen_immateriele_activa", "afschrijving_onderzoek_ontwikkeling", "afschrijving_goodwill", "willekeurige_afschrijvingen_immateriele_activa", "overige_afschrijvingen_immateriele_activa", "totaal_afschrijvingen_materiele_activa", "afschrijvingen_gebouwen_terreinen", "afschrijvingen_machines_installatie", "afschrijvingen_inventaris_gereedschappen", "afschrijvingen_kantoorinventaris", "afschrijvingen_vervoermiddelen_bestel_vrachtauto", "afschrijvingen_vervoermiddelen_personenautos", "willekeurige_afschrijvingen_materiele_vaste_activa", "overige_afschrijvingen_materiele_activa", "huisvestingskosten", "huurkosten", "energie_water", "ozb", "onderhoud_reparatie_huisvesting", "verzekeringskosten_huisvesting", "overige_huisvestingskosten", "autokosten", "kosten_vervoermiddelen", "leasekosten", "onderhoud_reparatie_vervoer", "brandstoffen_vervoer", "verzekeringen_vervoer", "belastingen_vervoer", "boetes_vervoer", "overige_kosten_vervoermiddelen", "privegebruik_auto_negatieve_autokosten", "btw_privegebruik_auto", "kosten_openbaar_vervoer", "kilometervergoeding", "overige_autokosten", "personeelskosten", "loonkosten", "management_vergoeding", "meewerk_vergoeding", "arbeidsvergoeding", "sociale_lasten", "pensioen_lasten", "doorberekende_personeelskosten", "ziekengeld_verzekering", "overige_personeelskosten", "andere_bedrijfskosten", "machine_exploitatiekosten", "onderhoud_reparaties_machines", "lease_huurkosten_machines", "kleine_aanschaffingen", "verzekeringen", "overige_machine_exploitatiekosten", "verkoop_advertentiekosten", "reclame_advertentiekosten", "kosten_sponsoring", "relatiegeschenken_representatiekosten", "reis_verblijfskosten", "dotatie_voorziening_dubieuze_debiteuren", "overige_verkoopkosten", "kantoorkosten", "kantoorbenodigdheden", "telecommunicatie_internet", "onderhoud_reparaties_kantoor", "porti", "drukwerk", "kosten_automatisering", "kantoorverzekering", "overige_kantoorkosten", "algemene_kosten", "algemene_verzekeringen", "contributies_abonnementen", "accountancy_kosten", "advieskosten", "af_te_boeken_verschillen", "overige_bedrijfskosten_overig"
]

IB_TOTAL_FORMULAS = {
    "totaal_vergoedingen_ondernemer": ["arbeidsvergoeding_ondernemer", "privegebruik_auto_ondernemer", "rentevergoeding_ondernemer", "overige_vergoedingen_ondernemer"],
    "totaal_vergoedingen_overige_vennoten_maten": ["arbeidsvergoeding_overige_vennoten_maten", "privegebruik_auto_overige_vennoten_maten", "rentevergoeding_overige_vennoten_maten", "overige_vergoedingen_overige_vennoten_maten"],
    "totaal_vergoedingen_alle_vennoten_maten": ["totaal_vergoedingen_ondernemer", "totaal_vergoedingen_overige_vennoten_maten"],
    "totaal_overige_box1_inkomsten": ["looninkomsten_voor_starten_onderneming", "looninkomen_naast_tijdens_ondernemerschap", "inkomensvervangende_uitkeringen", "inkomsten_uit_overige_werkzaamheden", "overige_box1_inkomsten"],
}
