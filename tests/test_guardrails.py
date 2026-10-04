from agent.guardrails import run, verdict


def test_sales_spam_is_blocked():
    lead = {"email": "outreach@rank-faster-now.biz", "name": "X", "company": "Rank Faster Now",
            "message": "Dear Sir/Madam, we guarantee first page results. Reply YES for your free audit. Unsubscribe at any time."}
    findings = run(lead, {}, {"budget_usd": None})
    assert verdict(findings) == "blocked"


def test_competitor_is_flagged_not_blocked():
    lead = {"email": "a@pinefield.studio", "name": "A", "company": "Pinefield Studio",
            "message": "Would you be open to a partnership or referral arrangement for overflow projects?"}
    findings = run(lead, {"industry": "Design agency"}, {"budget_usd": None})
    assert verdict(findings) == "flagged"
    assert all(f["action"] != "block" for f in findings)


def test_a_real_enquiry_passes_clean():
    lead = {"email": "m@tradewinds-logistics.com", "name": "M", "company": "Tradewinds",
            "message": "Board approved a customer portal replacement, we need discovery design and build."}
    assert verdict(run(lead, {"industry": "Logistics"}, {"budget_usd": 62000})) == "clear"


def test_tiny_budget_is_flagged():
    lead = {"email": "a@b.com", "name": "A", "company": "B", "message": "hello"}
    findings = run(lead, {}, {"budget_usd": 400})
    assert verdict(findings) == "flagged"
