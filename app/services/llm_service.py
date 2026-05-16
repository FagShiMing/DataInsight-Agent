from zhipuai import ZhipuAI
from app.core.config import ZHIPUAI_API_KEY, ZHIPUAI_MODEL


client = ZhipuAI(api_key=ZHIPUAI_API_KEY)


def ask_llm(message: str) -> str:
    response = client.chat.completions.create(
        model=ZHIPUAI_MODEL,
        messages=[
            {"role": "user", "content": message}
        ],
    )

    return response.choices[0].message.content