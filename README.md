# Inbound lead agent, with a run log, guardrails and a human approval gate

An AI agent that works an inbound lead inbox end to end: it reads new form submissions,
enriches each company, scores the lead against a written rubric, runs guardrails, drafts a
reply, and then stops and waits for a person before anything is sent. Every tool call is
recorded with its arguments, its result and how long it took, so a run can be audited
afterwards. The sample company, Fernwood Studio, and all seven enquiries are invented for
this demo. It runs with no API key at all, using a deterministic template writer, and
switches to a real model with one line in a config file.

## Run it

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app:app --reload
```

Open http://127.0.0.1:8000 and press "Run the agent".

## Tests

```bash
.venv/bin/python -m pytest tests -q
```

15 tests, no API key needed. They cover currency parsing, the scoring rubric, each
guardrail, and the three routes a lead can take through the agent.

## How the agent decides

| Outcome | When | What happens |
|---|---|---|
| Blocked | A guardrail returns `block`, for example sales spam or a blocklisted domain | No reply is drafted, no model is called, the row is written as blocked |
| Waiting for a person | Score at or above `APPROVAL_THRESHOLD`, or a guardrail returned `flag` | A reply is drafted but held. Nothing is sent until someone approves it |
| Answered automatically | Everything else | A short acknowledgement goes out and the row is written as replied |

Scoring is deterministic and lives in `agent/scoring.py`. Every point carries a written
reason, and the reasons always add up to the score, which one of the tests asserts.

Guardrails live in `agent/guardrails.py`. Each rule returns `block`, `flag` or nothing,
and a single `block` stops the run for that lead before the model is ever called.

## Swapping in your own workflow

`agent/tools.py` is the whole tool belt, one method per tool, each returning its result and
a one line summary for the log. `agent/runner.py` is the loop that calls them and records a
step for every call. To automate a different workflow, change those two files and leave the
log, the guardrails and the approval gate as they are.

## Backends

Set `AGENT_BACKEND` to `template` (default, no key, deterministic), `anthropic` (set
`ANTHROPIC_API_KEY`) or `claude_cli` (uses a local Claude CLI). If the chosen backend
fails, the agent falls back down the list rather than dropping the lead.
