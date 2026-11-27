"""
wxo_client.py — IBM wxO Runtime API 호출 클라이언트

wxO /v1/orchestrate/runs 엔드포인트로 에이전트를 호출하고
응답 텍스트를 반환합니다.
"""
import os
import httpx
from dotenv import load_dotenv

load_dotenv()

WXO_BASE_URL = os.getenv("WXO_BASE_URL", "").rstrip("/")
IBM_API_KEY  = os.getenv("IBM_API_KEY", "")

IAM_TOKEN_URL = "https://iam.cloud.ibm.com/identity/token"

_cached_token: dict = {"token": None, "expires_at": 0}


async def _get_iam_token() -> str:
    """IBM Cloud IAM 토큰 발급 (캐시 적용)."""
    import time
    if _cached_token["token"] and time.time() < _cached_token["expires_at"] - 60:
        return _cached_token["token"]

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            IAM_TOKEN_URL,
            data={
                "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
                "apikey": IBM_API_KEY,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

    import time
    _cached_token["token"] = data["access_token"]
    _cached_token["expires_at"] = time.time() + data.get("expires_in", 3600)
    return _cached_token["token"]


async def call_agent(
    agent_name: str,
    message: str,
    thread_id: str | None = None,
) -> dict:
    """
    wxO 에이전트를 호출하고 응답을 반환합니다.

    Returns:
        {
            "text": str,          # 에이전트 응답 텍스트
            "thread_id": str,     # 멀티턴용 스레드 ID
        }
    """
    token = await _get_iam_token()

    # 에이전트 ID 조회
    agent_id = await _get_agent_id(agent_name, token)

    payload: dict = {
        "input": {"text": message},
    }
    if thread_id:
        payload["session_id"] = thread_id

    url = f"{WXO_BASE_URL}/v1/orchestrate/runs"

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            url,
            json={"agent_id": agent_id, **payload},
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
        )
        resp.raise_for_status()
        data = resp.json()

    # 응답 파싱 — /runs 응답 구조: data.message.content[0].text
    try:
        text = data["result"]["data"]["message"]["content"][0]["text"]
    except (KeyError, IndexError, TypeError):
        text = str(data)

    return {
        "text": text,
        "thread_id": data.get("result", {}).get("session_id") or thread_id or "",
    }


# 에이전트 이름 → ID 캐시
_agent_id_cache: dict[str, str] = {}


async def _get_agent_id(agent_name: str, token: str) -> str:
    """에이전트 이름으로 agent_id 조회 (캐시 적용)."""
    if agent_name in _agent_id_cache:
        return _agent_id_cache[agent_name]

    url = f"{WXO_BASE_URL}/v1/orchestrate/agents"
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            url,
            headers={"Authorization": f"Bearer {token}"},
        )
        resp.raise_for_status()
        agents = resp.json().get("resources", [])

    for agent in agents:
        if agent.get("name") == agent_name:
            _agent_id_cache[agent_name] = agent["id"]
            return agent["id"]

    raise ValueError(f"Agent '{agent_name}' not found in wxO")
