import urllib.request
import json
from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission
from pydantic import BaseModel
from typing import Optional, List


class Paper(BaseModel):
    title: str
    published_date: Optional[str]
    authors: List[str]
    abstract: Optional[str]
    keywords: List[str]


class GetLabPapersOutput(BaseModel):
    lab_id: str
    total: int
    papers: List[Paper]


@tool(permission=ToolPermission.READ_ONLY)
def get_lab_papers(lab_id: str, limit: int = 5) -> GetLabPapersOutput:
    """rndcircle에서 특정 연구실의 최근 논문 목록을 가져옵니다.
    각 논문의 제목, 저자, 출판일, abstract, 키워드를 반환합니다.

    Args:
        lab_id (str): rndcircle 연구실 UUID (예: "24efd518-2b62-4598-b7c8-c2f7a085c75e")
        limit (int): 가져올 논문 수. 기본값 5, 최대 10.
    Returns:
        GetLabPapersOutput: 논문 목록 (total, papers).
    """
    limit = min(limit, 10)
    url = f"https://app.rndcircle.io/api/v2/labs/{lab_id}/papers"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Referer": "https://app.rndcircle.io/",
    }
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=10) as res:
        data = json.loads(res.read().decode("utf-8"))

    raw_papers = data.get("data", [])
    total = data.get("meta", {}).get("total", len(raw_papers))

    papers = []
    for p in raw_papers[:limit]:
        papers.append(Paper(
            title=p.get("title") or "",
            published_date=p.get("publishedDate") or p.get("publishedYear"),
            authors=p.get("authors") or [],
            abstract=p.get("abstract") or None,
            keywords=p.get("keywords") or [],
        ))

    return GetLabPapersOutput(lab_id=lab_id, total=total, papers=papers)
