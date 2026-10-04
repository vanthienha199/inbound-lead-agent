"""Fernwood Studio inbound lead agent. Sample project, invented company.

Run:  uvicorn app:app --reload
"""

import os
import pathlib
from datetime import datetime, timezone

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from agent.runner import APPROVAL_THRESHOLD, run_once
from agent.store import Crm
from agent.tools import SCHEMA

BASE = pathlib.Path(__file__).resolve().parent
app = FastAPI(title="Fernwood inbound lead agent (sample)")
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")
templates = Jinja2Templates(directory=BASE / "templates")

crm = Crm(os.environ.get("AGENT_DB", BASE / "data" / "crm.db"))
LAST_RUN = {"run": None}


def ctx(request, page, **kw):
    rows = crm.all()
    return {
        "request": request, "page": page, "rows": rows,
        "waiting": [r for r in rows if r["status"] == "awaiting approval"],
        "threshold": APPROVAL_THRESHOLD, "run": LAST_RUN["run"], **kw,
    }


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(request, "run.html", ctx(request, "run"))


@app.post("/run")
def do_run():
    LAST_RUN["run"] = run_once(crm).as_dict()
    return RedirectResponse("/", status_code=303)


@app.post("/reset")
def reset():
    crm.reset()
    LAST_RUN["run"] = None
    return RedirectResponse("/", status_code=303)


@app.get("/approvals", response_class=HTMLResponse)
def approvals(request: Request):
    return templates.TemplateResponse(request, "approvals.html", ctx(request, "approvals"))


@app.post("/approvals/{lead_id}")
def decide(lead_id: str, action: str = Form(...)):
    status = "reply sent" if action == "approve" else "declined"
    crm.set_decision(lead_id, status, "ha@fernwood.example",
                     datetime.now(timezone.utc).isoformat(timespec="seconds"))
    return RedirectResponse("/approvals", status_code=303)


@app.get("/crm", response_class=HTMLResponse)
def crm_page(request: Request):
    return templates.TemplateResponse(request, "crm.html", ctx(request, "crm"))


@app.get("/tools", response_class=HTMLResponse)
def tools_page(request: Request):
    return templates.TemplateResponse(request, "tools.html", ctx(request, "tools", schema=SCHEMA))


@app.get("/api/run")
def api_run():
    return JSONResponse(LAST_RUN["run"] or {"steps": [], "summary": "No run yet"})


@app.get("/healthz")
def healthz():
    return {"status": "ok", "rows": len(crm.all()), "threshold": APPROVAL_THRESHOLD}
