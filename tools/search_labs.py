import urllib.request
import json
from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission
from pydantic import BaseModel
from typing import Optional, List

UNIVERSITY_ID = 47  # 숙명여자대학교


class LabResult(BaseModel):
    professor_id: int
    name: str
    university: str
    department: str
    email: Optional[str]
    keywords: List[str]
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
    # 전체 페이지 수집 (최대 500명 한도)
    all_items: List[dict] = []
    page = 0
    while True:
        data = _fetch_open_labs(page=page, size=100)
        payload = data.get("payload", {})
        content = payload.get("content", [])
        all_items.extend(content)
        if payload.get("last", True) or page >= 4:
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

        score = _keyword_match_score(prof_keywords, keywords)
        if score == 0 and len(keywords) > 1:
            continue  # Match 모드에서 무관한 연구실 제외

        results.append(LabResult(
            professor_id=prof.get("id", 0),
            name=prof.get("name", ""),
            university=prof.get("university", "숙명여자대학교"),
            department=prof.get("department", ""),
            email=None,
            keywords=prof_keywords,
            is_recruiting_undergrad=is_undergrad,
            is_recruiting_grad=is_grad,
            view_count=item.get("viewCount", 0),
            profile_url=f"https://phdkim.net/professor/{prof.get('id', 0)}/info",
        ))

    # 정렬
    if len(keywords) == 1:
        # Lite 모드: 학부 모집 우선 → 조회수순
        mode = "lite"
        results.sort(key=lambda r: (not r.is_recruiting_undergrad, -r.view_count))
    else:
        # Match 모드: 키워드 점수 → 학부 모집 → 조회수
        mode = "match"
        scored = []
        for r in results:
            sc = _keyword_match_score(r.keywords, keywords)
            scored.append((sc, r))
        scored.sort(key=lambda x: (-x[0], not x[1].is_recruiting_undergrad, -x[1].view_count))
        results = [r for _, r in scored[:10]]

    return SearchLabsOutput(total=len(results), results=results, mode=mode)
