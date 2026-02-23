"""
AI v1 路由依賴：認證（X-AI-KEY Header）與 Rate Limit Stub。
此模組與 /api/v1 隔離，保有獨立的安全策略。
"""
from collections import defaultdict

from fastapi import Header
from app.infra.settings import settings
from app.common.exceptions import RateLimitException, UnauthorizedException

# In-memory 計數器 Stub（單 worker 環境有效；多 worker 需改用 Redis）
_counters: dict = defaultdict(int)


def verify_ai_auth(x_ai_key: str = Header(default="", alias="X-AI-KEY")):
    """
    驗證 X-AI-KEY Header 並套用 Rate Limit。
    在 /ai/v1 路由以 dependencies=[Depends(verify_ai_auth)] 掛載。
    """
    if x_ai_key != settings.AI_HEADER_KEY:
        raise UnauthorizedException("X-AI-KEY 無效，拒絕存取")

    _counters[x_ai_key] += 1
    if _counters[x_ai_key] > settings.AI_RATE_LIMIT_PER_KEY:
        raise RateLimitException(
            f"已超過此 KEY 的速率限制（{settings.AI_RATE_LIMIT_PER_KEY} 次）"
        )
