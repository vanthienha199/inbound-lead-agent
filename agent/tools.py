"""The agent's tool belt. Every tool has a schema, so the log can show what was called."""

import json
import pathlib

from .guardrails import domain_of, run as run_guardrails, verdict
from .scoring import score_lead

DATA = pathlib.Path(__file__).resolve().parent.parent / "data"

SCHEMA = [
    {"name": "fetch_new_leads", "args": {}, "returns": "list of form submissions not yet in the CRM"},
    {"name": "enrich_company", "args": {"domain": "string"}, "returns": "industry, employees, country"},
    {"name": "score_lead", "args": {"lead_id": "string"}, "returns": "score 0 to 100, band, reason per criterion"},
    {"name": "run_guardrails", "args": {"lead_id": "string"}, "returns": "findings and a verdict of clear, flagged or blocked"},
    {"name": "draft_reply", "args": {"lead_id": "string"}, "returns": "a first reply, written by the model"},
    {"name": "request_approval", "args": {"lead_id": "string"}, "returns": "pauses the run and waits for a person"},
    {"name": "save_to_crm", "args": {"lead_id": "string"}, "returns": "the row written to SQLite"},
    {"name": "post_team_summary", "args": {}, "returns": "one message for the team channel"},
]


def load_leads():
    return [json.loads(line) for line in (DATA / "leads.jsonl").read_text().splitlines() if line.strip()]


def load_companies():
    return json.loads((DATA / "companies.json").read_text())


class Tools:
    """Each method is one tool call. They return (result, summary) so the run log
    can print a one line summary without re-deriving it."""

    def __init__(self, crm):
        self.crm = crm
        self.companies = load_companies()

    def fetch_new_leads(self):
        leads = load_leads()
        known = {r["id"] for r in self.crm.all()}
        fresh = [l for l in leads if l["id"] not in known]
        return fresh, f"{len(fresh)} new submissions, {len(leads) - len(fresh)} already in the CRM"

    def enrich_company(self, lead):
        domain = domain_of(lead.get("email", ""))
        company = self.companies.get(domain)
        if not company:
            return {}, f"No record for {domain or 'an unknown domain'}"
        return company, f"{company['name']}, {company['industry']}, {company['employees']} employees, {company['country']}"

    def score_lead(self, lead, company):
        s = score_lead(lead, company)
        return s, f"{s['score']} out of 100, band {s['band']}"

    def run_guardrails(self, lead, company, score):
        findings = run_guardrails(lead, company, score)
        v = verdict(findings)
        if not findings:
            return {"findings": [], "verdict": v}, "No rule matched"
        return {"findings": findings, "verdict": v}, f"{v}: {findings[0]['rule']}"

    def draft_reply(self, lead, score):
        from .llm import draft
        text, backend = draft(lead, score)
        words = len(text.split())
        return {"reply": text, "backend": backend}, f"{words} word reply drafted by {backend}"

    def request_approval(self, lead, score):
        return (
            {"required": True, "reason": f"band {score['band']}, {score['score']} out of 100"},
            "Paused for a person. Nothing is sent until someone approves",
        )

    def save_to_crm(self, row):
        self.crm.upsert(row)
        return row, f"Row {row['id']} written with status {row['status']}"

    def post_team_summary(self, rows):
        hot = [r for r in rows if r["band"] in ("hot", "warm")]
        blocked = [r for r in rows if r["guardrail"] == "blocked"]
        waiting = [r for r in rows if r["status"] == "awaiting approval"]
        msg = (
            f"{len(rows)} new enquiries. {len(hot)} worth a call, "
            f"{len(waiting)} waiting on your approval, {len(blocked)} blocked as spam."
        )
        return {"message": msg}, msg
