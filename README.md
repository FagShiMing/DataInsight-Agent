# DataInsight Agent

DataInsight Agent 是一个面向 CSV 文件的轻量级数据分析 Agent 后端项目。

项目当前已经实现：CSV 上传、基础数据画像、session_id 内存会话缓存、缺失值分析、数值列摘要、规则版工具选择、可选 LLM 工具选择、fallback 兜底、工具调用轨迹记录、Markdown 报告生成、规则版和可选 LLM 工具选择评估、rule vs llm 工具选择对比评估、按问题类型统计工具选择准确率、hard / regression 评估集、评估版本对比、pytest 自动化测试。

当前项目不包含前端、数据库、RAG、多 Agent 编排。默认的数据问答流程使用规则判断选择工具；如果请求显式传入 `use_llm_tool_choice=true`，则会尝试使用 LLM 输出工具选择 JSON，并在失败时 fallback 到规则版。

## 项目背景

在实际数据分析工作中，拿到一个 CSV 文件后，第一步通常不是复杂建模，而是先回答这些基础问题：

- 数据有多少行、多少列？
- 有哪些字段？
- 每个字段是什么类型？
- 哪些字段有缺失值？
- 数值字段的均值、最大值、最小值、中位数是多少？
- 能否快速生成一份可读的数据分析报告？

DataInsight Agent 把这些固定分析步骤封装成后端接口，并用一个轻量 Agent 调度工具完成回答。这样既能展示 pandas 数据处理能力，也能展示 Agent Tool Calling 的基本工程思路。

## 核心功能

当前已实现功能：

- CSV 文件上传和读取。
- 上传 CSV 后返回 `session_id`，后续可以用 `question + session_id` 继续提问。
- 基础数据画像：
  - 行数
  - 列数
  - 字段名
  - 字段类型
  - 前 5 行预览
- 缺失值统计：
  - 每列缺失值数量
  - 每列缺失率
- 数值列摘要：
  - `count`
  - `mean`
  - `min`
  - `max`
  - `median`
  - `std`
- 类别列摘要：
  - 唯一值数量
  - Top 5 高频值
- 工具注册表：
  - `profile_csv`
  - `missing_value_analysis`
  - `numeric_summary`
  - `answer_data_question`
  - `generate_report`
- 规则版 Agent 工具调用：
  - 根据问题关键词选择工具
  - 调用工具并返回结构化结果
  - 记录工具调用轨迹
- Markdown 数据分析报告生成。
- pytest 自动化测试。

## V0.2 当前能力总结

V0.2 当前已经支持：

- `session_id` 会话缓存：上传 CSV 后返回 `session_id`，后续提问可以复用已生成的 profile。
- `/chat/data` 基于 `session_id` 提问：请求体可以只传 `question + session_id`。
- 规则版工具选择：默认使用关键词规则选择工具，保证本地演示和测试稳定。
- 可选 LLM 工具选择：传入 `use_llm_tool_choice=true` 后，Agent 会尝试让 LLM 输出工具选择 JSON。
- fallback 兜底：LLM 输出非法 JSON、工具不存在或工具调用失败时，会回退到规则版工具选择。
- `tool_trace` 调用轨迹：记录工具名、参数、状态、结果摘要、是否 fallback、fallback 原因和 LLM 原始输出。
- 工具选择评估集：使用 `eval/tool_choice_cases.jsonl` 和 `scripts/evaluate_tool_choice.py` 评估规则版工具选择准确率。

V0.2 阶段的规则版工具选择评估结果：

```text
total_cases: 16
correct: 16
accuracy: 1.0000
```

说明：这是 V0.2 阶段的基础评估结果，只代表当时 16 条固定样例全部命中规则，不代表真实开放场景下工具选择永远满分。

## V0.3 当前能力总结

V0.3 在 V0.2 的规则版工具选择评估基础上，补充了可选 LLM 工具选择评估能力：

- `rule` 模式：默认模式，只使用规则版工具选择，不需要 API Key，不调用真实 LLM。
- `llm` 模式：复用 Agent 中已有的 `use_llm_tool_choice=True` 逻辑，用于观察模型是否能正确选择工具。
- 每条评估样例都会记录：
  - `id`
  - `question`
  - `expected_tool`
  - `actual_tool`
  - `correct`
  - `error`
- 整体评估指标包括：
  - `total_cases`
  - `correct`
  - `accuracy`
  - `failed_cases`
  - `case_results`
- 支持通过 `--output` 保存完整 JSON 评估结果，方便后续对比 rule 和 LLM 的稳定性。

注意：`llm` 模式需要配置智谱 API Key。如果 API Key 缺失或 LLM 调用失败，评估脚本不会直接崩溃，而是把错误记录到对应 case 的 `error` 和 `failed_cases` 中。

## V0.4 当前能力总结

V0.4 把工具选择评估从“单模式评估”推进到“评估集扩充 + rule / llm 对比”：

- `eval/tool_choice_cases.jsonl` 从 16 条扩充到 50 条，覆盖更真实的用户表达和容易混淆的问题。
- 评估集覆盖当前工具注册表中的 5 类工具：
  - `profile_csv`
  - `missing_value_analysis`
  - `numeric_summary`
  - `answer_data_question`
  - `generate_report`
- 新增 `scripts/compare_tool_choice_modes.py`：
  - 默认只运行 `rule` 模式，不调用真实 LLM。
  - 只有显式传入 `--run-llm` 时，才会尝试运行 `llm` 模式。
  - 输出 rule / llm 各自准确率、失败样例和差异样例。
  - 支持 `--output` 保存 JSON 对比结果。
- 新增测试确保 compare 脚本默认不访问真实 LLM，LLM 分支通过 mock 验证。

当前 V0.4 规则版工具选择评估结果：

```text
total_cases: 50
correct: 38
accuracy: 0.7600
```

说明：V0.4 的评估集故意加入了“数据完整性”“字段质量”“汇报材料”“销售额和利润整体表现”等更接近真实用户的表达，因此 rule 准确率不再追求 100%。这个结果更适合用来定位规则版 Agent 在哪些表达上容易选错工具。

## V0.5 当前能力总结

V0.5 把工具选择评估从“只看总体准确率”升级为“按问题类型看准确率和失败分布”：

- 每条评估 case 新增 `category` 字段。
- `evaluate_tool_choice.py` 输出新增：
  - `category_metrics`：按问题类型统计 `total / correct / accuracy`。
  - `failure_analysis`：统计失败样例集中在哪些 `category` 和 `expected_tool`。
- `compare_tool_choice_modes.py` 输出新增：
  - `category_comparison`：当运行 `--run-llm` 时，对比 rule 和 llm 在每个 category 下的准确率。
  - 不运行 `--run-llm` 时，`category_comparison` 标记为 `skipped`。
- `case_results` 和 `failed_cases` 中都会保留 `category`，方便定位具体失败样例。

当前 category 类型：

- `profile_overview`
- `missing_value`
- `numeric_summary`
- `report_generation`
- `data_question`
- `ambiguous_intent`

当前 V0.5 rule 模式分类评估结果：

```text
total_cases: 50
correct: 38
accuracy: 0.7600

profile_overview: total=5, correct=5, accuracy=1.0000
missing_value: total=7, correct=6, accuracy=0.8571
numeric_summary: total=9, correct=9, accuracy=1.0000
report_generation: total=9, correct=6, accuracy=0.6667
data_question: total=7, correct=7, accuracy=1.0000
ambiguous_intent: total=13, correct=5, accuracy=0.3846
```

当前失败样例分析：

```text
total_failed: 12
failed_by_category:
  ambiguous_intent: 8
  missing_value: 1
  report_generation: 3

failed_by_expected_tool:
  missing_value_analysis: 5
  numeric_summary: 3
  generate_report: 4
```

说明：V0.5 的重点不是立刻把准确率拉满，而是先看清楚失败分布。当前 rule baseline 的主要问题集中在模糊表达，例如“数据完整性”“整体表现”“数据分析总结”“复盘/周报内容”等问题容易被规则分到普通问答。

## V0.6 当前能力总结

V0.6 基于 V0.5 的 `failure_analysis` 优化了 rule 模式工具选择规则，重点处理 `ambiguous_intent` 和 `report_generation` 的失败样例。

优化内容：

- 报告生成规则补充“发给老板、汇报、文档、分析总结、复盘、周报”等表达。
- 缺失值规则补充“没填全、空白、补数据、完整性、完整率、字段质量”等表达。
- 数值摘要规则补充“销售额、利润、年龄、金额、收入、范围、连续型、波动”等表达。
- 本地 CSV 画像规则支持带 `.csv` 路径的问题中出现“整体、概览、结构”等表达。

历史评估结果保存在：

- `eval/history/v0.5_rule_result.json`
- `eval/history/v0.6_rule_result.json`
- `eval/history/v0.5_vs_v0.6_rule_compare.json`

V0.5 vs V0.6 rule 结果：

```text
V0.5: total_cases=50, correct=38, accuracy=0.7600
V0.6: total_cases=50, correct=50, accuracy=1.0000
accuracy_delta: +0.2400
correct_delta: +12
```

重点 category 变化：

```text
ambiguous_intent: 0.3846 -> 1.0000, delta=+0.6154
report_generation: 0.6667 -> 1.0000, delta=+0.3333
missing_value: 0.8571 -> 1.0000, delta=+0.1429
```

本次对比结果：

```text
improved_cases: 12
regressed_cases: 0
```

说明：V0.6 没有调用 LLM，只是基于 V0.5 暴露出来的失败分布做规则优化。当前 50 条评估集已全部命中，但这仍然只是当前评估集上的结果，不代表开放问题永远满分。

## V0.7 当前能力总结

V0.7 的目标是验证 V0.6 rule 规则是否过拟合原始 50 条 case。项目现在区分三类评估集：

- `eval/tool_choice_cases.jsonl`：基础评估集，保留原始 50 条 case，并新增 `subcategory`。
- `eval/tool_choice_hard_cases.jsonl`：更难、更开放、更口语化的评估集，用来暴露规则边界。
- `eval/tool_choice_regression_cases.jsonl`：回归测试集，用来防止后续规则优化拉低稳定能力。

V0.7 新增字段和指标：

- `subcategory`：比 `category` 更细的问题类型。
- `subcategory_metrics`：按 subcategory 统计 `total / correct / accuracy`。
- `failed_by_subcategory`：失败样例按 subcategory 的分布。

V0.7 rule 评估结果：

```text
base: total_cases=50, correct=50, accuracy=1.0000
hard: total_cases=32, correct=17, accuracy=0.5312
regression: total_cases=15, correct=15, accuracy=1.0000
```

hard cases 失败分布：

```text
failed_by_category:
  profile_overview: 4
  ambiguous_intent: 4
  missing_value: 3
  report_generation: 3
  data_question: 1

failed_by_subcategory:
  ambiguous_overview: 3
  missing_vs_qa: 3
  numeric_vs_business_question: 3
  report_vs_summary: 2
  profile_vs_data_question: 1
  ambiguous_quality: 1
  report_vs_profile: 1
  business_insight: 1
```

说明：hard cases 准确率低于 1.0 是可接受的。它的目的不是刷分，而是暴露规则系统在开放表达下的边界；regression cases 则用于保护已经稳定的核心能力。

当前已有但不作为主要 Agent 流程的能力：

- `/chat` 基础 LLM 聊天接口。
- 智谱 GLM API Key 从环境变量读取。

## 技术栈

- Python
- FastAPI
- pandas
- Pydantic
- pytest
- python-dotenv
- 智谱 GLM-4.7 SDK

## 项目结构

```text
DataInsight-Agent/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── core/
│   │   └── config.py
│   └── services/
│       ├── agent_service.py
│       ├── data_profile.py
│       ├── llm_service.py
│       ├── report_service.py
│       ├── session_store.py
│       └── tools.py
├── data/
│   └── sample_sales.csv
├── docs/
│   └── project_review.md
├── eval/
│   ├── history/
│   │   ├── v0.5_rule_result.json
│   │   ├── v0.5_vs_v0.6_rule_compare.json
│   │   ├── v0.6_rule_result.json
│   │   ├── v0.7_base_rule_result.json
│   │   ├── v0.7_hard_rule_result.json
│   │   └── v0.7_regression_rule_result.json
│   ├── tool_choice_cases.jsonl
│   ├── tool_choice_compare_result.json
│   ├── tool_choice_hard_cases.jsonl
│   ├── tool_choice_regression_cases.jsonl
│   └── tool_choice_result.json
├── scripts/
│   ├── compare_eval_versions.py
│   ├── compare_tool_choice_modes.py
│   └── evaluate_tool_choice.py
├── tests/
│   ├── test_compare_eval_versions.py
│   ├── test_compare_tool_choice_modes.py
│   ├── test_data_profile.py
│   ├── test_eval_case_schema.py
│   ├── test_evaluate_tool_choice.py
│   ├── test_llm_tool_choice.py
│   ├── test_profile_upload.py
│   ├── test_report_service.py
│   ├── test_session_chat.py
│   └── test_tools_agent.py
├── pytest.ini
├── requirements.txt
└── README.md
```

核心文件说明：

- `app/main.py`：FastAPI 入口，定义 API 接口。
- `app/services/data_profile.py`：CSV 读取和数据画像逻辑。
- `app/services/tools.py`：工具函数和工具注册表。
- `app/services/agent_service.py`：规则版 Agent 调度、工具调用和轨迹记录。
- `app/services/report_service.py`：Markdown 报告生成。
- `app/services/session_store.py`：内存版 session_id 缓存，用于保存上传 CSV 后生成的 profile。
- `app/services/llm_service.py`：智谱 LLM 调用封装。
- `tests/`：pytest 测试。
- `docs/project_review.md`：面试复盘材料。
- `eval/tool_choice_cases.jsonl`：工具选择评估样例。
- `eval/tool_choice_hard_cases.jsonl`：更难、更开放、更口语化的工具选择评估样例。
- `eval/tool_choice_regression_cases.jsonl`：防止规则优化退化的核心回归样例。
- `eval/tool_choice_compare_result.json`：工具选择对比脚本通过 `--output` 生成的 JSON 结果文件。
- `eval/tool_choice_result.json`：单模式工具选择评估脚本通过 `--output` 生成的 JSON 结果文件。
- `eval/history/`：保存不同版本的 rule 评估结果和版本对比结果。
- `scripts/evaluate_tool_choice.py`：工具选择准确率评估脚本，支持 `rule` 和 `llm` 两种模式。
- `scripts/compare_tool_choice_modes.py`：工具选择模式对比脚本，默认只运行 `rule`，可选运行 `llm`。
- `scripts/compare_eval_versions.py`：评估版本对比脚本，用于比较优化前后的 JSON 结果。

## Agent 工具调用流程

当前 Agent 是轻量规则版实现，不依赖 LangChain / LangGraph。

核心流程：

```text
用户上传 CSV，得到 session_id
-> 用户提交 question 和 session_id
-> 后端根据 session_id 取出 profile
-> choose_tool_by_rules(question)
-> 根据关键词选择工具名
-> get_tool(tool_name)
-> call_tool(tool_name, arguments)
-> 工具执行
-> build_trace(...) 记录调用轨迹
-> 返回 answer / result / tool_trace
```

规则示例：

- 问题包含“缺失、空值、null”：调用 `missing_value_analysis`。
- 问题包含“数值、平均、最大、最小、中位、标准差、摘要”：调用 `numeric_summary`。
- 问题包含“报告、Markdown”：调用 `generate_report`。
- 其他问题：调用 `answer_data_question`。

工具调用轨迹包含：

- `tool_name`
- `arguments`
- `status`
- `result_summary` 或 `error_message`
- `timestamp`

## Session 机制

当前项目实现了一个最小可用的内存版 session 机制，核心文件是：

```text
app/services/session_store.py
```

它提供三个函数：

- `create_session(profile: dict) -> str`
- `get_profile(session_id: str) -> dict | None`
- `delete_session(session_id: str) -> bool`

为什么当前使用内存字典：

- 当前阶段目标是验证 Agent MVP 流程，不引入数据库、Redis 或复杂部署。
- 内存字典实现简单，适合学习、测试和面试讲解。
- 上传 CSV 后保存 profile，后续提问只需要传 `session_id`，避免每次把完整 profile 传回后端。

当前流程：

```text
POST /profile/upload
-> 后端读取 CSV 并生成 profile
-> create_session(profile)
-> 返回 session_id + profile
-> POST /chat/data
-> 传 question + session_id
-> get_profile(session_id)
-> 调用现有 Agent 逻辑回答问题
```

`/chat/data` 目前兼容两种请求方式：

新方式，推荐用于正常流程：

```json
{
  "question": "哪些字段有缺失值？",
  "session_id": "上传 CSV 后返回的 session_id"
}
```

旧方式，继续兼容直接传 profile：

```json
{
  "question": "哪些字段有缺失值？",
  "profile": {
    "shape": {
      "rows": 5,
      "columns": 5
    },
    "columns": ["date", "product", "region", "sales", "profit"],
    "missing_values": {
      "sales": 1
    },
    "missing_rate": {
      "sales": 0.2
    },
    "numeric_summary": {}
  }
}
```

当前方案局限性：

- 服务重启后，内存中的 session 会全部丢失。
- 多进程或多实例部署时，不同进程之间不会共享 session。
- 当前没有过期时间，长期运行可能造成内存增长。
- 没有持久化，无法保存历史上传记录和历史分析结果。

后续生产化可以替换为：

- Redis：适合缓存 session，支持 TTL 过期，多实例共享。
- SQLite：适合本地单机持久化，能保存上传历史和分析报告。
- PostgreSQL：适合正式生产环境，能支持用户、权限、历史记录和审计查询。

## API 接口说明

### 健康检查

```http
GET /health
```

返回示例：

```json
{
  "status": "ok"
}
```

### 上传 CSV 并生成数据画像

```http
POST /profile/upload
```

请求类型：

```text
multipart/form-data
```

请求参数：

- `file`：上传的 CSV 文件，只支持 `.csv` 后缀。

返回字段：

- `session_id`：本次上传生成的会话 ID，后续 `/chat/data` 可以用它查找 profile。
- `filename`：上传文件名。
- `shape.rows`：行数。
- `shape.columns`：列数。
- `columns`：字段名列表。
- `dtypes`：每列数据类型。
- `missing_values`：每列缺失值数量。
- `missing_rate`：每列缺失率。
- `numeric_summary`：数值列摘要。
- `categorical_summary`：类别列摘要。
- `preview`：前 5 行数据预览。

### 围绕数据提问

```http
POST /chat/data
```

推荐方式：传 `question + session_id`。

请求示例：

```json
{
  "question": "哪些字段有缺失值？",
  "session_id": "上传 CSV 后返回的 session_id"
}
```

兼容旧方式：直接传 `question + profile`。

请求示例：

```json
{
  "question": "哪些字段有缺失值？",
  "profile": {
    "shape": {
      "rows": 5,
      "columns": 5
    },
    "columns": ["date", "product", "region", "sales", "profit"],
    "missing_values": {
      "date": 0,
      "product": 0,
      "region": 0,
      "sales": 1,
      "profit": 0
    },
    "missing_rate": {
      "date": 0.0,
      "product": 0.0,
      "region": 0.0,
      "sales": 0.2,
      "profit": 0.0
    },
    "numeric_summary": {}
  }
}
```

返回字段：

- `answer`：面向用户的回答。
- `tool_name`：Agent 本次选择的工具。
- `result`：工具执行结果。
- `tool_trace`：工具调用轨迹。

错误处理：

- `session_id` 不存在：返回 404，`detail` 为 `Session not found`。
- `session_id` 和 `profile` 都不传：返回 400，`detail` 为 `Either session_id or profile is required`。

### 生成 Markdown 报告

```http
POST /report/generate
```

请求示例：

```json
{
  "profile": {
    "shape": {
      "rows": 5,
      "columns": 5
    },
    "columns": ["date", "product", "region", "sales", "profit"],
    "missing_values": {
      "sales": 1
    },
    "missing_rate": {
      "sales": 0.2
    },
    "numeric_summary": {}
  },
  "insights": "建议关注 sales 字段缺失值。",
  "tool_trace": []
}
```

返回字段：

- `markdown`：Markdown 格式的数据分析报告。

### 本地 CSV 文件画像

```http
GET /analyze-csv?file_path=data/sample_sales.csv
```

作用：读取项目本地 CSV 文件路径，并返回数据画像。

### 基础 LLM 聊天

```http
POST /chat
```

作用：调用智谱 LLM 返回普通聊天结果。

注意：这个接口需要配置 `ZHIPUAI_API_KEY`，当前不参与 `/chat/data` 的规则版 Agent 工具调用流程。

## 本地运行方式

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

如果使用项目内虚拟环境，可以直接使用 `.venv/bin/python`、`.venv/bin/pytest`、`.venv/bin/uvicorn`。

### 2. 配置环境变量

如果需要测试 `/chat` LLM 接口，请在 `.env` 中配置：

```text
ZHIPUAI_API_KEY=your_api_key_here
ZHIPUAI_MODEL=glm-4.7
```

如果只测试 CSV 上传、数据画像、Agent 工具调用和报告生成，不需要配置 LLM API Key。

### 3. 启动服务

```bash
uvicorn app.main:app --reload
```

或使用项目虚拟环境：

```bash
.venv/bin/uvicorn app.main:app --reload
```

Swagger 地址：

```text
http://127.0.0.1:8000/docs
```

如果 8000 端口被占用，可以换端口：

```bash
.venv/bin/uvicorn app.main:app --reload --port 8010
```

## 测试方式

运行全部测试：

```bash
pytest
```

如果全局没有 `pytest`，可以使用：

```bash
python -m pytest
```

或项目虚拟环境：

```bash
.venv/bin/pytest
```

当前测试覆盖：

- CSV 正常上传。
- 非 CSV 文件返回错误。
- 空 CSV 文件返回错误。
- 数据画像字段是否正确。
- 缺失值分析是否正确。
- 数值摘要是否正确。
- 工具注册表能否找到工具。
- 工具不存在时是否返回错误。
- Agent 是否能完成一次工具调用闭环。
- Agent 是否能处理非法 JSON。
- 工具选择评估脚本是否能正常读取样例并输出结果。
- 工具选择评估脚本是否支持 `rule` / `llm` 模式。
- 工具选择评估脚本是否能跳过空行、识别缺字段和 JSON 格式错误。
- 工具选择评估脚本是否能校验 `category` 字段和非法分类。
- 工具选择评估脚本是否能校验 `subcategory` 字段。
- 工具选择评估脚本是否能输出 `category_metrics`、`subcategory_metrics` 和 `failure_analysis`。
- 基础评估集、hard 评估集和 regression 评估集是否都符合 JSONL schema。
- hard 评估集和 regression 评估集是否都能正常运行 rule 评估。
- regression 评估集是否保持 rule accuracy 为 1.0。
- 工具选择评估脚本是否能通过 `--output` 保存 JSON 结果。
- LLM 工具选择评估是否可以通过 mock 测试，避免真实请求 API。
- 工具选择对比脚本默认是否只运行 `rule` 模式。
- 工具选择对比脚本是否能通过 mock 比较 `rule` 和 `llm` 的差异样例。
- 工具选择对比脚本是否能输出 `category_comparison`。
- 工具选择对比脚本是否能通过 `--output` 保存 JSON 对比结果。
- 评估版本对比脚本是否能计算 accuracy delta、category delta、improved cases 和 regressed cases。
- 上传 CSV 后是否返回 `session_id`。
- `/chat/data` 是否支持 `question + session_id`。
- 不存在的 `session_id` 是否返回 404。
- 旧的 `question + profile` 方式是否仍然可用。
- Markdown 报告是否包含核心章节。

当前验证结果：

```text
65 passed
```

## 工具选择评估 / Tool Choice Evaluation

评估集文件：

```text
eval/tool_choice_cases.jsonl
```

默认运行方式是 `rule` 模式，只使用规则版工具选择，不需要 API Key，也不会调用真实 LLM：

```bash
python scripts/evaluate_tool_choice.py
```

如果使用项目虚拟环境：

```bash
.venv/bin/python scripts/evaluate_tool_choice.py
```

也可以显式指定 `rule` 模式：

```bash
.venv/bin/python scripts/evaluate_tool_choice.py --mode rule
```

`llm` 模式用于观察模型是否能根据问题正确选择工具，需要先配置智谱 API Key：

```bash
.venv/bin/python scripts/evaluate_tool_choice.py --mode llm
```

输出指标包括：

- `total_cases`：评估样例总数。
- `correct`：工具选择正确的样例数。
- `accuracy`：准确率。
- `category_metrics`：按问题类型统计准确率。
- `subcategory_metrics`：按更细的问题类型统计准确率。
- `failure_analysis`：按 category 和 expected_tool 统计失败分布。
- `failed_cases`：失败样例，包含问题、期望工具、实际工具和错误原因。

V0.5 给每条评估 case 增加了 `category`，用于区分问题类型：

- `profile_overview`
- `missing_value`
- `numeric_summary`
- `report_generation`
- `data_question`
- `ambiguous_intent`

现在评估结果不仅能看总体 `accuracy`，也能看每一类问题的 `accuracy`。`failure_analysis` 可以帮助定位失败样例集中在哪些 category 和 expected_tool 上。

V0.7 进一步增加了 `subcategory`，用于拆分更细的问题边界，例如：

- `missing_vs_qa`
- `report_vs_summary`
- `report_vs_profile`
- `numeric_vs_business_question`
- `profile_vs_data_question`
- `ambiguous_overview`
- `ambiguous_quality`
- `ambiguous_insight`
- `field_specific_question`
- `business_insight`
- `regression_core`

查看每条样例结果：

```bash
.venv/bin/python scripts/evaluate_tool_choice.py --mode rule --verbose
```

保存完整 JSON 结果：

```bash
.venv/bin/python scripts/evaluate_tool_choice.py --mode rule --output eval/tool_choice_result.json
```

基础评估集：

```bash
.venv/bin/python scripts/evaluate_tool_choice.py --mode rule --cases eval/tool_choice_cases.jsonl
```

hard cases：

```bash
.venv/bin/python scripts/evaluate_tool_choice.py --mode rule --cases eval/tool_choice_hard_cases.jsonl
```

regression cases：

```bash
.venv/bin/python scripts/evaluate_tool_choice.py --mode rule --cases eval/tool_choice_regression_cases.jsonl
```

保存 V0.7 评估结果：

```bash
.venv/bin/python scripts/evaluate_tool_choice.py --mode rule --cases eval/tool_choice_cases.jsonl --output eval/history/v0.7_base_rule_result.json
.venv/bin/python scripts/evaluate_tool_choice.py --mode rule --cases eval/tool_choice_hard_cases.jsonl --output eval/history/v0.7_hard_rule_result.json
.venv/bin/python scripts/evaluate_tool_choice.py --mode rule --cases eval/tool_choice_regression_cases.jsonl --output eval/history/v0.7_regression_rule_result.json
```

V0.4 新增 rule vs llm 对比脚本。默认只运行 `rule`，不会调用真实 LLM：

```bash
.venv/bin/python scripts/compare_tool_choice_modes.py
```

查看对比摘要和差异详情：

```bash
.venv/bin/python scripts/compare_tool_choice_modes.py --verbose
```

运行 rule vs llm 对比，需要先配置智谱 API Key，并显式加上 `--run-llm`：

```bash
.venv/bin/python scripts/compare_tool_choice_modes.py --run-llm
```

保存对比结果：

```bash
.venv/bin/python scripts/compare_tool_choice_modes.py --run-llm --output eval/tool_choice_compare_result.json
```

如果只想保存默认 rule-only 对比结果，也可以不加 `--run-llm`：

```bash
.venv/bin/python scripts/compare_tool_choice_modes.py --output eval/tool_choice_compare_result.json
```

说明：

- `compare_tool_choice_modes.py` 默认不会调用真实 LLM。
- 只有加 `--run-llm` 才会尝试运行 `llm` 模式。
- `rule` 模式不需要 API Key。
- `llm` 模式需要智谱 API Key。
- 对比结果可以帮助定位 Agent 在什么类型的问题上选错工具，例如“报告生成 vs 普通问答”“缺失值分析 vs 数据问答”“数值摘要 vs 数据问答”。
- V0.5 的 `category_comparison` 可以进一步对比 rule 和 llm 在每个问题类型上的表现。

V0.6 新增评估版本对比脚本，用于比较规则优化前后的结果：

```bash
.venv/bin/python scripts/compare_eval_versions.py --before eval/history/v0.5_rule_result.json --after eval/history/v0.6_rule_result.json
```

查看优化和退化的具体样例：

```bash
.venv/bin/python scripts/compare_eval_versions.py --before eval/history/v0.5_rule_result.json --after eval/history/v0.6_rule_result.json --verbose
```

保存版本对比结果：

```bash
.venv/bin/python scripts/compare_eval_versions.py --before eval/history/v0.5_rule_result.json --after eval/history/v0.6_rule_result.json --output eval/history/v0.5_vs_v0.6_rule_compare.json
```

## 示例输入输出

示例文件：

```text
data/sample_sales.csv
```

示例内容：

```csv
date,product,region,sales,profit
2026-04-01,A,济南,1200,300
2026-04-02,B,杭州,1800,450
2026-04-03,A,济南,1500,380
2026-04-04,C,上海,,500
2026-04-05,B,杭州,2100,620
```

上传后会得到类似结果：

```json
{
  "session_id": "7f4c2d2a-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "filename": "sample_sales.csv",
  "shape": {
    "rows": 5,
    "columns": 5
  },
  "columns": ["date", "product", "region", "sales", "profit"],
  "missing_values": {
    "date": 0,
    "product": 0,
    "region": 0,
    "sales": 1,
    "profit": 0
  },
  "missing_rate": {
    "date": 0.0,
    "product": 0.0,
    "region": 0.0,
    "sales": 0.2,
    "profit": 0.0
  }
}
```

围绕数据提问：

```text
哪些字段有缺失值？
```

请求可以只传：

```json
{
  "question": "哪些字段有缺失值？",
  "session_id": "上传 CSV 后返回的 session_id"
}
```

Agent 会选择：

```text
missing_value_analysis
```

返回中会包含：

```json
{
  "answer": "共有 1 个字段存在缺失值，缺失单元格总数为 1。",
  "tool_name": "missing_value_analysis",
  "tool_trace": [
    {
      "tool_name": "missing_value_analysis",
      "status": "success"
    }
  ]
}
```

## 项目亮点

- 用 pandas 完成确定性数据画像，避免所有分析都依赖 LLM。
- 用内存 session_id 缓存 profile，让上传和后续问答形成更自然的流程。
- 使用工具注册表管理 Agent 可调用能力，结构清晰，方便扩展。
- Agent 调用过程会记录工具轨迹，便于调试和面试讲解。
- 不引入 LangChain / LangGraph，代码更轻，适合说明 Tool Calling 原理。
- pytest 覆盖核心业务逻辑，不需要先启动服务也能验证主要功能。
- Markdown 报告可以作为直接展示的分析产物。

## 后续优化方向

- 增加更多数据分析工具，例如异常值检测、相关性分析、分组统计。
- 继续扩充工具选择评估集，加入更多真实表达、边界问题和容易混淆的问题。
- 用 hard cases 暴露 rule 边界，用 regression cases 保护已稳定能力。
- 基于 V0.5 的 `failure_analysis` 优先优化 `ambiguous_intent`、`report_generation` 等失败较多的类型。
- 继续保留历史评估结果，用版本对比脚本观察每次规则或 prompt 修改是否引入退化。
- 增加报告完整性和异常处理能力评估。
- 按问题类型细分 rule 和 llm 两种工具选择模式的稳定性。
- 将当前内存 session_store 升级为 Redis、SQLite 或 PostgreSQL，保存上传记录、工具调用轨迹和报告。
- 增加极简前端或 Streamlit 页面，方便非技术用户演示。
- 对 `/chat` LLM 调用增加 mock 测试，避免测试依赖真实外部 API。

## 当前限制

- 当前 session_store 使用内存字典，服务重启后 session 会丢失。
- 多进程或多实例部署时，内存 session 不共享。
- 当前 session 没有过期时间，也没有持久化。
- 默认 Agent 工具选择是规则判断，不是真正的 LLM 自主规划。
- `/chat` 依赖外部 LLM API 和环境变量。
- 当前没有数据库、前端、RAG 和 Docker。

## 每日开发记录

> 说明：下面的日期是按当前项目记录和开发计划整理的阶段日志，用来帮助复盘“每一天做了什么、产出了什么、学到了什么”。

### 2026-04-26：项目立项与基础规划

目标：确定 DataInsight Agent 的项目方向和第一阶段边界。

完成内容：

- 明确项目定位：用于求职展示的 AI 数据分析 Agent。
- 确定第一阶段先做后端，不急着做前端、数据库、RAG、Docker。
- 确定核心业务主线：

```text
CSV 数据输入 -> pandas 读取 -> 数据画像 -> JSON 返回 -> 后续接入 Agent
```

- 初步确定技术栈：
  - Python
  - FastAPI
  - pandas
  - Pydantic
  - pytest
  - 智谱 GLM-4.7

阶段价值：

- 把项目从“想做一个 AI Agent”收敛成了一个可落地、可展示、可逐步扩展的后端项目。
- 先做确定性的数据分析能力，再考虑 LLM 和 Agent，避免一开始就过度复杂。

### 2026-04-27：FastAPI 基础服务、LLM 配置、数据画像模块

目标：搭建后端基础结构，并完成最早的数据画像函数。

完成内容：

- 搭建 FastAPI 应用入口。
- 新增健康检查接口：

```http
GET /health
```

- 配置智谱 GLM-4.7 相关环境变量读取。
- 新增基础聊天接口：

```http
POST /chat
```

- 新增数据画像模块：

```text
app/services/data_profile.py
```

- 实现本地 CSV 文件分析函数：

```python
analyze_csv(file_path: str)
```

- 实现 DataFrame 数据画像函数：

```python
profile_dataframe(df)
```

当日核心产出：

- `app/main.py`
- `app/core/config.py`
- `app/services/llm_service.py`
- `app/services/data_profile.py`

当日技术点：

- FastAPI 应用如何创建。
- `.env` 环境变量如何读取。
- 如何封装 LLM 调用服务。
- pandas 如何读取 CSV。
- DataFrame 如何统计行列数、字段名、数据类型、缺失值和数值列摘要。

### 2026-04-28：实现 CSV 上传数据画像接口原型

目标：把数据画像能力接入 FastAPI，让用户可以通过接口上传 CSV 文件并得到分析结果。

完成内容：

- 新增 CSV 上传接口：

```http
POST /profile/upload
```

- 使用 FastAPI 的 `UploadFile` 和 `File` 接收上传文件。
- 使用 `await file.read()` 读取上传内容。
- 使用 `BytesIO` 把上传内容转成 pandas 可读取对象。
- 使用 `pandas.read_csv()` 读取 CSV。
- 调用 `profile_dataframe(df)` 生成数据画像。
- 返回上传文件名和画像结果。

当日核心流程：

```text
上传 CSV 文件
-> FastAPI 接收文件
-> 读取文件二进制内容
-> pandas 读取为 DataFrame
-> 调用数据画像函数
-> 返回 JSON
```

阶段价值：

- 4.27 的 `data_profile.py` 只是本地函数能力。
- 4.28 把这个能力变成了可以通过 HTTP 调用的后端接口。
- 这一天完成的是“功能原型”，已经可以在 Swagger 中上传 CSV 进行测试。

### 2026-04-29：稳定化 CSV 上传数据画像模块

目标：把 4.28 的上传接口从“能用”打磨成“稳定、可测试、可展示”的后端业务模块。

完成内容：

- 优化 `/profile/upload` 接口返回结构。
- 校验文件后缀，只允许 `.csv`。
- 处理空文件。
- 处理 pandas 读取失败。
- 处理未知服务端错误。
- 返回更清晰的 JSON 结构：
  - `filename`
  - `shape.rows`
  - `shape.columns`
  - `columns`
  - `dtypes`
  - `missing_values`
  - `numeric_summary`
  - `preview`
- 给数据画像结果新增前 5 行预览。
- 新增示例数据：

```text
data/sample_sales.csv
```

- 新增接口测试：

```text
tests/test_profile_upload.py
```

- 新增 pytest 配置：

```text
pytest.ini
```

- 新增 Python 包标识文件：

```text
app/__init__.py
```

当日核心产出：

- `app/main.py`
- `app/services/data_profile.py`
- `data/sample_sales.csv`
- `tests/test_profile_upload.py`
- `pytest.ini`
- `app/__init__.py`
- `README.md`

阶段价值：

- 4.28 已经能上传 CSV 并返回画像。
- 4.29 没有改变核心统计算法，而是增强工程质量：
  - 返回结构更适合展示。
  - 错误信息更清楚。
  - pytest 可以自动验证接口。
  - README 可以支持后续复盘。

### 2026-05-16：补齐 CSV 数据分析 Agent MVP

目标：把项目从“CSV 上传画像接口”推进到“能展示 Agent 工具调用流程的 MVP”。

完成内容：

- 增强数据画像能力：
  - 缺失值数量
  - 缺失率
  - 数值列 `count / mean / min / max / median / std`
  - 类别列唯一值数量和高频值
  - 前 5 行预览
- 新增工具模块：
  - `profile_csv`
  - `missing_value_analysis`
  - `numeric_summary`
  - `answer_data_question`
  - `generate_report`
- 新增统一工具注册表 `TOOL_REGISTRY`。
- 新增规则版轻量 Agent：
  - 根据用户问题选择工具。
  - 调用工具并返回结构化结果。
  - 记录工具调用轨迹。
  - 处理非法 JSON、工具不存在、参数错误和工具执行失败。
- 新增 Markdown 报告生成能力。
- 新增数据问答接口：

```http
POST /chat/data
```

- 新增报告生成接口：

```http
POST /report/generate
```

- 新增测试文件，覆盖数据画像、工具注册、Agent 闭环和报告生成。

当日核心产出：

- `app/services/tools.py`
- `app/services/agent_service.py`
- `app/services/report_service.py`
- `tests/test_data_profile.py`
- `tests/test_tools_agent.py`
- `tests/test_report_service.py`
- `README.md`

阶段价值：

- 项目已经具备“上传 CSV -> 数据画像 -> 提问 -> 工具选择 -> 工具调用 -> 轨迹记录 -> 报告生成”的完整 MVP 闭环。
- 当前 Agent 不依赖重型框架，便于学习、复盘和面试解释。

### 2026-05-16：V0.3 工具选择评估升级

目标：把工具选择评估从“只评估规则版基线”升级为“规则版基线 + 可选 LLM 工具选择评估”。

完成内容：

- 增强 `scripts/evaluate_tool_choice.py`：
  - 新增 `--cases` 参数，用于指定评估集路径。
  - 新增 `--mode rule|llm` 参数，默认仍为 `rule`。
  - 新增 `--verbose` 参数，用于查看每条 case 的评估结果。
  - 新增 `--output` 参数，用于保存 JSON 评估结果。
- 保留默认规则版评估行为：

```bash
.venv/bin/python scripts/evaluate_tool_choice.py
```

- 复用已有 `run_agent(..., use_llm_tool_choice=True)` 作为 LLM 工具选择评估入口。
- 增强 JSONL 读取校验：
  - 空行会跳过。
  - JSON 格式错误会提示具体行号。
  - 缺少 `question` 或 `expected_tool` 会抛出 `ValueError`。
- 补充评估结果结构：
  - `mode`
  - `total_cases`
  - `correct`
  - `accuracy`
  - `failed_cases`
  - `case_results`
- 增强测试覆盖，确保 `rule` 模式不调用真实 LLM，`llm` 模式通过 mock 验证，不依赖真实 API Key。

当日核心产出：

- `scripts/evaluate_tool_choice.py`
- `tests/test_evaluate_tool_choice.py`
- `README.md`

当日技术点：

- 使用 `argparse` 给脚本增加 CLI 参数。
- 用 mock / monkeypatch 测试 LLM 分支，避免测试联网或依赖 API Key。
- 把逐条评估结果保存为结构化 JSON，方便后续比较 rule 和 LLM 的稳定性。

阶段价值：

- V0.3 让项目具备了评估 Agent 工具选择稳定性的基础框架。
- `rule` 模式可以作为确定性 baseline。
- `llm` 模式可以作为后续模型效果观察入口，但不会影响默认本地测试稳定性。

### 2026-05-16：V0.4 工具选择评估集扩充与模式对比

目标：把项目从“能评估单一模式工具选择”升级为“能扩充评估集，并对比 rule 模式和 llm 模式的工具选择效果”。

完成内容：

- 扩充 `eval/tool_choice_cases.jsonl`：
  - 从 16 条扩充到 50 条。
  - 覆盖 `profile_csv`、`missing_value_analysis`、`numeric_summary`、`answer_data_question`、`generate_report`。
  - 加入更真实和容易混淆的问题表达。
- 新增 `scripts/compare_tool_choice_modes.py`：
  - 支持 `--cases` 指定评估集。
  - 支持 `--run-llm` 显式运行 LLM 模式。
  - 支持 `--verbose` 查看差异样例。
  - 支持 `--output` 保存 JSON 对比结果。
- 默认 compare 脚本只运行 `rule`，不会调用真实 LLM。
- `--run-llm` 分支复用 V0.3 已有的 `evaluate_tool_choice()`，不重复实现评估逻辑。
- 新增 `tests/test_compare_tool_choice_modes.py`，通过 mock 验证 LLM 对比逻辑，不依赖真实 API Key。
- 补充 `profile_csv` 的规则版路径识别，让包含 `data/sample_sales.csv` 的本地 CSV 画像 case 可以进入对应工具。

当日核心产出：

- `app/services/agent_service.py`
- `eval/tool_choice_cases.jsonl`
- `scripts/compare_tool_choice_modes.py`
- `tests/test_compare_tool_choice_modes.py`
- `README.md`

当日技术点：

- 评估集不只看高分，也要覆盖真实表达和容易混淆的问题。
- 对比报告需要同时保留两种模式的整体指标、失败样例和差异样例。
- 默认路径必须安全：不加 `--run-llm` 时不能调用真实 LLM。
- 测试 LLM 分支时使用 monkeypatch/mock，避免联网和 API Key 依赖。

阶段价值：

- V0.4 让项目不仅能“调用工具”，还能评估 Agent 工具选择效果。
- rule 模式可以作为 baseline，llm 模式可以作为后续模型能力对比入口。
- 差异样例可以指导下一步优化规则、prompt 或工具边界。

### 2026-05-17：V0.5 工具选择分类评估与失败分析

目标：把工具选择评估从“只看总体准确率”升级为“按问题类型统计准确率，并输出失败样例分析”。

完成内容：

- 给 `eval/tool_choice_cases.jsonl` 的 50 条 case 增加 `category` 字段。
- 新增固定 category 集合：
  - `profile_overview`
  - `missing_value`
  - `numeric_summary`
  - `report_generation`
  - `data_question`
  - `ambiguous_intent`
- 增强 `scripts/evaluate_tool_choice.py`：
  - `load_cases()` 校验 `category` 是否存在、是否为空、是否属于允许值。
  - `case_results` 和 `failed_cases` 中保留 `category`。
  - 新增 `category_metrics`。
  - 新增 `failure_analysis`。
- 增强 `scripts/compare_tool_choice_modes.py`：
  - 差异样例中保留 `category`。
  - 新增 `category_comparison`。
  - 默认不运行 LLM 时，`category_comparison` 标记为 `skipped`。
- 扩展测试覆盖，确保分类统计、失败分析、compare 输出和 JSON 输出都可验证。

当日核心产出：

- `eval/tool_choice_cases.jsonl`
- `scripts/evaluate_tool_choice.py`
- `scripts/compare_tool_choice_modes.py`
- `tests/test_evaluate_tool_choice.py`
- `tests/test_compare_tool_choice_modes.py`
- `README.md`

当日技术点：

- 评估结果不能只看总分，还需要按问题类型拆开看。
- 失败分析先用确定性统计完成，不调用 LLM，保证本地可重复。
- 默认路径继续保持安全：不加 `--run-llm` 时不调用真实 LLM。

阶段价值：

- V0.5 可以看出 rule baseline 的弱点主要集中在 `ambiguous_intent`。
- 后续优化规则、prompt 或工具边界时，可以优先处理失败分布最集中的问题类型。

### 2026-05-17：V0.6 基于失败分析优化规则选择

目标：基于 V0.5 的 `failure_analysis` 优化 rule 模式下的工具选择逻辑，并记录优化前后的指标变化。

完成内容：

- 保存 V0.5 rule baseline：

```text
eval/history/v0.5_rule_result.json
```

- 分析 V0.5 的 12 条失败样例：
  - `ambiguous_intent` 中 8 条失败，主要是“数据完整性、字段质量、整体表现、分析总结”等表达。
  - `report_generation` 中 3 条失败，主要是“汇报材料、复盘、周报内容”等没有直接出现“报告”的表达。
  - `missing_value_analysis` 期望工具有 5 条失败，主要是没有命中“缺失/空值”显式关键词。
  - `numeric_summary` 期望工具有 3 条失败，主要是“销售额/利润整体表现、数字范围、连续型字段”等表达。
  - `generate_report` 期望工具有 4 条失败，主要是“总结/汇报/复盘/周报”这类报告意图。
- 优化 `app/services/agent_service.py` 中的 `choose_tool_by_rules()`：
  - 扩展报告生成关键词。
  - 扩展缺失值分析关键词。
  - 扩展数值摘要关键词。
  - 保持默认不调用 LLM。
- 新增评估版本对比脚本：

```text
scripts/compare_eval_versions.py
```

- 新增 V0.6 结果和对比结果：

```text
eval/history/v0.6_rule_result.json
eval/history/v0.5_vs_v0.6_rule_compare.json
```

- 增强测试：
  - 覆盖新增版本对比脚本。
  - 覆盖规则选择的代表性问题。

当日核心产出：

- `app/services/agent_service.py`
- `scripts/compare_eval_versions.py`
- `tests/test_compare_eval_versions.py`
- `tests/test_tools_agent.py`
- `eval/history/v0.5_rule_result.json`
- `eval/history/v0.6_rule_result.json`
- `eval/history/v0.5_vs_v0.6_rule_compare.json`
- `README.md`

当日技术点：

- 用历史 JSON 结果做版本对比，而不是凭印象判断优化效果。
- `improved_cases` 表示优化前错误、优化后正确。
- `regressed_cases` 表示优化前正确、优化后错误。
- 规则优化要优先解决失败分布最集中的类别，同时检查是否引入退化。

阶段价值：

- V0.6 把 V0.5 的失败分析转化成了可验证的规则优化。
- 工具选择评估从“发现问题”进一步推进到“量化改进”。
- 后续每次修改规则或 prompt 都可以复用版本对比脚本验证收益和退化。

### 2026-05-17：V0.7 Hard Cases 与回归评估集

目标：验证 V0.6 rule 规则是否过拟合原始 50 条 case，并建立更可信的评估体系。

完成内容：

- 保留原始基础评估集：

```text
eval/tool_choice_cases.jsonl
```

- 给基础评估集 50 条 case 增加 `subcategory` 字段。
- 新增 hard 评估集：

```text
eval/tool_choice_hard_cases.jsonl
```

- 新增 regression 评估集：

```text
eval/tool_choice_regression_cases.jsonl
```

- 增强 `scripts/evaluate_tool_choice.py`：
  - `load_cases()` 校验 `subcategory`。
  - `case_results` 和 `failed_cases` 中保留 `subcategory`。
  - 新增 `subcategory_metrics`。
  - `failure_analysis` 新增 `failed_by_subcategory`。
- 新增 `tests/test_eval_case_schema.py`，直接校验三个 JSONL 文件的 schema。
- 保存 V0.7 三类评估结果：

```text
eval/history/v0.7_base_rule_result.json
eval/history/v0.7_hard_rule_result.json
eval/history/v0.7_regression_rule_result.json
```

真实运行结果：

```text
base: 50/50, accuracy=1.0000
hard: 17/32, accuracy=0.5312
regression: 15/15, accuracy=1.0000
```

hard cases 失败最多的类型：

```text
category:
  profile_overview: 4
  ambiguous_intent: 4

subcategory:
  ambiguous_overview: 3
  missing_vs_qa: 3
  numeric_vs_business_question: 3
```

当日核心产出：

- `eval/tool_choice_cases.jsonl`
- `eval/tool_choice_hard_cases.jsonl`
- `eval/tool_choice_regression_cases.jsonl`
- `eval/history/v0.7_base_rule_result.json`
- `eval/history/v0.7_hard_rule_result.json`
- `eval/history/v0.7_regression_rule_result.json`
- `scripts/evaluate_tool_choice.py`
- `scripts/compare_tool_choice_modes.py`
- `scripts/compare_eval_versions.py`
- `tests/test_eval_case_schema.py`
- `README.md`

当日技术点：

- 评估集需要分层：基础集看主流程稳定性，hard 集看开放表达边界，regression 集防止规则退化。
- hard cases 准确率低不是问题，它的价值是暴露下一轮优化方向。
- `subcategory` 可以帮助进一步定位具体混淆类型。

阶段价值：

- V0.7 证明 V0.6 在基础集满分，但在更开放表达下仍有明显边界。
- 项目评估体系从“单一准确率”升级为“基础评估 + hard 评估 + 回归保护”。
