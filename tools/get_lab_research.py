import urllib.request
import json
from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission
from pydantic import BaseModel
from typing import Optional, List


class ResearchTopic(BaseModel):
    title_ko: Optional[str]
    title_en: Optional[str]
    summary: Optional[str]
    core_content: Optional[str]


class GetLabResearchOutput(BaseModel):
    lab_id: str
    topics: List[ResearchTopic]


@tool(permission=ToolPermission.READ_ONLY)
def get_lab_research(lab_id: str) -> GetLabResearchOutput:
    """rndcircle에서 특정 연구실의 대표 연구 주제를 가져옵니다.
    연구 주제 제목(한/영)과 요약, 핵심 내용을 반환합니다.

    Args:
        lab_id (str): rndcircle 연구실 UUID (예: "24efd518-2b62-4598-b7c8-c2f7a085c75e")
    Returns:
        GetLabResearchOutput: 대표 연구 주제 목록.
    """
    url = f"https://app.rndcircle.io/api/v2/labs/{lab_id}/main-research"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Referer": "https://app.rndcircle.io/",
    }
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=10) as res:
        data = json.loads(res.read().decode("utf-8"))

    raw = data.get("data", [])
    topics = []
    for item in raw:
        if item.get("hidden"):
            continue
        topics.append(ResearchTopic(
            title_ko=item.get("titleKo") or None,
            title_en=item.get("titleEn") or None,
            summary=item.get("summary") or None,
            core_content=item.get("coreContent") or None,
        ))

    return GetLabResearchOutput(lab_id=lab_id, topics=topics)
