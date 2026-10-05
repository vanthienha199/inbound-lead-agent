# Inbound lead agent, with a run log, guardrails and a human approval gate

An AI agent that works an inbound lead inbox end to end: it reads new form submissions,
enriches each company, scores the lead against a written rubric, runs guardrails, drafts a
reply, and then stops and waits for a person before anything is sent. Every tool call is
recorded with its arguments, its result and how long it took, so a run can be audited
afterwards. The sample company, Studio Lind, and all seven enquiries are invented for
this demo. It runs with no API key at all, using a deterministic template writer, and
switches to a real model with one line in a config file.

## Run it

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app:app --reload
```

Open http://127.0.0.1:8000 and press "Run the agent". The lead list is the home page.
Click any row to open the drawer, which holds the drafted reply, the points behind the
score, the guardrail findings and every tool call the agent made for that lead.

## Tests

```bash
.venv/bin/python -m pytest tests -q
```

18 tests, no API key needed. They cover currency parsing, the scoring rubric, each
guardrail, the three routes a lead can take through the agent, the working each row keeps,
and a dead team webhook, which has to be logged as a failed step without costing the
operator the run summary.

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

## The team webhook

Set `TEAM_WEBHOOK` to post the one line run summary to a channel. When it is not set
nothing is posted and the log says so. When it is set and the endpoint is down, the step
is recorded as failed and the summary is still computed locally, so a broken channel never
costs the operator the one line that says what happened.

## Gallery captures

`scripts/stage.sh` brings up the two extra instances the screenshots need, one with an
empty database and one with a dead team webhook, and `scripts/capture.mjs` takes every
image from the running app. Both need puppeteer: run `npm i puppeteer` here, or point
`PUPPETEER_FROM` at the `package.json` of a project that has it.

## Backends

Set `AGENT_BACKEND` to `template` (default, no key, deterministic), `anthropic` (set
`ANTHROPIC_API_KEY`) or `claude_cli` (uses a local Claude CLI). If the chosen backend
fails, the agent falls back down the list rather than dropping the lead.
