from typing import Optional
from pydantic import BaseModel
from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission


class MatchedLab(BaseModel):
    rank: int
    professor_name: str
    department: str
    email: str
    matched_keywords: list[str]
    score: int
    is_recruiting_undergrad: bool
    recommendation_reason: str


class MatchResult(BaseModel):
    top_labs: list[MatchedLab]
    student_keywords: list[str]
    total_candidates: int


MatchResult.model_rebuild()


@tool(permission=ToolPermission.READ_ONLY)
def match_labs(
    student_keywords: list[str],
    lab_candidates: list[dict],
    top_n: Optional[int] = 3,
) -> MatchResult:
    """Score and rank lab candidates by keyword overlap with student interests, with recommendation reasons.

    This tool receives a list of lab candidates (from search_open_labs) and
    the student's interest keywords, then returns the top-N best matching labs
    ranked by score with a human-readable recommendation reason.

    Args:
        student_keywords (list[str]): Keywords representing the student's research interests (e.g. ["AI", "NLP", "로봇"]).
        lab_candidates (list[dict]): List of lab dicts returned by search_open_labs. Each dict must have keys: name, department, email, keywords, is_recruiting_undergrad, view_count.
        top_n (Optional[int]): Number of top results to return. Defaults to 3.
    Returns:
        MatchResult: Ranked list of best-matching labs with scores, matched keywords, and recommendation reasons.
    """
    if top_n is None:
        top_n = 3

    student_kw_lower = [kw.lower() for kw in student_keywords]
    total_kw = len(student_keywords)

    scored = []
    for item in lab_candidates:
        name = item.get("name", "")
        department = item.get("department", "")
        email = item.get("email", "")
        keywords = item.get("keywords", [])
        is_recruiting = item.get("is_recruiting_undergrad", False)
        view_count = item.get("view_count", 0)

        lab_kw_lower = [kw.lower() for kw in keywords]

        matched = [
            orig_kw
            for orig_kw, lc_kw in zip(keywords, lab_kw_lower)
            if any(lc_kw in s_kw or s_kw in lc_kw for s_kw in student_kw_lower)
        ]

        score = len(matched) * 10
        if is_recruiting:
            score += 5
        score += min(view_count // 100, 5)

        scored.append((score, matched, name, department, email, is_recruiting, len(keywords)))

    scored.sort(key=lambda x: x[0], reverse=True)

    top_labs = []
    for i, (score, matched, name, department, email, is_recruiting, lab_total_kw) in enumerate(scored[:top_n]):
        # 추천 이유 문구 생성
        reasons = []
        if matched:
            reasons.append(f"관심 키워드 {len(matched)}/{total_kw}개 일치 ({', '.join(matched)})")
        if is_recruiting:
            reasons.append("학부생 인턴 모집 중")
        if not reasons:
            reasons.append("관련 연구 분야 보유")

        recommendation_reason = " · ".join(reasons)

        top_labs.append(
            MatchedLab(
                rank=i + 1,
                professor_name=name,
                department=department,
                email=email,
                matched_keywords=matched,
                score=score,
                is_recruiting_undergrad=is_recruiting,
                recommendation_reason=recommendation_reason,
            )
        )

    return MatchResult(
        top_labs=top_labs,
        student_keywords=student_keywords,
        total_candidates=len(lab_candidates),
    )
