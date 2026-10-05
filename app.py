"""Studio Lind inbound lead agent. Sample project, invented company.

Run:  uvicorn app:app --reload
"""

import json
import os
import pathlib
from datetime import datetime, timezone

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from agent.runner import APPROVAL_THRESHOLD, run_once
from agent.store import Crm
from agent.tools import SCHEMA

BASE = pathlib.Path(__file__).resolve().parent
app = FastAPI(title="Studio Lind inbound lead agent (sample)")
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")
templates = Jinja2Templates(directory=BASE / "templates")


def duration(ms):
    """Tool calls range from a fraction of a millisecond to half a minute, so the
    slow ones read in seconds rather than as a five digit number."""
    return f"{ms / 1000:.1f} s" if ms >= 1000 else f"{ms:.1f} ms"


def clock(stamp):
    return f"{stamp[11:16]} UTC on {stamp[8:10]} {stamp[5:7]}" if len(stamp) > 15 else stamp


templates.env.filters["duration"] = duration

crm = Crm(os.environ.get("AGENT_DB", BASE / "data" / "crm.db"))
LAST_RUN = {"run": None}

STATUS_LABEL = {
    "awaiting approval": "Waiting for you",
    "reply sent": "Sent",
    "declined": "Declined",
    "replied automatically": "Replied automatically",
    "blocked": "Blocked",
}


def unpack(row):
    """Rows carry the agent's own working as JSON, so the drawer never has to
    re-run anything to explain a decision."""
    row = dict(row)
    for key in ("reasons", "findings", "trail"):
        try:
            row[key] = json.loads(row.get(key) or "[]")
        except (TypeError, ValueError):
            row[key] = []
    row["label"] = STATUS_LABEL.get(row["status"], row["status"])
    if row["status"] == "reply sent" and row.get("decided_at"):
        row["label"] = "Sent " + row["decided_at"][11:16]
    return row


def ctx(request, page, **kw):
    rows = [unpack(r) for r in crm.all()]
    return {
        "request": request,
        "page": page,
        "rows": rows,
        "waiting": [r for r in rows if r["status"] == "awaiting approval"],
        "threshold": APPROVAL_THRESHOLD,
        "run": LAST_RUN["run"],
        **kw,
    }


@app.get("/", response_class=HTMLResponse)
def leads(request: Request, lead: str | None = None):
    data = ctx(request, "leads")
    data["open_lead"] = next((r for r in data["rows"] if r["id"] == lead), None)
    return templates.TemplateResponse(request, "leads.html", data)


@app.post("/run")
def do_run():
    LAST_RUN["run"] = run_once(crm).as_dict()
    return RedirectResponse("/", status_code=303)


@app.post("/reset")
def reset():
    crm.reset()
    LAST_RUN["run"] = None
    return RedirectResponse("/", status_code=303)


@app.post("/decide/{lead_id}")
async def decide(request: Request, lead_id: str, action: str = Form(...)):
    status = "reply sent" if action == "approve" else "declined"
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    crm.set_decision(lead_id, status, "ha@studiolind.example", now)
    row = unpack(crm.get(lead_id))
    if "application/json" in (request.headers.get("accept") or ""):
        return JSONResponse({"id": lead_id, "status": status, "label": row["label"]})
    return RedirectResponse(f"/?lead={lead_id}", status_code=303)


@app.get("/activity", response_class=HTMLResponse)
def activity(request: Request):
    return templates.TemplateResponse(request, "activity.html", ctx(request, "activity"))


@app.get("/tools", response_class=HTMLResponse)
def tools_page(request: Request):
    return templates.TemplateResponse(request, "tools.html", ctx(request, "tools", schema=SCHEMA))


@app.get("/api/run")
def api_run():
    return JSONResponse(LAST_RUN["run"] or {"steps": [], "summary": "No run yet"})


@app.get("/api/run.json")
def download_run():
    body = json.dumps(LAST_RUN["run"] or {"steps": [], "summary": "No run yet"}, indent=2)
    return Response(
        body,
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="run-log.json"'},
    )


@app.get("/healthz")
def healthz():
    return {"status": "ok", "rows": len(crm.all()), "threshold": APPROVAL_THRESHOLD}
