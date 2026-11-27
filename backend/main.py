"""
main.py — Lab Finder FastAPI 백엔드

엔드포인트:
  POST /api/search  — LITE 모드: 키워드 → 연구실 목록
  POST /api/match   — MATCH 모드: 키워드 + 추가정보 → Top 3 추천
  POST /api/email   — 이메일 작성: 대충 쓴 내용 → 완성 메일
"""
import os
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from wxo_client import call_agent

load_dotenv()

app = FastAPI(title="Lab Finder API", version="1.0.0")

# CORS — 프론트엔드(로컬 파일 / localhost)에서 호출 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

AGENT_LAB_ADVISOR  = os.getenv("AGENT_LAB_ADVISOR",  "lab_advisor_agent")
AGENT_EMAIL_HELPER = os.getenv("AGENT_EMAIL_HELPER",  "email_helper_shh")


# ── 요청/응답 스키마 ────────────────────────────────────────

class SearchRequest(BaseModel):
    keywords: list[str]                     # 필수 키워드 (1개 이상)
    department: Optional[str] = None        # 학과
    semester: Optional[str] = None          # 학기
    major_type: Optional[str] = None        # 전공 현황
    thread_id: Optional[str] = None


class MatchRequest(BaseModel):
    keywords: list[str]
    department: Optional[str] = None
    semester: Optional[str] = None
    major_type: Optional[str] = None
    # 선택 정보
    purpose: Optional[str] = None           # 연구 참여 목적
    activity_styles: Optional[list[str]] = None   # 선호 활동 방식
    skills: Optional[list[str]] = None      # 보유 역량
    duration: Optional[str] = None          # 희망 기간
    weekly_hours: Optional[str] = None      # 주당 시간
    intro: Optional[str] = None             # 한 줄 자기소개
    thread_id: Optional[str] = None


class EmailRequest(BaseModel):
    professor_name: str                     # 교수명
    professor_dept: str                     # 소속 학과
    professor_keywords: list[str]           # 연구 키워드
    student_dept: Optional[str] = None      # 학생 학과
    student_semester: Optional[str] = None  # 학기
    raw_message: str                        # 대충 쓴 내용
    thread_id: Optional[str] = None


class AgentResponse(BaseModel):
    text: str
    thread_id: str


# ── 헬퍼: 학생 정보 → 자연어 메시지 변환 ───────────────────

def _build_search_message(req: SearchRequest) -> str:
    parts = []
    if req.department:
        parts.append(f"학과: {req.department}")
    if req.semester:
        parts.append(f"학기: {req.semester}")
    if req.major_type:
        parts.append(f"전공 현황: {req.major_type}")
    parts.append(f"관심 키워드: {', '.join(req.keywords)}")
    return "\n".join(parts)


def _build_match_message(req: MatchRequest) -> str:
    parts = []
    if req.department:
        parts.append(f"학과: {req.department}")
    if req.semester:
        parts.append(f"학기: {req.semester}")
    if req.major_type:
        parts.append(f"전공 현황: {req.major_type}")
    parts.append(f"관심 키워드: {', '.join(req.keywords)}")
    if req.purpose:
        parts.append(f"연구 참여 목적: {req.purpose}")
    if req.activity_styles:
        parts.append(f"선호 활동 방식: {', '.join(req.activity_styles)}")
    if req.skills:
        parts.append(f"보유 역량: {', '.join(req.skills)}")
    if req.duration:
        parts.append(f"희망 참여 기간: {req.duration}")
    if req.weekly_hours:
        parts.append(f"주당 투자 가능 시간: {req.weekly_hours}")
    if req.intro:
        parts.append(f"자기소개: {req.intro}")
    return "\n".join(parts)


def _build_email_message(req: EmailRequest) -> str:
    lines = [
        f"교수님: {req.professor_name} ({req.professor_dept})",
        f"연구 키워드: {', '.join(req.professor_keywords)}",
    ]
    if req.student_dept:
        lines.append(f"내 학과: {req.student_dept}")
    if req.student_semester:
        lines.append(f"내 학기: {req.student_semester}")
    lines.append(f"\n하고 싶은 말:\n{req.raw_message}")
    return "\n".join(lines)


# ── 엔드포인트 ──────────────────────────────────────────────

@app.get("/")
async def health():
    return {"status": "ok", "service": "Lab Finder API"}


@app.post("/api/search", response_model=AgentResponse)
async def search_labs(req: SearchRequest):
    """LITE 모드: 키워드 관련 연구실 전체 목록 반환."""
    if not req.keywords:
        raise HTTPException(status_code=400, detail="키워드를 1개 이상 입력해주세요.")

    message = _build_search_message(req)
    try:
        result = await call_agent(AGENT_LAB_ADVISOR, message, req.thread_id)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

    return AgentResponse(**result)


@app.post("/api/match", response_model=AgentResponse)
async def match_labs(req: MatchRequest):
    """MATCH 모드: 추가 정보 기반 Top 3 맞춤 추천."""
    if not req.keywords:
        raise HTTPException(status_code=400, detail="키워드를 1개 이상 입력해주세요.")

    has_optional = any([
        req.purpose, req.activity_styles, req.skills,
        req.duration, req.weekly_hours, req.intro,
    ])
    if not has_optional:
        raise HTTPException(
            status_code=400,
            detail="MATCH 모드는 선택 정보를 1개 이상 입력해야 합니다. /api/search를 사용하세요."
        )

    message = _build_match_message(req)
    try:
        result = await call_agent(AGENT_LAB_ADVISOR, message, req.thread_id)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

    return AgentResponse(**result)


@app.post("/api/email", response_model=AgentResponse)
async def write_email(req: EmailRequest):
    """이메일 작성: 대충 쓴 내용 → 정중한 컨택 메일 완성."""
    if not req.raw_message.strip():
        raise HTTPException(status_code=400, detail="하고 싶은 말을 입력해주세요.")

    message = _build_email_message(req)
    try:
        result = await call_agent(AGENT_EMAIL_HELPER, message, req.thread_id)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

    return AgentResponse(**result)
