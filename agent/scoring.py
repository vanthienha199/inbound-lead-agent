"""Deterministic lead scoring. No model is involved, so the score is auditable."""

import re

# Fixture rates. A real deployment would read these from the finance system.
USD_PER = {"USD": 1.0, "GBP": 1.27, "EUR": 1.08}
PROJECT_FLOOR_USD = 12_000

MONEY = re.compile(r"(?P<sym>[£$€])?\s*(?P<num>\d[\d,]*(?:\.\d+)?)\s*(?P<code>GBP|EUR|USD|K)?", re.I)
SYMBOL_CODE = {"£": "GBP", "$": "USD", "€": "EUR"}


def parse_budget(text):
    """Return (usd_amount, currency, raw) or (None, None, raw) when nothing parses."""
    if not text:
        return None, None, text
    upper = text.upper()
    for m in MONEY.finditer(text):
        raw_num = m.group("num").replace(",", "")
        try:
            value = float(raw_num)
        except ValueError:
            continue
        code = (m.group("code") or "").upper()
        if code == "K":
            value *= 1000
            code = ""
        if value < 50:  # "a few hundred" style noise, or a stray year
            continue
        currency = SYMBOL_CODE.get(m.group("sym") or "") or code
        if not currency:
            for name in ("GBP", "EUR", "USD"):
                if name in upper:
                    currency = name
                    break
        currency = currency or "USD"
        return round(value * USD_PER.get(currency, 1.0)), currency, text
    return None, None, text


def score_lead(lead, company):
    """Return a score out of 100 with the reason for every point awarded."""
    reasons = []
    total = 0

    usd, currency, _ = parse_budget(lead.get("budget_text", ""))
    if usd is None:
        reasons.append(("Budget", 0, "No budget stated"))
    elif usd >= PROJECT_FLOOR_USD * 3:
        total += 40
        reasons.append(("Budget", 40, f"About {usd:,} USD, well above the {PROJECT_FLOOR_USD:,} floor"))
    elif usd >= PROJECT_FLOOR_USD:
        total += 30
        reasons.append(("Budget", 30, f"About {usd:,} USD, above the {PROJECT_FLOOR_USD:,} floor"))
    else:
        total += 5
        reasons.append(("Budget", 5, f"About {usd:,} USD, below the {PROJECT_FLOOR_USD:,} floor"))

    timeline = (lead.get("timeline") or "").lower()
    if any(w in timeline for w in ("week", "immediately", "asap", "kickoff")):
        total += 20
        reasons.append(("Timeline", 20, "Starts within weeks"))
    elif any(w in timeline for w in ("month", "november", "december", "january", "q1", "q2")):
        total += 15
        reasons.append(("Timeline", 15, "Named a month or quarter"))
    elif timeline and timeline not in ("n/a", "whenever"):
        total += 8
        reasons.append(("Timeline", 8, "Loose timeline"))
    else:
        reasons.append(("Timeline", 0, "No timeline given"))

    message = lead.get("message", "")
    words = len(message.split())
    specifics = sum(
        1 for kw in ("integration", "integrat", "booking", "portal", "configurator",
                     "erp", "migration", "discovery", "donation", "api", "rebuild")
        if kw in message.lower()
    )
    if words >= 40 and specifics >= 2:
        total += 20
        reasons.append(("Scope clarity", 20, f"{words} words, {specifics} concrete requirements"))
    elif words >= 25 or specifics >= 1:
        total += 12
        reasons.append(("Scope clarity", 12, f"{words} words, {specifics} concrete requirements"))
    else:
        total += 3
        reasons.append(("Scope clarity", 3, f"Only {words} words and no concrete requirement"))

    employees = (company or {}).get("employees", 0)
    if employees >= 100:
        total += 20
        reasons.append(("Company size", 20, f"{employees} employees"))
    elif employees >= 20:
        total += 14
        reasons.append(("Company size", 14, f"{employees} employees"))
    elif employees > 0:
        total += 6
        reasons.append(("Company size", 6, f"{employees} employees"))
    else:
        reasons.append(("Company size", 0, "Company not found in the enrichment source"))

    band = "hot" if total >= 75 else "warm" if total >= 55 else "nurture" if total >= 30 else "low"
    return {"score": total, "band": band, "reasons": reasons, "budget_usd": usd, "currency": currency}
