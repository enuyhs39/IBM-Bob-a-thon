#!/bin/bash
# import-all.sh — 의존성 순서대로 임포트
set -e

source venv/bin/activate

echo "=== [1/3] tools 임포트 ==="
orchestrate tools import -k python -f tools/get_today_date.py
orchestrate tools import -k python -f tools/search_labs.py
orchestrate tools import -k python -f tools/match_labs.py

echo "=== [2/3] agents 임포트 (collaborator 먼저) ==="
orchestrate agents import -f agents/email_helper_shh.yaml
orchestrate agents import -f agents/lab_matching_agent.yaml

echo "=== [3/3] 오케스트레이터 임포트 ==="
orchestrate agents import -f agents/lab_advisor_agent.yaml

echo "=== Done! ==="
orchestrate agents list
