"""
wxo_client.py — IBM wxO Runtime API 호출 클라이언트

wxO /v1/orchestrate/runs 엔드포인트로 에이전트를 호출하고
응답 텍스트를 반환합니다.
"""
import os
import asyncio
import httpx
from dotenv import load_dotenv

load_dotenv()

WXO_BASE_URL = (os.getenv("WXO_BASE_URL") or "https://api.jp-tok.watson-orchestrate.cloud.ibm.com/instances/89dcdbf5-e4da-477f-96f3-bab18d67b781").rstrip("/")
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
        "agent_id": agent_id,
        "message": {"role": "user", "content": message},
    }
    if thread_id:
        payload["thread_id"] = thread_id

    url = f"{WXO_BASE_URL}/v1/orchestrate/runs"

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            url,
            json=payload,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
        )
        resp.raise_for_status()
        run_data = resp.json()

    new_thread_id = run_data.get("thread_id", thread_id or "")
    run_id        = run_data.get("run_id", "")

    # 비동기 응답 폴링 — /v1/orchestrate/runs/{run_id}
    poll_url = f"{WXO_BASE_URL}/v1/orchestrate/runs/{run_id}"
    for _ in range(30):
        await asyncio.sleep(2)
        async with httpx.AsyncClient(timeout=20) as client:
            pr = await client.get(
                poll_url,
                headers={"Authorization": f"Bearer {token}"},
            )
            pr.raise_for_status()
            pd = pr.json()

        status = pd.get("status", "")
        if status in ("completed", "failed", "error"):
            break

    # 응답 텍스트 파싱 — result.data.message.content[0].text
    text = ""
    try:
        text = pd["result"]["data"]["message"]["content"][0]["text"]
    except (KeyError, IndexError, TypeError):
        pass
    if not text:
        text = str(pd)

    return {
        "text": text,
        "thread_id": new_thread_id,
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
        body = resp.json()
        # 응답이 list이면 그대로, dict이면 resources 키 추출
        agents = body if isinstance(body, list) else body.get("resources", body.get("data", []))

    for agent in agents:
        if agent.get("name") == agent_name:
            _agent_id_cache[agent_name] = agent["id"]
            return agent["id"]

    raise ValueError(f"Agent '{agent_name}' not found in wxO")
