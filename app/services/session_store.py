from uuid import uuid4


# 当前 V0.2 先用进程内存保存 profile，方便验证 session_id 流程。
# 这种方式不依赖数据库或 Redis，适合 MVP；缺点是服务重启后数据会丢失。
_SESSION_PROFILES: dict[str, dict] = {}


def create_session(profile: dict) -> str:
    """保存一次 CSV 数据画像，并返回 session_id。"""
    session_id = str(uuid4())
    _SESSION_PROFILES[session_id] = profile
    return session_id


def get_profile(session_id: str) -> dict | None:
    """根据 session_id 获取之前上传 CSV 生成的数据画像。"""
    return _SESSION_PROFILES.get(session_id)


def delete_session(session_id: str) -> bool:
    """删除指定 session，删除成功返回 True。"""
    if session_id not in _SESSION_PROFILES:
        return False

    del _SESSION_PROFILES[session_id]
    return True
