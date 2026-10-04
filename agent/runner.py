"""The agent loop. Every tool call is recorded so the run can be audited afterwards."""

import time
from datetime import datetime, timezone

from .guardrails import domain_of
from .tools import Tools

APPROVAL_THRESHOLD = 65


class Step:
    def __init__(self, tool, args, lead_id=None):
        self.tool = tool
        self.args = args
        self.lead_id = lead_id
        self.status = "running"
        self.summary = ""
        self.detail = None
        self.ms = 0.0


class Run:
    def __init__(self):
        self.started = datetime.now(timezone.utc).isoformat(timespec="seconds")
        self.steps = []
        self.rows = []
        self.summary = ""

    def as_dict(self):
        return {
            "started": self.started,
            "summary": self.summary,
            "steps": [
                {
                    "n": i + 1, "tool": s.tool, "args": s.args, "lead_id": s.lead_id,
                    "status": s.status, "summary": s.summary, "detail": s.detail, "ms": s.ms,
                }
                for i, s in enumerate(self.steps)
            ],
        }


def _call(run, tool, args, fn, lead_id=None):
    step = Step(tool, args, lead_id)
    run.steps.append(step)
    start = time.perf_counter()
    try:
        result, summary = fn()
        step.status = "ok"
        step.summary = summary
        step.detail = result
    except Exception as exc:
        step.status = "error"
        step.summary = str(exc)[:200]
        result = None
    step.ms = round((time.perf_counter() - start) * 1000, 1)
    return result


def run_once(crm):
    """Process every new lead end to end. Returns a Run with the full log."""
    tools = Tools(crm)
    run = Run()

    leads = _call(run, "fetch_new_leads", {}, tools.fetch_new_leads) or []

    for lead in leads:
        lid = lead["id"]
        company = _call(run, "enrich_company", {"domain": domain_of(lead["email"])},
                        lambda l=lead: tools.enrich_company(l), lid) or {}
        score = _call(run, "score_lead", {"lead_id": lid},
                      lambda l=lead, c=company: tools.score_lead(l, c), lid)
        guard = _call(run, "run_guardrails", {"lead_id": lid},
                      lambda l=lead, c=company, s=score: tools.run_guardrails(l, c, s), lid)

        reply = None
        if guard["verdict"] == "blocked":
            status = "blocked"
        else:
            drafted = _call(run, "draft_reply", {"lead_id": lid},
                            lambda l=lead, s=score: tools.draft_reply(l, s), lid)
            reply = (drafted or {}).get("reply")
            if score["score"] >= APPROVAL_THRESHOLD or guard["verdict"] == "flagged":
                _call(run, "request_approval", {"lead_id": lid},
                      lambda l=lead, s=score: tools.request_approval(l, s), lid)
                status = "awaiting approval"
            else:
                status = "replied automatically"

        row = {
            "id": lid,
            "received_at": lead["received_at"],
            "name": lead["name"],
            "email": lead["email"],
            "company": lead.get("company") or (company.get("name") if company else ""),
            "industry": company.get("industry", ""),
            "employees": company.get("employees", 0),
            "budget_usd": score["budget_usd"],
            "score": score["score"],
            "band": score["band"],
            "guardrail": guard["verdict"],
            "status": status,
            "reply": reply,
            "decided_by": None,
            "decided_at": None,
        }
        _call(run, "save_to_crm", {"lead_id": lid}, lambda r=row: tools.save_to_crm(r), lid)
        run.rows.append(row)

    posted = _call(run, "post_team_summary", {}, lambda: tools.post_team_summary(run.rows))
    run.summary = (posted or {}).get("message", "Nothing new to process")
    return run
