import json
import os

from zhipuai import ZhipuAI

from app.core.config import ZHIPUAI_API_KEY, ZHIPUAI_MODEL


def _get_api_key() -> str:
    api_key = os.getenv("ZHIPUAI_API_KEY") or ZHIPUAI_API_KEY
    if not api_key:
        raise RuntimeError("missing_api_key")
    return api_key


def _get_client() -> ZhipuAI:
    return ZhipuAI(api_key=_get_api_key())


def ask_llm(message: str) -> str:
    response = _get_client().chat.completions.create(
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

    response = _get_client().chat.completions.create(
        model=ZHIPUAI_MODEL,
        messages=[
            {"role": "user", "content": prompt}
        ],
    )

    return response.choices[0].message.content


def generate_llm_answer(
    question: str,
    selected_tool: str,
    tool_result: dict,
    profile_summary: dict | None = None,
) -> str:
    """基于已执行工具的结构化结果，生成最终自然语言回答。"""
    system_prompt = """
你是 DataInsight-Agent 的数据分析助手。
你只能根据系统提供的数据画像、工具名称和工具执行结果回答。
不要编造不存在的字段、数值、趋势或业务背景。
如果当前工具结果不足以回答用户问题，请明确说明无法判断，并建议下一步应该查看哪些数据。
回答请使用中文。
回答结构：
1. 直接结论
2. 数据依据
3. 可选的进一步分析建议
"""
    user_prompt = f"""
用户问题：
{question}

本次调用的工具：
{selected_tool}

工具返回结果：
{json.dumps(tool_result, ensure_ascii=False, default=str)}

数据画像摘要：
{json.dumps(profile_summary or {}, ensure_ascii=False, default=str)}

请生成面向用户的自然语言回答。
"""

    response = _get_client().chat.completions.create(
        model=ZHIPUAI_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )

    return response.choices[0].message.content
