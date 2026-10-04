"""Guardrails run before anything is drafted or written. Each one can block or flag."""

import re

SPAM_MARKERS = [
    "guarantee first page", "guaranteed first page", "free audit", "reply yes",
    "unsubscribe at any time", "dear sir/madam", "not ranking for key terms",
]
COMPETITOR_MARKERS = ["partnership", "referral arrangement", "overflow", "white label", "white-label"]
DISPOSABLE = ("rank-faster-now.biz", "mailinator.com", "guerrillamail.com")
EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[a-z]{2,}$", re.I)


def domain_of(email):
    return email.split("@")[-1].lower() if "@" in (email or "") else ""


def run(lead, company, score):
    """Return a list of findings. Any finding with action 'block' stops the run."""
    findings = []
    text = f"{lead.get('message','')} {lead.get('company','')} {lead.get('name','')}".lower()

    hits = [m for m in SPAM_MARKERS if m in text]
    if len(hits) >= 2:
        findings.append({
            "rule": "Unsolicited sales outreach",
            "action": "block",
            "detail": f"Matched {len(hits)} solicitation phrases, including \"{hits[0]}\"",
        })

    if domain_of(lead.get("email", "")) in DISPOSABLE:
        findings.append({
            "rule": "Sender domain on the blocklist",
            "action": "block",
            "detail": f"Domain {domain_of(lead.get('email',''))} is on the blocklist",
        })

    industry = (company or {}).get("industry", "")
    if industry == "Design agency" or any(m in text for m in COMPETITOR_MARKERS):
        findings.append({
            "rule": "Competitor or partnership enquiry",
            "action": "flag",
            "detail": "Reads as an agency to agency approach, not a client project. Route to the partnerships inbox.",
        })

    if not EMAIL.match(lead.get("email", "") or ""):
        findings.append({
            "rule": "Contact details incomplete",
            "action": "flag",
            "detail": "No usable email address, so no reply can be sent",
        })

    if score["budget_usd"] is not None and score["budget_usd"] < 2_000:
        findings.append({
            "rule": "Budget far below the floor",
            "action": "flag",
            "detail": f"About {score['budget_usd']:,} USD against a 12,000 USD minimum project",
        })

    return findings


def verdict(findings):
    if any(f["action"] == "block" for f in findings):
        return "blocked"
    if any(f["action"] == "flag" for f in findings):
        return "flagged"
    return "clear"
