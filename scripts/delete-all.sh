#!/bin/bash
# delete-all.sh — 역순으로 삭제
source venv/bin/activate

orchestrate agents remove -n lab_matching_agent --kind native || true
orchestrate agents remove -n email_helper_shh --kind native || true
orchestrate tools remove -n search_labs || true
orchestrate tools remove -n get_today_date || true

echo "=== All removed ==="
