from datetime import datetime, timezone, timedelta
from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission


@tool(permission=ToolPermission.READ_ONLY)
def get_today_date() -> str:
    """Return today's date in Korean Standard Time (KST, UTC+9).

    Returns:
        str: Today's date formatted as 'YYYY년 MM월 DD일 (요일)'.
    """
    kst = timezone(timedelta(hours=9))
    now = datetime.now(tz=kst)
    weekdays = ["월", "화", "수", "목", "금", "토", "일"]
    weekday = weekdays[now.weekday()]
    return f"{now.year}년 {now.month:02d}월 {now.day:02d}일 ({weekday})"
