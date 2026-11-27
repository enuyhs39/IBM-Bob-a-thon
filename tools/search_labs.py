import urllib.request
import json
from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission
from pydantic import BaseModel
from typing import Optional, List

UNIVERSITY_ID = 47  # 숙명여자대학교

# 학생 선택 키워드 → 김박사넷 연구실 키워드 유사어 확장
# 프론트 태그에 없는 세부 용어들을 묶어줌
KEYWORD_EXPAND: dict = {
    "ai":           ["ai", "agentic ai", "ai modeling", "ai user experience", "generative ai",
                     "human-ai interaction", "human-centered ai", "responsible ai",
                     "intelligent user interfaces", "3d ai", "ai 프로젝트"],
    "머신러닝":      ["머신러닝", "deep learning", "diffusion", "gan", "multi-modal processing"],
    "데이터과학":    ["데이터과학", "big data", "data mining", "database", "통계분석"],
    "소프트웨어":    ["소프트웨어", "computer graphics", "computer vision", "3d content",
                     "3d generation", "3d vision", "vision graphics", "video generation",
                     "accessible computing"],
    "약학·신약개발": ["약학·신약개발", "nafld", "자동화 파이프라인 구축", "화장품소재"],
    "화학·생명과학": ["화학·생명과학", "이상지질", "의료기기화"],
    "환경·생태":     ["환경·생태"],
    "경영·마케팅":   ["경영·마케팅", "personalization", "광고"],
    "경제·금융":     ["경제·금융", "금융"],
    "법학·정책":     ["법학·정책"],
    "미디어·pr":     ["미디어·pr", "미디어"],
    "심리·상담":     ["심리·상담", "인간공학 adas 개발", "인간공학", "인간공학 및 ux 연구"],
    "아동·가족":     ["아동·가족"],
    "디자인·시각예술":["디자인·시각예술", "adas 개발", "화장품 소재"],
    "역사·문화":     ["역사·문화"],
    "언어·문학":     ["언어·문학", "언어처리", "대화학습"],
    "교육학":        ["교육학"],
    "통계·수학":     ["통계·수학", "통계분석"],
}


class LabResult(BaseModel):
    professor_id: int
    name: str
    university: str
    department: str
    email: Optional[str]
    keywords: List[str]
    matched_keywords: List[str]  # 학생 키워드와 실제 일치한 것들
    is_recruiting_undergrad: bool
    is_recruiting_grad: bool
    view_count: int
    profile_url: str


class SearchLabsOutput(BaseModel):
    total: int
    results: List[LabResult]
    mode: str


def _fetch_open_labs(page: int = 0, size: int = 100) -> dict:
    """김박사넷 오픈랩 API 호출."""
    url = (
        f"https://phdkim.net/api/professor/open-lab"
        f"?university={UNIVERSITY_ID}&page={page}&size={size}"
    )
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=10) as res:
        return json.loads(res.read().decode("utf-8"))


def _keyword_match_score(prof_keywords: List[str], student_keywords: List[str]) -> int:
    """교수 키워드와 학생 키워드의 일치 점수 계산."""
    prof_lower = {k.lower() for k in prof_keywords}
    score = 0
    for sk in student_keywords:
        sk_lower = sk.lower()
        if sk_lower in prof_lower:
            score += 3
            continue
        for pk in prof_lower:
            if sk_lower in pk or pk in sk_lower:
                score += 1
                break
    return score


@tool(permission=ToolPermission.READ_ONLY)
def search_labs(
    keywords: List[str],
    recruit_undergrad_only: bool = False,
) -> SearchLabsOutput:
    """숙명여자대학교 교수 연구실을 키워드로 검색합니다.
    키워드가 1개이면 Lite 모드(전체 목록), 2개 이상이면 Match 모드(Top 10 정렬)로 동작합니다.

    Args:
        keywords (List[str]): 학생의 관심 연구 키워드 목록. 예: ["AI", "머신러닝"]. 최소 1개 필수.
        recruit_undergrad_only (bool): True이면 학부생 인턴 모집 중인 연구실만 반환합니다.
    Returns:
        SearchLabsOutput: 검색 결과 (total, results 목록, mode).
    """
    # 키워드 유사어 확장
    expanded_keywords: List[str] = []
    for kw in keywords:
        kw_lower = kw.lower()
        expanded_keywords.append(kw_lower)
        for base, aliases in KEYWORD_EXPAND.items():
            if kw_lower == base or kw_lower in aliases:
                expanded_keywords.extend(aliases)
                break
    # 중복 제거
    expanded_keywords = list(dict.fromkeys(expanded_keywords))

    # 전체 페이지 수집 (last 플래그 기준, 제한 없음)
    all_items: List[dict] = []
    page = 0
    while True:
        data = _fetch_open_labs(page=page, size=100)
        payload = data.get("payload", {})
        content = payload.get("content", [])
        all_items.extend(content)
        if payload.get("last", True):
            break
        page += 1

    # 숙명여대만 필터 + professor_id 기준 중복 제거
    seen_ids: set = set()
    sookmyung_items = []
    for item in all_items:
        pid = item.get("professor", {}).get("id")
        if item.get("professor", {}).get("university") == "숙명여자대학교" and pid not in seen_ids:
            seen_ids.add(pid)
            sookmyung_items.append(item)

    results: List[LabResult] = []
    for item in sookmyung_items:
        prof = item.get("professor", {})
        prof_keywords: List[str] = item.get("keywords", [])
        recruiting = item.get("recruiting", {})

        is_undergrad = recruiting.get("isRecruitingUndergraduateIntern", False)
        is_grad = recruiting.get("isRecruitingGradStudent", False)

        if recruit_undergrad_only and not is_undergrad:
            continue

        # 확장된 키워드로 매칭
        score = _keyword_match_score(prof_keywords, expanded_keywords)
        if score == 0:
            continue

        # 실제로 일치한 키워드 목록 계산 (원본 student keywords 기준으로 표시)
        prof_lower = {k.lower(): k for k in prof_keywords}
        matched: List[str] = []
        for sk in expanded_keywords:
            sk_lower = sk.lower()
            for pk_lower, pk_orig in prof_lower.items():
                if sk_lower in pk_lower or pk_lower in sk_lower:
                    if pk_orig not in matched:
                        matched.append(pk_orig)

        results.append(LabResult(
            professor_id=prof.get("id", 0),
            name=prof.get("name", ""),
            university=prof.get("university", "숙명여자대학교"),
            department=prof.get("department", ""),
            email=None,
            keywords=prof_keywords,
            matched_keywords=matched,
            is_recruiting_undergrad=is_undergrad,
            is_recruiting_grad=is_grad,
            view_count=item.get("viewCount", 0),
            profile_url=f"https://phdkim.net/professor/{prof.get('id', 0)}/info",
        ))

    # 항상 Lite 모드 — 키워드 점수 → 학부 모집 → 조회수순 정렬
    mode = "lite"
    scored = []
    for r in results:
        sc = _keyword_match_score(r.keywords, expanded_keywords)
        scored.append((sc, r))
    scored.sort(key=lambda x: (-x[0], not x[1].is_recruiting_undergrad, -x[1].view_count))
    results = [r for _, r in scored]

    return SearchLabsOutput(total=len(results), results=results, mode=mode)
