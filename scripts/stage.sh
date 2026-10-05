#!/usr/bin/env bash
# Brings up the three instances the capture script expects.
#   8122  the CRM after a full run, four leads still waiting
#   8123  an empty CRM, for the empty state
#   8124  a copy of 8122's database started with an unreachable team webhook,
#         so the failed step in the log is a real failure
set -e
cd "$(dirname "$0")/.."
for port in 8123 8124; do lsof -ti:$port | xargs kill 2>/dev/null || true; done
sleep 1
rm -f /tmp/sl_empty.db
cp data/crm.db /tmp/sl_full.db
env -u ANTHROPIC_API_KEY AGENT_DB=/tmp/sl_empty.db .venv/bin/python -m uvicorn app:app --port 8123 >/tmp/sl2.log 2>&1 &
env -u ANTHROPIC_API_KEY AGENT_DB=/tmp/sl_full.db TEAM_WEBHOOK=http://127.0.0.1:9/hook \
  .venv/bin/python -m uvicorn app:app --port 8124 >/tmp/sl3.log 2>&1 &
sleep 4
curl -s -X POST localhost:8124/run -o /dev/null
echo "8123 empty, 8124 staged with a dead webhook"
