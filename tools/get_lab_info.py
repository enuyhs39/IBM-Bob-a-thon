import urllib.request
import json
import urllib.parse
from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission
from pydantic import BaseModel
from typing import Optional, List


class LabInfo(BaseModel):
    lab_id: str
    professor_name: str
    lab_name: str
    university: str
    department: str
    research_area: str
    keywords: List[str]
    profile_url: str


class GetLabInfoOutput(BaseModel):
    lab: LabInfo


@tool(permission=ToolPermission.READ_ONLY)
def get_lab_info(lab_id: str) -> GetLabInfoOutput:
    """rndcircle에서 특정 연구실의 기본 정보를 가져옵니다.
    교수명, 연구실명, 소속 학과, 연구 분야, 키워드를 반환합니다.

    Args:
        lab_id (str): rndcircle 연구실 UUID (예: "24efd518-2b62-4598-b7c8-c2f7a085c75e")
    Returns:
        GetLabInfoOutput: 연구실 기본 정보.
    """
    url = f"https://app.rndcircle.io/api/v2/labs/{lab_id}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Referer": "https://app.rndcircle.io/",
    }
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=10) as res:
        data = json.loads(res.read().decode("utf-8"))

    # /api/v2/labs/{id} 응답 구조에 맞게 파싱
    item = data.get("data") or data
    prof = item.get("professor") or item
    keywords = item.get("keywords") or []
    if isinstance(keywords, list) and keywords and isinstance(keywords[0], dict):
        keywords = [k.get("name", "") for k in keywords]

    return GetLabInfoOutput(
        lab=LabInfo(
            lab_id=lab_id,
            professor_name=prof.get("name") or item.get("professorName") or "",
            lab_name=item.get("labName") or item.get("name") or "",
            university=prof.get("university") or item.get("university") or "숙명여자대학교",
            department=prof.get("department") or item.get("department") or "",
            research_area=item.get("researchArea") or "",
            keywords=keywords,
            profile_url=f"https://app.rndcircle.io/lab/{lab_id}",
        )
    )
