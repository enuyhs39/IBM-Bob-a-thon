"""
main.py — Lab Finder FastAPI 백엔드 (v2)

구조:
  POST /api/search  — LITE: search_labs 직접 실행 → 구조화 JSON
  POST /api/match   — MATCH: search_labs + match_labs 직접 실행 → Top3 JSON + 에이전트 추천이유
  POST /api/email   — 이메일: email_helper_shh 에이전트 호출
"""
import os, sys, json
from typing import Optional, List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# tools 경로 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tools'))
from search_labs import search_labs as _search_labs
from match_labs import match_labs as _match_labs
from wxo_client import call_agent

load_dotenv()

app = FastAPI(title="Lab Finder API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

AGENT_EMAIL_HELPER = os.getenv("AGENT_EMAIL_HELPER", "email_helper_shh")
AGENT_MATCH       = os.getenv("AGENT_LAB_ADVISOR", "lab_advisor_agent")


# ── 요청 스키마 ───────────────────────────────────────────────

class SearchRequest(BaseModel):
    keywords: List[str]
    department: Optional[str] = None
    semester: Optional[str] = None
    major_type: Optional[str] = None

class MatchRequest(BaseModel):
    keywords: List[str]
    department: Optional[str] = None
    semester: Optional[str] = None
    major_type: Optional[str] = None
    purpose: Optional[str] = None
    activity_styles: Optional[List[str]] = None
    skills: Optional[List[str]] = None
    duration: Optional[str] = None
    weekly_hours: Optional[str] = None
    intro: Optional[str] = None
    thread_id: Optional[str] = None

class EmailRequest(BaseModel):
    professor_name: str
    professor_dept: str
    professor_keywords: List[str]
    student_dept: Optional[str] = None
    student_semester: Optional[str] = None
    raw_message: str
    thread_id: Optional[str] = None


# ── 헬퍼 ─────────────────────────────────────────────────────

def _lab_result_to_dict(r) -> dict:
    return {
        "professor_id": r.professor_id,
        "name": r.name,
        "department": r.department,
        "keywords": r.keywords,
        "matched_keywords": r.matched_keywords,
        "is_recruiting_undergrad": r.is_recruiting_undergrad,
        "is_recruiting_grad": r.is_recruiting_grad,
        "profile_url": r.profile_url,
        "view_count": r.view_count,
    }


# ── 엔드포인트 ────────────────────────────────────────────────

@app.get("/")
async def health():
    return {"status": "ok", "service": "Lab Finder API v2"}


@app.post("/api/search")
async def search(req: SearchRequest):
    """LITE 모드: 키워드 OR 검색 → 구조화 JSON 반환 (에이전트 없음)."""
    if not req.keywords:
        raise HTTPException(status_code=400, detail="키워드를 1개 이상 입력해주세요.")
    try:
        # @tool 데코레이터 함수는 로컬 직접 호출 시 반환값 자체를 반환 (.content 없음)
        result = _search_labs(keywords=req.keywords)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

    return {
        "mode": "lite",
        "keywords": req.keywords,
        "total": result.total,
        "labs": [_lab_result_to_dict(r) for r in result.results],
    }


@app.post("/api/match")
async def match(req: MatchRequest):
    """MATCH 모드: search_labs + match_labs 직접 실행 → Top3 + 에이전트 추천이유."""
    if not req.keywords:
        raise HTTPException(status_code=400, detail="키워드를 1개 이상 입력해주세요.")

    # 1) 오픈랩 검색
    try:
        search_result = _search_labs(keywords=req.keywords)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"연구실 검색 실패: {e}")

    if search_result.total == 0:
        raise HTTPException(status_code=404, detail="해당 키워드와 일치하는 연구실이 없습니다.")

    # 2) match_labs로 Top3 선정
    candidates = [_lab_result_to_dict(r) for r in search_result.results]
    try:
        match_result = _match_labs(
            student_keywords=req.keywords,
            lab_candidates=candidates,
            top_n=3,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"매칭 실패: {e}")

    top3 = match_result.top_labs

    # 3) 에이전트로 각 순위별 자연어 추천이유 생성
    student_info = []
    if req.department: student_info.append(f"학과: {req.department}")
    if req.semester:   student_info.append(f"학기: {req.semester}")
    if req.purpose:    student_info.append(f"목적: {req.purpose}")
    if req.activity_styles: student_info.append(f"선호 활동: {', '.join(req.activity_styles)}")
    if req.skills:     student_info.append(f"역량: {', '.join(req.skills)}")
    if req.intro:      student_info.append(f"자기소개: {req.intro}")
    student_info.append(f"관심 키워드: {', '.join(req.keywords)}")

    async def _get_reason(lab) -> str:
        prompt = (
            f"학생 정보:\n{chr(10).join(student_info)}\n\n"
            f"추천 연구실: {lab.professor_name} 교수 ({lab.department})\n"
            f"연구실 키워드: {', '.join(lab.matched_keywords)}\n"
            f"학부생 모집: {'모집 중' if lab.is_recruiting_undergrad else '마감'}\n\n"
            f"위 학생에게 이 연구실을 추천하는 이유를 2~3문장으로 자연스럽게 한국어로 작성해줘. "
            f"학생 상황과 연구실 특징을 연결해서 구체적으로 써줘."
        )
        try:
            agent_resp = await call_agent(AGENT_MATCH, prompt, req.thread_id)
            return agent_resp["text"].strip()
        except Exception:
            return f"관심 키워드 {len(lab.matched_keywords)}개 일치"

    import asyncio
    reasons = list(await asyncio.gather(*[_get_reason(lab) for lab in top3]))

    labs_out = []
    for i, lab in enumerate(top3):
        # 전체 candidates에서 매칭된 연구실의 profile_url 찾기
        prof_url = "#"
        for c in candidates:
            if c["name"] == lab.professor_name and c["department"] == lab.department:
                prof_url = c["profile_url"]
                break
        labs_out.append({
            "rank": i + 1,
            "name": lab.professor_name,
            "department": lab.department,
            "matched_keywords": lab.matched_keywords,
            "score": lab.score,
            "is_recruiting_undergrad": lab.is_recruiting_undergrad,
            "recommendation_reason": reasons[i],
            "profile_url": prof_url,
        })

    return {
        "mode": "match",
        "keywords": req.keywords,
        "total_candidates": search_result.total,
        "labs": labs_out,
    }


@app.post("/api/email")
async def write_email(req: EmailRequest):
    """이메일 작성: email_helper_shh 에이전트 호출. raw_message 비어있으면 기본 틀로 작성."""

    lines = [f"교수님: {req.professor_name} ({req.professor_dept})"]
    if req.professor_keywords:
        lines.append(f"연구 키워드: {', '.join(req.professor_keywords)}")
    if req.student_dept:
        lines.append(f"내 학과: {req.student_dept}")
    if req.student_semester:
        lines.append(f"내 학기: {req.student_semester}")
    lines.append(f"\n하고 싶은 말:\n{req.raw_message}")

    try:
        result = await call_agent(AGENT_EMAIL_HELPER, "\n".join(lines), req.thread_id)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

    return {"text": result["text"], "thread_id": result["thread_id"]}
