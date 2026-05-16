# DataInsight-Agent 项目复盘材料

## 1. 项目名称

DataInsight-Agent：轻量级 CSV 数据分析 Agent 系统。

## 2. 项目解决什么问题

很多业务人员或数据分析初学者拿到 CSV 后，需要先做基础了解：有多少行列、有哪些字段、有没有缺失值、数值列分布如何、能不能快速生成一份分析报告。

这个项目把这些固定分析流程封装成后端服务，并用一个轻量 Agent 根据用户问题选择工具执行，返回结构化结果和工具调用轨迹。

## 3. 目标用户是谁

- 数据分析初学者：快速理解 CSV 数据。
- 业务人员：上传表格后获得基础分析结果。
- 面试展示场景：展示 FastAPI、pandas、pytest、Agent Tool Calling 的工程能力。
- 后续可扩展给内部运营、销售、报表分析场景。

## 4. 核心业务流程

```text
用户上传 CSV
-> FastAPI 接收文件
-> pandas 读取为 DataFrame
-> 生成数据画像 profile
-> 创建 session_id 并缓存 profile
-> 用户围绕数据提问
-> 后端通过 session_id 找到 profile
-> Agent 根据问题选择工具
-> 工具执行
-> 返回 answer / result / tool_trace
-> 可生成 Markdown 分析报告
```

当前核心接口：

- `POST /profile/upload`
- `POST /chat/data`
- `POST /report/generate`
- `GET /health`

## 5. 系统架构

```text
app/main.py
-> API 接口层

app/services/data_profile.py
-> CSV 读取与数据画像

app/services/tools.py
-> 工具函数 + 工具注册表

app/services/agent_service.py
-> Agent 工具选择、调用、轨迹记录、异常处理

app/services/report_service.py
-> Markdown 报告生成

app/services/session_store.py
-> session_id 内存会话缓存

tests/
-> pytest 自动化测试
```

业务核心逻辑主要在 `app/services/`。

FastAPI 的接口声明、Pydantic 请求模型、pytest 测试函数属于框架固定写法。

## 6. 主要模块说明

### `app/main.py`

输入：HTTP 请求，例如上传文件、用户问题、profile。

输出：JSON 响应。

执行流程：

```text
定义 FastAPI app
-> 接收请求
-> 调用 service 层函数
-> 返回 JSON 结果
```

### `app/services/data_profile.py`

输入：CSV 文件路径或 pandas DataFrame。

输出：结构化 profile。

执行流程：

```text
读取 CSV
-> 统计行列、字段、字段类型
-> 统计缺失值
-> 统计数值列摘要
-> 统计类别列高频值
-> 返回前几行预览
```

### `app/services/tools.py`

输入：工具名和参数。

输出：工具执行结果。

执行流程：

```text
定义工具函数
-> 用 TOOL_REGISTRY 注册工具
-> Agent 根据 tool_name 查找工具
-> call_tool 执行工具 callable
```

### `app/services/agent_service.py`

输入：用户问题、profile、可选 LLM JSON 工具选择结果。

输出：`answer`、`tool_name`、`result`、`tool_trace`。

执行流程：

```text
选择工具
-> 补齐工具参数
-> 调用工具
-> 记录成功或失败轨迹
-> 返回结构化结果
```

### `app/services/report_service.py`

输入：profile、可选 insights、可选 tool_trace。

输出：Markdown 字符串。

执行流程：

```text
读取 profile 关键字段
-> 拼接报告章节
-> 加入分析建议
-> 可选加入工具调用轨迹
-> 返回 Markdown
```

### `app/services/session_store.py`

输入：上传 CSV 后生成的 profile，或用户后续请求传入的 session_id。

输出：`session_id` 或对应的 profile。

执行流程：

```text
create_session(profile)
-> 使用 uuid4 生成 session_id
-> 把 session_id 和 profile 存入内存字典
-> /chat/data 根据 session_id 调用 get_profile
-> 找到 profile 后继续走 Agent 工具调用流程
```

当前使用内存字典是为了让 MVP 先跑通“上传一次，后续用 session_id 提问”的流程，不引入数据库或 Redis。

## 7. Agent 工具调用流程

当前是规则版轻量 Agent，不依赖 LangChain / LangGraph。

执行流程：

```text
用户上传 CSV 得到 session_id
-> /chat/data 提交 question + session_id
-> 后端从 session_store 取出 profile
-> run_agent(question, profile)
-> choose_tool_by_rules(question)
-> get_tool(tool_name)
-> call_tool(tool_name, arguments)
-> build_trace(...)
-> 返回结构化结果
```

规则示例：

- 问题包含“缺失、空值、null”：调用 `missing_value_analysis`。
- 问题包含“平均、最大、最小、数值、中位、标准差”：调用 `numeric_summary`。
- 问题包含“报告、Markdown”：调用 `generate_report`。
- 其他问题：调用 `answer_data_question`。

## 7.1 session_id 内存会话缓存机制

### 这个模块解决什么问题

在早期版本中，`/chat/data` 需要调用方每次手动传入完整的 `profile`。这虽然简单，但接口使用体验不好：

```text
用户上传 CSV 得到 profile
-> 每次提问都要把完整 profile 再传一遍
```

session_id 内存会话缓存机制解决的是“上传 CSV 之后如何在后续问答中复用 profile”的问题。

新的流程是：

```text
用户上传 CSV
-> 后端生成 profile
-> 后端创建 session_id
-> 返回 session_id
-> 用户后续只传 question + session_id
-> 后端自动找到 profile
-> 调用 Agent 回答问题
```

### 输入是什么

`create_session(profile)` 的输入：

- `profile: dict`：CSV 上传后生成的数据画像。

`get_profile(session_id)` 的输入：

- `session_id: str`：上传 CSV 时返回的会话 ID。

`delete_session(session_id)` 的输入：

- `session_id: str`：需要删除的会话 ID。

`/chat/data` 的新请求方式：

```json
{
  "question": "哪些字段有缺失值？",
  "session_id": "上传 CSV 后返回的 session_id"
}
```

旧请求方式仍然兼容：

```json
{
  "question": "哪些字段有缺失值？",
  "profile": {
    "shape": {
      "rows": 5,
      "columns": 5
    }
  }
}
```

### 输出是什么

`create_session(profile)` 输出：

```text
session_id 字符串
```

`get_profile(session_id)` 输出：

```text
找到时返回 profile 字典
找不到时返回 None
```

`delete_session(session_id)` 输出：

```text
删除成功返回 True
session_id 不存在返回 False
```

`/profile/upload` 返回中新增：

```json
{
  "session_id": "7f4c2d2a-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "filename": "sample_sales.csv",
  "shape": {
    "rows": 5,
    "columns": 5
  }
}
```

### 核心执行流程

上传阶段：

```text
/profile/upload
-> pandas 读取 CSV
-> profile_dataframe(df) 生成 profile
-> 整理 response_data
-> create_session(response_data)
-> response_data 增加 session_id
-> 返回给用户
```

问答阶段：

```text
/chat/data
-> 如果请求体有 session_id
-> get_profile(session_id)
-> 找不到则返回 404
-> 找到则调用 run_agent(question, profile)
```

兼容旧方式：

```text
/chat/data
-> 如果没有 session_id，但有 profile
-> 直接调用 run_agent(question, profile)
```

错误处理：

```text
/chat/data
-> 如果 session_id 和 profile 都没有
-> 返回 400
```

### 关键代码解释

核心文件：

```text
app/services/session_store.py
```

核心结构：

```python
_SESSION_PROFILES: dict[str, dict] = {}
```

这里用全局字典保存 `session_id -> profile` 的映射。

创建 session：

```python
def create_session(profile: dict) -> str:
    session_id = str(uuid4())
    _SESSION_PROFILES[session_id] = profile
    return session_id
```

关键点：

- `uuid4()` 用于生成随机、不容易重复的 session_id。
- profile 保存在内存字典里。
- 返回 session_id 给接口层。

读取 profile：

```python
def get_profile(session_id: str) -> dict | None:
    return _SESSION_PROFILES.get(session_id)
```

关键点：

- 找到就返回 profile。
- 找不到返回 `None`，由接口层转换成 404。

接口层逻辑：

```python
if request.session_id:
    profile = get_profile(request.session_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Session not found")
elif request.profile:
    profile = request.profile
else:
    raise HTTPException(
        status_code=400,
        detail="Either session_id or profile is required",
    )
```

这段代码同时支持新旧两种调用方式。

### 哪些地方是必须理解的核心逻辑

- 上传 CSV 后，后端不仅返回 profile，还把 profile 缓存在 session_store 中。
- `session_id` 是后续问答找到 profile 的索引。
- `/chat/data` 优先使用 `session_id`，没有 `session_id` 时才使用旧的 `profile` 方式。
- session 不存在时返回 404，不应该让 Agent 继续执行。
- session_id 和 profile 都没有时返回 400，因为请求缺少必要上下文。

### 哪些地方是框架/库的固定写法

- `uuid4()`：Python 标准库生成随机 UUID 的固定写法。
- `dict.get(key)`：从字典中安全读取值，找不到返回 `None`。
- `BaseModel`：Pydantic 请求模型写法。
- `HTTPException(status_code=..., detail=...)`：FastAPI 返回错误状态码的固定写法。

### 我为什么这样设计

当前阶段不引入数据库、Redis、LangChain 或 LangGraph，原因是项目目标是先完成一个可运行、可测试、可面试讲解的 MVP。

内存字典方案的优点：

- 实现简单。
- 不增加依赖。
- 测试容易写。
- 能清楚展示 session_id 的基本思想。
- 后续可以平滑替换为 Redis、SQLite 或 PostgreSQL。

同时保留旧的 `question + profile` 方式，是为了向后兼容已有调用方式和测试。

### 可能出现的错误和异常情况

`session_id` 不存在：

```text
返回 404
detail: Session not found
```

请求中既没有 `session_id`，也没有 `profile`：

```text
返回 400
detail: Either session_id or profile is required
```

服务重启：

```text
内存字典被清空，原来的 session_id 会失效
```

多进程部署：

```text
不同进程有不同内存，session_id 可能只在某一个进程中存在
```

长期运行：

```text
当前没有过期时间，session 可能持续占用内存
```

### 如何测试这个模块是否正常

测试文件：

```text
tests/test_session_chat.py
tests/test_profile_upload.py
```

测试场景：

- 上传 CSV 后返回 `session_id`。
- `session_id` 是非空字符串。
- 原有 profile 字段仍然存在。
- 使用 `question + session_id` 调用 `/chat/data` 能正常选择 `missing_value_analysis`。
- 不存在的 `session_id` 返回 404。
- 旧的 `question + profile` 方式仍然可用。
- `session_id` 和 `profile` 都不传时返回 400。

运行命令：

```bash
.venv/bin/pytest
```

### 如果让我手写一个简化版，我会怎么写

```python
from uuid import uuid4

sessions = {}


def create_session(profile):
    session_id = str(uuid4())
    sessions[session_id] = profile
    return session_id


def get_profile(session_id):
    return sessions.get(session_id)


def delete_session(session_id):
    if session_id not in sessions:
        return False
    del sessions[session_id]
    return True
```

接口中使用：

```python
if session_id:
    profile = get_profile(session_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Session not found")
elif profile:
    pass
else:
    raise HTTPException(status_code=400, detail="Either session_id or profile is required")
```

### 面试官可能追问的问题

为什么不用数据库或 Redis？

回答思路：

当前是 MVP 和面试展示阶段，内存字典足够验证 session_id 流程，而且没有额外部署成本。生产环境会替换成 Redis 或数据库。

内存 session 有什么问题？

回答思路：

服务重启会丢失，多进程不共享，没有 TTL，也不能持久化历史记录。

为什么还保留直接传 profile 的旧方式？

回答思路：

这是为了向后兼容已有接口和测试，也方便调试 Agent。新方式推荐用 session_id，旧方式作为兼容入口。

如果换成 Redis 怎么改？

回答思路：

保留 `create_session/get_profile/delete_session` 这三个函数签名不变，把内部的全局字典替换成 Redis 的 `set/get/delete`，并给 session 设置 TTL。

如果换成数据库怎么改？

回答思路：

新增 session 表，字段可以包括 `session_id`、`profile_json`、`created_at`、`updated_at`。接口层不用大改，只替换 session_store 的内部实现。

## 8. 工具注册表为什么这样设计

工具注册表在 `tools.py` 中是 `TOOL_REGISTRY`。

每个工具包含：

- `name`
- `description`
- `parameters`
- `callable`

这样设计的原因：

- Agent 不需要知道具体函数在哪里，只需要根据 `tool_name` 查表调用。
- 工具描述和参数集中维护，后续可以给 LLM 做工具选择提示词。
- 新增工具时只需要新增函数并注册，不需要大改 Agent 主流程。
- 这模拟了真实 Agent 的 Tool Calling 思路，但实现保持简单。

业务核心逻辑：工具抽象、注册、查找、调用。

固定写法：Python `dataclass`、字典存储函数引用。

## 9. CSV 数据画像模块如何实现

核心文件：`app/services/data_profile.py`

核心函数：

```python
profile_dataframe(df)
analyze_csv(file_path)
```

输入：

- `profile_dataframe(df)` 输入 pandas DataFrame。
- `analyze_csv(file_path)` 输入本地 CSV 路径。

输出：

```json
{
  "rows": 5,
  "columns": 5,
  "column_names": [],
  "dtypes": {},
  "missing_values": {},
  "missing_rate": {},
  "numeric_summary": {},
  "categorical_summary": {},
  "preview": []
}
```

执行流程：

```text
读取 DataFrame shape
-> 获取字段名
-> 统计 dtype
-> df.isna().sum() 统计缺失值
-> select_dtypes(include="number") 找数值列
-> 计算 count / mean / min / max / median / std
-> select_dtypes(exclude="number") 找类别列
-> value_counts().head(5) 统计高频值
-> df.head(5) 生成预览
```

pandas 固定写法：

- `df.shape`
- `df.dtypes`
- `df.isna()`
- `select_dtypes()`

业务核心逻辑：

- 决定返回哪些画像字段。
- 把 pandas 统计结果组织成稳定 JSON。
- 为后续 Agent 工具和报告生成提供统一 profile。

## 10. 缺失值分析如何实现

核心函数：`missing_value_analysis(profile)`

输入：`/profile/upload` 返回的 profile。

输出：

```json
{
  "summary": "共有 1 个字段存在缺失值，缺失单元格总数为 1。",
  "total_missing": 1,
  "columns_with_missing": [],
  "missing_values": {},
  "missing_rate": {}
}
```

执行流程：

```text
读取 profile["missing_values"]
-> 计算 total_missing
-> 过滤 count > 0 的字段
-> 拼接 summary
-> 返回结构化结果
```

业务核心逻辑：从画像结果中提炼“哪些字段需要关注”。

固定写法：遍历 dict、列表推导式。

## 11. 数值摘要如何实现

核心函数：`numeric_summary(profile)`

输入：profile。

输出：

```json
{
  "summary": "识别到 2 个数值列...",
  "numeric_summary": {
    "sales": {
      "count": 4,
      "mean": 1650.0,
      "min": 1200.0,
      "max": 2100.0,
      "median": 1650.0,
      "std": 387.2983
    }
  }
}
```

执行流程：

```text
profile_dataframe 阶段先统计 numeric_summary
-> numeric_summary 工具读取该字段
-> 如果没有数值列，返回明确说明
-> 如果有数值列，返回摘要和原始统计结构
```

pandas 固定写法：

- `mean()`
- `min()`
- `max()`
- `median()`
- `std()`

业务核心逻辑：把数值字段摘要作为 Agent 可调用工具输出。

## 12. 报告生成如何实现

核心文件：`app/services/report_service.py`

核心函数：

```python
generate_markdown_report(profile, insights=None, tool_trace=None)
```

输入：

- profile
- 可选 LLM 或规则分析建议
- 可选工具调用轨迹

输出：Markdown 字符串。

报告章节：

```text
# CSV 数据分析报告
## 数据概览
## 缺失值分析
## 数值列摘要
## 类别字段摘要
## 分析建议
## 工具调用轨迹
```

执行流程：

```text
读取 profile 中的 shape / columns / missing / numeric / categorical
-> 用字符串列表 lines 拼接 Markdown
-> 如果传入 tool_trace，则追加工具调用轨迹
-> "\n".join(lines) 返回报告
```

业务核心逻辑：报告结构设计。

固定写法：字符串拼接和列表 append。

## 13. 工具调用轨迹如何记录

核心函数：`build_trace(...)`

成功时记录：

```json
{
  "tool_name": "missing_value_analysis",
  "arguments": {},
  "status": "success",
  "result_summary": "...",
  "timestamp": "..."
}
```

失败时记录：

```json
{
  "tool_name": "unknown",
  "arguments": {},
  "status": "failed",
  "error_message": "...",
  "timestamp": "..."
}
```

执行流程：

```text
Agent 确定工具名和参数
-> 调用工具
-> 成功：记录 result_summary
-> 失败：记录 error_message
-> timestamp 使用 UTC 时间
```

设计重点：轨迹让 Agent 不再是黑盒，面试时可以清楚解释“系统为什么调用这个工具”。

## 14. 工具选择评估集与评估脚本

### 1. 这个模块解决什么问题

Agent 项目不能只停留在“能调用工具”，还需要回答一个更关键的问题：

```text
用户提出一个问题时，Agent 选的工具是否正确？
```

工具选择评估集与评估脚本解决的是“如何用一批固定问题，评估 Agent 工具选择准确率”的问题。

当前项目已经有规则版工具选择逻辑：

```text
choose_tool_by_rules(question)
```

但如果没有评估集，就只能靠手动试几个问题，很难说明工具选择是否稳定。评估集可以让项目具备可量化的 Agent 评估能力。

当前先评估规则版工具选择，原因是：

- 规则版不依赖 LLM，不会受网络、API Key 或模型随机性的影响。
- 可以先建立稳定 baseline。
- 后续接入 LLM 工具选择后，可以和规则版 baseline 对比。
- 规则版结果可复现，适合写自动化测试。

### 2. 输入是什么

评估数据文件：

```text
eval/tool_choice_cases.jsonl
```

每一行是一个 JSON：

```json
{"question": "哪些字段有缺失值？", "expected_tool": "missing_value_analysis"}
```

字段说明：

- `question`：用户问题。
- `expected_tool`：期望 Agent 选择的工具名。

当前评估集包含 16 条样例，覆盖 4 类工具：

- `missing_value_analysis`
- `numeric_summary`
- `generate_report`
- `answer_data_question`

评估函数还需要一个固定的 sample profile，用来模拟用户已经上传 CSV 后生成的数据画像。

### 3. 输出是什么

评估脚本输出：

```text
Tool choice evaluation
total_cases: 16
correct: 16
accuracy: 1.0000

Failed cases:
- none
```

评估函数返回结构：

```json
{
  "total_cases": 16,
  "correct": 16,
  "accuracy": 1.0,
  "failed_cases": []
}
```

字段含义：

- `total_cases`：评估样例总数。
- `correct`：实际工具和期望工具一致的数量。
- `accuracy`：工具选择准确率。
- `failed_cases`：选择失败的案例列表。

准确率计算公式：

```text
accuracy = correct / total_cases
```

### 4. 核心执行流程

命令行运行：

```bash
python scripts/evaluate_tool_choice.py
```

执行流程：

```text
读取 eval/tool_choice_cases.jsonl
-> 构造 sample_profile
-> 遍历每条 case
-> 调用 run_agent(question, profile, use_llm_tool_choice=False)
-> 读取实际 tool_name
-> 和 expected_tool 对比
-> 统计 total_cases / correct / accuracy / failed_cases
-> 打印评估结果
```

当前明确使用：

```python
use_llm_tool_choice=False
```

所以评估的是规则版工具选择，不会真实调用智谱 API。

### 5. 关键代码解释

核心脚本：

```text
scripts/evaluate_tool_choice.py
```

读取评估集：

```python
def load_cases(path) -> list[dict]:
    cases = []
    with Path(path).open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            line = line.strip()
            if not line:
                continue

            case = json.loads(line)
            if "question" not in case or "expected_tool" not in case:
                raise ValueError(...)
            cases.append(case)
    return cases
```

关键点：

- JSONL 一行一个样例，方便持续追加。
- 每条样例必须包含 `question` 和 `expected_tool`。
- 读取阶段就做基础校验，避免评估结果不可信。

构造固定 profile：

```python
def sample_profile() -> dict:
    return {
        "shape": {"rows": 5, "columns": 5},
        "columns": ["date", "product", "region", "sales", "profit"],
        "missing_values": {...},
        "numeric_summary": {...}
    }
```

关键点：

- 不依赖真实上传接口。
- 不依赖外部 API。
- 保证评估可重复运行。

读取实际工具名：

```python
def _actual_tool_name(agent_response: dict) -> str | None:
    if agent_response.get("tool_name"):
        return agent_response["tool_name"]

    tool_trace = agent_response.get("tool_trace", [])
    if tool_trace:
        return tool_trace[-1].get("tool_name")

    return None
```

关键点：

- 优先读取 `response["tool_name"]`。
- 如果没有，再从 `tool_trace` 兜底读取。
- 这样对 Agent 返回结构更稳。

评估函数：

```python
def evaluate_tool_choice(cases, profile) -> dict:
    failed_cases = []
    correct = 0

    for case in cases:
        response = run_agent(
            question=case["question"],
            profile=profile,
            use_llm_tool_choice=False,
        )
        actual_tool = _actual_tool_name(response)
        expected_tool = case["expected_tool"]

        if actual_tool == expected_tool:
            correct += 1
        else:
            failed_cases.append(...)

    accuracy = correct / total_cases if total_cases else 0.0
```

关键点：

- 每条 case 都走真实 `run_agent`。
- 当前不调用 LLM。
- 失败案例会保留 question、expected_tool、actual_tool。

### 6. 哪些地方是必须理解的核心逻辑

- Agent 项目需要评估集，因为工具选择是否正确必须可量化。
- 每条评估样例由 `question` 和 `expected_tool` 组成。
- `run_agent` 是真实被评估对象。
- 当前使用 `use_llm_tool_choice=False`，所以评估的是规则版 baseline。
- `accuracy = correct / total_cases`。
- `failed_cases` 是后续优化规则、prompt 或工具描述的重要依据。
- 当前准确率 `1.0000` 只说明这 16 条固定样例全部选对，不代表真实用户问题永远满分。

### 7. 哪些地方是框架/库的固定写法

- `json.loads(line)`：解析 JSON 字符串。
- `Path(...).open(..., encoding="utf-8")`：读取 UTF-8 文件。
- `if __name__ == "__main__": main()`：让脚本既能被导入测试，也能命令行运行。
- pytest 中用 `assert` 验证结果字段和 accuracy 范围。
- JSONL 格式本身是一种常见评估数据组织方式。

### 8. 我为什么这样设计

我没有引入复杂评估框架，而是用 JSONL + Python 脚本，是因为当前阶段的目标是轻量、可读、可运行。

这样设计的好处：

- 学习成本低。
- 评估数据容易追加。
- 评估逻辑能被 pytest 直接导入测试。
- 不依赖 LLM，不依赖网络。
- 可以先形成规则版 baseline。
- 后续扩展到 LLM 工具选择评估时，不需要重写整个评估流程。

为什么先评估规则版：

- 规则版是当前最稳定的工具选择方式。
- 它能作为 LLM 工具选择的对照组。
- 如果规则版在固定样例上都选不准，就不应该急着评估 LLM。

### 9. 可能出现的错误和异常情况

JSONL 中某一行不是合法 JSON：

```text
json.loads 会抛出 JSONDecodeError
```

某条 case 缺少字段：

```text
load_cases 会抛出 ValueError
```

`expected_tool` 写错：

```text
评估结果会出现 failed_cases
```

问题表达超出规则覆盖范围：

```text
规则版可能选择 answer_data_question，导致准确率下降
```

Agent 返回结构变化：

```text
_actual_tool_name 先读 tool_name，再从 tool_trace 兜底，降低结构变化带来的风险
```

### 10. 如何测试这个模块是否正常

测试文件：

```text
tests/test_evaluate_tool_choice.py
```

测试内容：

- 可以读取 `eval/tool_choice_cases.jsonl`。
- 每条样例都有 `question` 和 `expected_tool`。
- `evaluate_tool_choice` 返回 `total_cases`、`correct`、`accuracy`、`failed_cases`。
- `accuracy` 在 0 到 1 之间。
- 默认评估文件路径存在。

运行测试：

```bash
.venv/bin/pytest
```

单独运行评估：

```bash
.venv/bin/python scripts/evaluate_tool_choice.py
```

当前评估结果：

```text
total_cases: 16
correct: 16
accuracy: 1.0000
```

### 11. 如果让我手写一个简化版，我会怎么写

```python
import json

from app.services.agent_service import run_agent


def load_cases(path):
    cases = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            cases.append(json.loads(line))
    return cases


def evaluate(cases, profile):
    correct = 0
    failed = []

    for case in cases:
        response = run_agent(
            question=case["question"],
            profile=profile,
            use_llm_tool_choice=False,
        )
        actual = response.get("tool_name")
        expected = case["expected_tool"]

        if actual == expected:
            correct += 1
        else:
            failed.append({
                "question": case["question"],
                "expected_tool": expected,
                "actual_tool": actual,
            })

    total = len(cases)
    return {
        "total_cases": total,
        "correct": correct,
        "accuracy": correct / total if total else 0,
        "failed_cases": failed,
    }
```

### 12. 面试官可能追问的问题

为什么 Agent 项目需要评估集？

回答思路：

Agent 的关键能力不是“能不能调用工具”，而是“面对不同问题能不能选对工具”。评估集可以把这个能力量化，避免只靠手动演示。

为什么当前准确率是 1.0000？

回答思路：

因为当前 16 条样例是围绕现有规则设计的固定样例，规则关键词覆盖得比较明确。这只代表当前评估集全对，不代表真实用户问题永远满分。

`failed_cases` 有什么价值？

回答思路：

它能告诉我哪些问题没有选对工具。后续可以根据失败案例优化规则、改写工具描述、调整 LLM prompt 或补充新工具。

为什么先评估规则版，不直接评估 LLM？

回答思路：

规则版稳定、可复现、不依赖外部 API。先建立 baseline，再评估 LLM，可以知道 LLM 是否真的比规则更好。

后续如何扩展到 LLM 工具选择评估？

回答思路：

可以给 `evaluate_tool_choice` 增加参数 `use_llm_tool_choice=True`，调用同一批 case，统计 LLM 的工具选择准确率。同时记录 `fallback_used`、`fallback_reason` 和 `llm_choice_raw`。

后续还可以增加哪些指标？

回答思路：

可以增加：

- fallback 率
- JSON 解析失败率
- 工具不存在率
- 工具调用成功率
- 平均响应耗时
- 每个工具的单独准确率

## 15. 异常处理做了哪些

### CSV 上传接口

- 非 `.csv`：返回 400。
- 空文件：返回 400。
- pandas 解析失败：返回 400。
- 服务端处理异常：返回 500。

### 本地 CSV 分析

- 路径为空：`ValueError`。
- 文件不存在：`FileNotFoundError`。
- 路径不是文件：`ValueError`。
- 非 CSV：`ValueError`。
- 空 CSV / 解析失败 / 编码失败：转换成清晰错误。

### Agent

- 问题为空：返回失败轨迹。
- LLM 输出非法 JSON：返回失败轨迹。
- 工具不存在：返回失败轨迹。
- 参数缺失或错误：返回失败轨迹。
- 工具执行失败：返回失败轨迹。

## 16. 测试覆盖了哪些场景

当前测试命令：

```bash
.venv/bin/pytest
```

当前测试结果：

```text
28 passed
```

测试文件：

- `tests/test_profile_upload.py`
- `tests/test_data_profile.py`
- `tests/test_tools_agent.py`
- `tests/test_report_service.py`
- `tests/test_session_chat.py`
- `tests/test_evaluate_tool_choice.py`

覆盖场景：

- CSV 正常上传。
- 非 CSV 文件。
- 空 CSV 文件。
- 数据画像字段。
- 缺失值数量和缺失率。
- 数值摘要。
- 类别字段高频值。
- 工具注册表能找到工具。
- 工具不存在时抛错。
- Agent 完成一次工具调用闭环。
- Agent 处理非法 JSON。
- Markdown 报告包含核心章节。
- 上传 CSV 后返回 session_id。
- 使用 session_id 调用 `/chat/data`。
- session_id 不存在时返回 404。
- 旧的 question + profile 方式仍然可用。
- 工具选择评估集能正常读取。
- 工具选择评估函数能返回准确率和失败案例。
- 规则版工具选择评估脚本可运行。

pytest 固定写法：

- `assert`
- 测试函数命名
- 异常断言

业务核心测试：

- 验证画像、工具选择、工具执行、轨迹和报告结果是否符合预期。

## 17. 项目亮点

- 不是只调 LLM，而是先用 pandas 做确定性分析。
- Agent 工具调用流程清晰，有工具注册表和调用轨迹。
- 不引入重型框架，适合解释底层原理。
- 接口结构稳定，方便后续接前端或数据库。
- 测试覆盖了核心业务闭环。
- 新增工具选择评估脚本，可以量化 Agent 工具选择准确率。
- Markdown 报告能直接作为分析产物展示。

## 18. 项目不足

- 当前 session_store 使用内存字典，服务重启后 session 会丢失。
- 多进程或多实例部署时，内存 session 不共享。
- 当前 session 没有过期时间，也没有持久化历史记录。
- 工具选择默认是规则判断，不是真正由 LLM 自动决策。
- 当前评估集规模较小，16 条样例不能代表真实用户所有提问方式。
- `/chat` 的真实 LLM 调用没有测试覆盖。
- 没有数据库，无法保存上传历史和分析报告。
- 没有前端，主要通过 Swagger 或 API 调用展示。
- 当前报告是规则模板生成，智能分析深度有限。

## 19. 后续优化方向

优先级建议：

1. 将内存 session_store 升级为 Redis、SQLite 或 PostgreSQL。
2. 让 LLM 输出 JSON 工具选择结果，并用规则作为 fallback。
3. 扩展评估集，增加更多真实问题表达和每个工具的单独准确率。
4. 增加更多工具，例如异常值检测、字段相关性分析、分组统计。
5. 接入数据库保存分析记录。
6. 做一个极简前端或 Streamlit 展示页。
7. 增加 LLM 生成自然语言洞察的测试 mock。

## 20. 简历上可以怎么写

较完整版本：

```text
DataInsight-Agent：基于 FastAPI + pandas + pytest 实现的轻量级 CSV 数据分析 Agent。
支持 CSV 上传、session_id 会话缓存、数据画像、缺失值分析、数值摘要、规则版工具选择、
工具调用轨迹记录和 Markdown 报告生成。
设计了统一 Tool Registry，将数据分析能力封装为可调用工具，
并通过 pytest 覆盖上传、画像、工具调用、异常处理和报告生成等核心场景。
```

更短版本：

```text
实现一个轻量级 CSV 数据分析 Agent，使用 FastAPI 提供接口，
pandas 完成数据画像，内存 session_store 缓存上传后的 profile，Tool Registry 管理分析工具，
Agent 根据问题选择工具并记录调用轨迹，支持 Markdown 报告生成和 pytest 自动化测试。
```

## 21. 面试官可能追问的问题和回答思路

### Q1：为什么不用 LangChain / LangGraph？

回答思路：

当前项目目标是 MVP 和学习展示，我希望先把 Agent 的核心机制讲清楚：工具注册、工具选择、参数传递、执行和轨迹记录。重型框架会隐藏这些细节，所以先手写轻量版，后续可以平滑迁移。

### Q2：Agent 现在真的智能吗？

回答思路：

当前默认是规则版工具选择，保证稳定可测试；同时代码预留了 `llm_tool_choice_json`，可以接入 LLM 输出 `{tool_name, arguments}`。所以现在是“可解释、可测试的 Agent MVP”，不是复杂智能体。

### Q3：为什么先做 pandas 数据画像？

回答思路：

CSV 分析有很多确定性任务，例如行列数、缺失值、数值摘要，这些不需要 LLM。先用 pandas 保证结果准确，再让 LLM 做总结和建议，系统会更可靠。

### Q4：工具注册表有什么价值？

回答思路：

它把工具元信息和函数统一管理，Agent 只通过工具名调用能力。这样新增工具时不需要改主流程，也方便未来把工具描述交给 LLM 做函数选择。

### Q5：如何保证系统可测试？

回答思路：

把业务逻辑放在 service 层，接口层只负责接收请求和返回响应。这样 pytest 可以直接测试画像、工具、Agent 和报告，不依赖真实服务启动，也不依赖真实 LLM。

### Q6：工具调用轨迹有什么用？

回答思路：

它解决 Agent 黑盒问题。用户和开发者都能看到系统调用了哪个工具、传了什么参数、执行是否成功、结果摘要是什么。这对调试、评估和面试展示都很重要。

### Q7：后续如何接入真实 LLM 工具选择？

回答思路：

把 `TOOL_REGISTRY` 中的 `name`、`description`、`parameters` 组织成 prompt，让 LLM 输出 JSON。然后用当前 `parse_llm_tool_choice` 解析。如果 LLM 输出非法 JSON 或工具不存在，就走错误处理或规则 fallback。
