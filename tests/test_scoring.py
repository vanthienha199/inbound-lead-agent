from agent.scoring import parse_budget, score_lead


def test_parses_each_currency_to_usd():
    assert parse_budget("around 18,500 GBP")[0] == 23495
    assert parse_budget("EUR 41,000")[0] == 44280
    assert parse_budget("$62,000 approved")[0] == 62000


def test_ignores_vague_amounts():
    assert parse_budget("not sure yet, maybe a few hundred")[0] is None
    assert parse_budget("")[0] is None
    assert parse_budget("n/a")[0] is None


def test_k_suffix_is_expanded():
    assert parse_budget("about 40k")[0] == 40000


def test_budget_below_the_floor_scores_low():
    lead = {"budget_text": "$3,000", "timeline": "", "message": "hi"}
    result = score_lead(lead, {})
    assert result["band"] == "low"
    assert any(r[0] == "Budget" and r[1] == 5 for r in result["reasons"])


def test_every_point_has_a_written_reason():
    lead = {"budget_text": "$62,000", "timeline": "kickoff within 3 weeks",
            "message": "We need a portal rebuild with ERP integration " * 5}
    result = score_lead(lead, {"employees": 310})
    assert result["score"] == sum(points for _, points, _ in result["reasons"])
    assert all(isinstance(text, str) and text for _, _, text in result["reasons"])
