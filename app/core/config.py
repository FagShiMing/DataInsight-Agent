import os
from dotenv import load_dotenv

load_dotenv()

ZHIPUAI_API_KEY = os.getenv("ZHIPUAI_API_KEY")
ZHIPUAI_MODEL = os.getenv("ZHIPUAI_MODEL", "glm-4.7")


def _parse_cors_origins(raw_value: str | None) -> list[str]:
    if not raw_value:
        return [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]

    return [
        origin.strip()
        for origin in raw_value.split(",")
        if origin.strip()
    ]


CORS_ORIGINS = _parse_cors_origins(os.getenv("CORS_ORIGINS"))
