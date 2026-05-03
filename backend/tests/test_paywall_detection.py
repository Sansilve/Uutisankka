from app.services.paywall import assess_paywall


def test_clear_free_article():
    content = (
        "Yritys julkaisi uuden tuotteen ja kertoi laajasta kansainvalisesta strategiasta. "
        "Artikkelissa kuvataan markkinat, taustat ja vaikutukset useassa kappaleessa. "
        "Lisaksi mukana on asiantuntijakommentteja ja tarkkoja numeroita liikevaihdosta. "
        "Lopussa analysoidaan seuraavia askeleita ja riskeja."
    )
    result = assess_paywall(title="Uusi strategia julki", content=content, source="Yle")
    assert result.status == "free"
    assert result.score <= 0.30


def test_clear_paywalled_article():
    content = (
        "Vain tilaajille. Lue koko juttu tilaamalla. "
        "Continue reading for subscribers only."
    )
    result = assess_paywall(title="Sisalto lukittu", content=content, source="Helsingin Sanomat")
    assert result.status == "paywalled"
    assert result.score >= 0.70


def test_scrape_fail_but_actually_free_not_paywalled():
    content = (
        "Pitka artikkeli kertoo yksityiskohtaisesti tilanteesta, sisaltaa taustaa, "
        "kommentteja ja laajan analyysin ilman tilaajaviitteita. "
        "Teksti jatkuu useilla luonnollisilla kappaleilla ja muodostaa ehean rungon."
    )
    result = assess_paywall(
        title="Laaja analyysi markkinoista",
        content=content,
        source="Reuters",
        scrape_failed=True,
    )
    assert result.status != "paywalled"


def test_scrape_success_but_teaser_paywall():
    content = "Lue lisaa tilaamalla... Vain tilaajille."
    result = assess_paywall(
        title="Iso paljastus",
        content=content,
        source="Talouselama",
        scrape_failed=False,
    )
    assert result.status == "paywalled"


def test_conflicting_case_returns_uncertain():
    content = (
        "Artikkeli alkaa normaalisti mutta on melko lyhyt. "
        "Mukana ei ole selvaa tilaajatekstia, mutta runko muistuttaa teaseria."
    )
    result = assess_paywall(
        title="Sekalainen tapaus",
        content=content,
        source="Ilta-Sanomat",
        scrape_failed=False,
        source_overrides={"Ilta-Sanomat": 0.05},
    )
    assert result.status == "uncertain"


def test_source_override_support_changes_score_direction():
    content = "Lyhyt teksti ilman tilaajasanoja mutta ei aivan tyhja."
    baseline = assess_paywall(title="Case", content=content, source="Example Source")
    overridden = assess_paywall(
        title="Case",
        content=content,
        source="Example Source",
        source_overrides={"Example Source": 0.30},
    )
    assert overridden.score > baseline.score
