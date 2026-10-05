"""Pluggable reply writing. Backend is chosen with AGENT_BACKEND."""

import json
import os
import subprocess
import urllib.request

SYSTEM = (
    "You write a short first reply from Studio Lind, a web and brand design agency, "
    "to someone who filled in the contact form.\n"
    "Rules:\n"
    "1. Four sentences at most. No greeting line longer than four words.\n"
    "2. Name one specific thing from their message so it is clearly not a template.\n"
    "3. Propose one concrete next step with a named time window.\n"
    "4. Never invent a price, a delivery date or a capability that was not given to you.\n"
    "5. Plain English. No em dashes. No exclamation marks.\n"
    "6. Write as the studio. Use we, never I, and do not sign a personal name."
)


def _prompt(lead, score):
    return (
        f"{SYSTEM}\n\n"
        f"Their name: {lead['name']}\n"
        f"Company: {lead.get('company') or 'not given'}\n"
        f"Budget they stated: {lead.get('budget_text') or 'not given'}\n"
        f"Timeline they stated: {lead.get('timeline') or 'not given'}\n"
        f"Their message: {lead['message']}\n"
        f"Internal qualification band: {score['band']}\n\n"
        "Write only the body of the email."
    )


def _anthropic(lead, score, model):
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set")
    body = json.dumps({
        "model": model, "max_tokens": 400,
        "messages": [{"role": "user", "content": _prompt(lead, score)}],
    }).encode()
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages", data=body,
        headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)["content"][0]["text"].strip()


def _claude_cli(lead, score, model):
    env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
    proc = subprocess.run(
        ["claude", "-p", _prompt(lead, score), "--model", model],
        capture_output=True, text=True, env=env, timeout=180,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"claude cli failed: {proc.stderr[:200]}")
    return proc.stdout.strip()


def _template(lead, score, model):
    """No key needed. Deterministic, so the tests can assert on it."""
    first = lead["name"].split()[0]
    topic = "your project"
    for kw, label in (("booking", "the online booking work"), ("portal", "the customer portal"),
                      ("configurator", "the product configurator"), ("donation", "the donation flow"),
                      ("rebuild", "the rebuild")):
        if kw in lead["message"].lower():
            topic = label
            break
    return (
        f"Hello {first},\n\n"
        f"Thank you for getting in touch about {topic}. It is the kind of work we take on most often, "
        f"and what you described is clear enough for us to be useful quickly.\n\n"
        f"Could we book 30 minutes this week to walk through the detail and what a first phase would cover. "
        f"If you send two or three times that suit you, we will confirm one today.\n\n"
        f"Best regards,\nStudio Lind"
    )


BACKENDS = {"anthropic": _anthropic, "claude_cli": _claude_cli, "template": _template}


def draft(lead, score):
    name = os.environ.get("AGENT_BACKEND", "template")
    model = os.environ.get("AGENT_MODEL", "claude-haiku-4-5-20251001")
    order = [name] + [b for b in ("claude_cli", "template") if b != name]
    errors = []
    for backend in order:
        try:
            return BACKENDS[backend](lead, score, model), backend
        except Exception as exc:
            errors.append(f"{backend}: {exc}")
    raise RuntimeError("; ".join(errors))
