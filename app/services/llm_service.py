import json

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


def ask_llm_for_tool_choice(
    question: str,
    profile_summary: dict,
    tools_schema: dict,
) -> str:
    """让 LLM 只返回工具选择 JSON，不在这里解析或执行工具。"""
    prompt = f"""
你是一个 CSV 数据分析 Agent 的工具选择器。

请根据用户问题、数据画像摘要和可用工具，选择一个最合适的工具。

要求：
1. 只返回 JSON，不要返回 Markdown，不要解释原因。
2. JSON 必须包含 tool_name 和 arguments。
3. arguments 必须是 JSON 对象。
4. 如果工具不需要额外参数，arguments 返回空对象。

返回格式示例：
{{
  "tool_name": "missing_value_analysis",
  "arguments": {{}}
}}

用户问题：
{question}

数据画像摘要：
{json.dumps(profile_summary, ensure_ascii=False)}

可用工具：
{json.dumps(tools_schema, ensure_ascii=False)}
"""

    response = client.chat.completions.create(
        model=ZHIPUAI_MODEL,
        messages=[
            {"role": "user", "content": prompt}
        ],
    )

    return response.choices[0].message.content
