import pathlib
import tempfile

import pytest

from agent.runner import APPROVAL_THRESHOLD, run_once
from agent.store import Crm


@pytest.fixture
def crm():
    return Crm(pathlib.Path(tempfile.mkdtemp()) / "crm.db")


def test_every_lead_is_processed_and_logged(crm):
    run = run_once(crm)
    assert len(crm.all()) == 7
    assert all(s.status == "ok" for s in run.steps)
    assert run.steps[0].tool == "fetch_new_leads"
    assert run.steps[-1].tool == "post_team_summary"


def test_blocked_lead_never_gets_a_reply_drafted(crm):
    run_once(crm)
    spam = crm.get("LD-4476")
    assert spam["guardrail"] == "blocked"
    assert spam["status"] == "blocked"
    assert spam["reply"] is None


def test_high_score_waits_for_a_person(crm):
    run_once(crm)
    for lead_id in ("LD-4473", "LD-4477", "LD-4471"):
        row = crm.get(lead_id)
        assert row["score"] >= APPROVAL_THRESHOLD
        assert row["status"] == "awaiting approval", lead_id


def test_low_score_is_answered_without_a_person(crm):
    run_once(crm)
    row = crm.get("LD-4475")
    assert row["score"] < APPROVAL_THRESHOLD
    assert row["status"] == "replied automatically"
    assert row["reply"]


def test_a_second_run_finds_nothing_new(crm):
    run_once(crm)
    second = run_once(crm)
    assert second.steps[0].summary.startswith("0 new submissions")
    assert len(crm.all()) == 7


def test_approval_is_recorded_with_who_and_when(crm):
    run_once(crm)
    crm.set_decision("LD-4473", "reply sent", "ha@fernwood.example", "2026-10-04T18:00:00+00:00")
    row = crm.get("LD-4473")
    assert row["status"] == "reply sent"
    assert row["decided_by"] == "ha@fernwood.example"
    assert row["decided_at"].startswith("2026-10-04")
