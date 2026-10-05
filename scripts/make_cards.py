"""Renders the two text artefacts the gallery uses, the test run and the exported
run log, from real output rather than a mockup."""

import html
import json
import re
import subprocess
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP = ("rootdir:", "cachedir:", "platform ", "plugins:", "collecting ")

HEAD = """<!doctype html><html><head><meta charset="utf-8">
<link href="https://api.fontshare.com/v2/css?f[]=zodiak@700&display=swap" rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family=Hanken+Grotesk:wght@400;500;600&family=Roboto+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
 body{margin:0;background:#F4F1EA;font-family:"Roboto Mono",monospace}
 .card{width:%dpx;margin:28px;background:#fff;border:1px solid #E3DED2;padding:28px 32px}
 h3{font-family:"Zodiak",Georgia,serif;font-weight:700;font-size:21px;margin:0 0 6px;color:#1A1A18}
 .sub{font-family:"Hanken Grotesk",sans-serif;font-size:14px;color:#5C584F;margin:0 0 20px}
 div.line{font-size:13px;line-height:1.75;color:#5C584F;white-space:pre}
 div.pass{color:#1A1A18}
 div.sum{color:#1E5A46;font-weight:500;margin-top:12px;border-top:1px solid #EDE9E0;padding-top:12px}
</style></head><body>"""


def card(width, title, subtitle, rows, out):
    body = HEAD % width + f'<div class="card"><h3>{title}</h3><p class="sub">{subtitle}</p>' + "".join(rows) + "</div></body></html>"
    (ROOT / "scripts" / out).write_text(body, encoding="utf-8")


result = subprocess.run(
    [str(ROOT / ".venv/bin/python"), "-m", "pytest", "tests", "-v", "--no-header", "-p", "no:cacheprovider"],
    cwd=ROOT, capture_output=True, text=True,
)
lines = [l.rstrip() for l in result.stdout.splitlines() if l.strip() and not l.startswith(SKIP)]
lines = [re.sub(r"=+", lambda m: "=" * min(len(m.group(0)), 18), l) for l in lines]
rows = []
for line in lines:
    kind = "pass" if "PASSED" in line else "line"
    if "passed" in line and "=" in line:
        kind = "sum"
    rows.append(f'<div class="line {kind}">{html.escape(line)}</div>')
card(1020, "pytest", "No API key needed, the reply writer falls back to a template", rows, "tests.html")

log = json.loads(urllib.request.urlopen("http://127.0.0.1:8122/api/run.json", timeout=10).read())
cut = {"started": log["started"], "summary": log["summary"], "steps": log["steps"][1:4]}
text = json.dumps(cut, indent=2)
rows = [f'<div class="line pass">{html.escape(l)}</div>' for l in text.splitlines()[:13]]
rows.append(f'<div class="line">    ... {len(log["steps"]) - 1} more steps</div>')
card(1180, "run-log.json", f"The whole run, {len(log['steps'])} tool calls, downloaded from the activity page", rows, "log.html")
print("cards written")
