# DataInsight Agent

DataInsight Agent 是一个面向 CSV 文件的轻量级数据分析 Agent 后端项目。

项目当前已经实现：CSV 上传、基础数据画像、缺失值分析、数值列摘要、规则版工具选择、工具调用轨迹记录、Markdown 报告生成和 pytest 自动化测试。

当前项目不包含前端、数据库、RAG、多 Agent 编排，也没有把 LLM 接入到 Agent 工具选择主流程中。默认的数据问答流程使用规则判断选择工具，目的是让功能稳定、可测试、适合面试讲解。

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
│       └── tools.py
├── data/
│   └── sample_sales.csv
├── docs/
│   └── project_review.md
├── tests/
│   ├── test_data_profile.py
│   ├── test_profile_upload.py
│   ├── test_report_service.py
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
- `app/services/llm_service.py`：智谱 LLM 调用封装。
- `tests/`：pytest 测试。
- `docs/project_review.md`：面试复盘材料。

## Agent 工具调用流程

当前 Agent 是轻量规则版实现，不依赖 LangChain / LangGraph。

核心流程：

```text
用户提交 question 和 profile
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

当前项目没有会话存储，所以调用 `/chat/data` 时需要把 `/profile/upload` 返回的 profile 一起传入。

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
- Markdown 报告是否包含核心章节。

当前验证结果：

```text
14 passed
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
- 使用工具注册表管理 Agent 可调用能力，结构清晰，方便扩展。
- Agent 调用过程会记录工具轨迹，便于调试和面试讲解。
- 不引入 LangChain / LangGraph，代码更轻，适合说明 Tool Calling 原理。
- pytest 覆盖核心业务逻辑，不需要先启动服务也能验证主要功能。
- Markdown 报告可以作为直接展示的分析产物。

## 后续优化方向

- 增加 `session_id`，让上传后的 profile 可以在后续问答中复用。
- 让 LLM 基于 `TOOL_REGISTRY` 输出 JSON 工具选择结果，并用规则选择作为 fallback。
- 增加更多数据分析工具，例如异常值检测、相关性分析、分组统计。
- 增加基础评估集，评估工具选择准确率、报告完整性和异常处理能力。
- 接入数据库，保存上传记录、工具调用轨迹和报告。
- 增加极简前端或 Streamlit 页面，方便非技术用户演示。
- 对 `/chat` LLM 调用增加 mock 测试，避免测试依赖真实外部 API。

## 当前限制

- `/chat/data` 不保存会话状态，需要调用方传入 profile。
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
