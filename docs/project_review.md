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
-> 用户围绕数据提问
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

## 7. Agent 工具调用流程

当前是规则版轻量 Agent，不依赖 LangChain / LangGraph。

执行流程：

```text
run_agent(question, profile)
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

## 14. 异常处理做了哪些

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

## 15. 测试覆盖了哪些场景

当前测试命令：

```bash
.venv/bin/pytest
```

当前测试结果：

```text
14 passed
```

测试文件：

- `tests/test_profile_upload.py`
- `tests/test_data_profile.py`
- `tests/test_tools_agent.py`
- `tests/test_report_service.py`

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

pytest 固定写法：

- `assert`
- 测试函数命名
- 异常断言

业务核心测试：

- 验证画像、工具选择、工具执行、轨迹和报告结果是否符合预期。

## 16. 项目亮点

- 不是只调 LLM，而是先用 pandas 做确定性分析。
- Agent 工具调用流程清晰，有工具注册表和调用轨迹。
- 不引入重型框架，适合解释底层原理。
- 接口结构稳定，方便后续接前端或数据库。
- 测试覆盖了核心业务闭环。
- Markdown 报告能直接作为分析产物展示。

## 17. 项目不足

- 当前 `/chat/data` 不保存会话，需要调用方传入 profile。
- 工具选择默认是规则判断，不是真正由 LLM 自动决策。
- `/chat` 的真实 LLM 调用没有测试覆盖。
- 没有数据库，无法保存上传历史和分析报告。
- 没有前端，主要通过 Swagger 或 API 调用展示。
- 当前报告是规则模板生成，智能分析深度有限。

## 18. 后续优化方向

优先级建议：

1. 增加 `session_id`，上传 CSV 后缓存 profile。
2. 让 LLM 输出 JSON 工具选择结果，并用规则作为 fallback。
3. 增加评估集，测试工具选择准确率和报告完整性。
4. 增加更多工具，例如异常值检测、字段相关性分析、分组统计。
5. 接入数据库保存分析记录。
6. 做一个极简前端或 Streamlit 展示页。
7. 增加 LLM 生成自然语言洞察的测试 mock。

## 19. 简历上可以怎么写

较完整版本：

```text
DataInsight-Agent：基于 FastAPI + pandas + pytest 实现的轻量级 CSV 数据分析 Agent。
支持 CSV 上传、数据画像、缺失值分析、数值摘要、规则版工具选择、
工具调用轨迹记录和 Markdown 报告生成。
设计了统一 Tool Registry，将数据分析能力封装为可调用工具，
并通过 pytest 覆盖上传、画像、工具调用、异常处理和报告生成等核心场景。
```

更短版本：

```text
实现一个轻量级 CSV 数据分析 Agent，使用 FastAPI 提供接口，
pandas 完成数据画像，Tool Registry 管理分析工具，
Agent 根据问题选择工具并记录调用轨迹，支持 Markdown 报告生成和 pytest 自动化测试。
```

## 20. 面试官可能追问的问题和回答思路

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
