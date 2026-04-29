# Codex 工作说明

这个文件用于帮助后续启动的 Codex 快速理解 DataInsight-Agent 项目，并延续当前项目的开发方式和文档写作风格。

## 项目定位

DataInsight Agent 是一个用于求职展示的 AI 数据分析 Agent 项目。

当前项目不是一次性做完整复杂系统，而是按阶段推进：

```text
后端基础服务
-> CSV 数据读取
-> 数据画像
-> 上传接口
-> 异常处理
-> 自动化测试
-> README 复盘
-> 后续再扩展 LLM / Agent / RAG / 数据库 / 前端
```

项目当前重点是让每一步都清晰、可运行、可测试、适合复盘和面试展示。

## 当前开发边界

除非用户明确要求，当前阶段不要主动做这些事情：

- 不接入新的 LLM 功能
- 不接入 Agent 编排
- 不做 RAG
- 不做数据库
- 不做前端
- 不上 Docker
- 不引入复杂架构

优先做这些事情：

- 保持 FastAPI 后端代码清晰
- 保持 pandas 数据画像逻辑易懂
- 保持接口返回 JSON 结构稳定
- 保持异常处理明确
- 保持 pytest 测试可运行
- 保持 README 可复盘

## 代码风格要求

- 使用简单直接的 Python 写法。
- 不为了“高级”而过度封装。
- 新增函数时，函数名要能说明用途。
- 注释可以写中文，但要解释关键业务步骤，不要写废话。
- 保持适合 Python 基础水平的人学习。
- 不随意改动与当前任务无关的代码。
- 如果已有函数可以复用，优先复用已有函数。

## README 写作规则

每次修改 `README.md` 时，请延续当前风格。

README 应该让人一读就知道：

- 这个项目是什么。
- 当前做到哪一步。
- 每一天完成了什么。
- 每一天产出了哪些文件。
- 当前接口怎么启动和测试。
- 哪些是业务核心逻辑。
- 哪些是 FastAPI / pandas / pytest 的固定写法。

### 每日记录格式

每日记录放在：

```text
## 每日开发记录
```

下面。

日期标题使用：

```text
### YYYY-MM-DD：当天主题
```

每一天尽量包含：

- 目标
- 完成内容
- 当日核心产出
- 当日技术点
- 阶段价值

如果当天修改了接口、测试或 README，需要写清楚对应文件。

### 追加规则

- 不要删除历史日期内容。
- 不要大幅重写过去日期内容，除非用户明确要求。
- 新一天的内容应该追加到“每日开发记录”中。
- 如果需要修正历史内容，只做小幅修正，并保持原有风格。
- 如果不确定真实历史事实，用“按当前项目记录整理”这类谨慎表述，不要写成绝对事实。

## 当前重要文件

```text
app/main.py
```

FastAPI 入口文件，当前包含：

- `/health`
- `/chat`
- `/profile/upload`
- `/analyze-csv`

```text
app/services/data_profile.py
```

数据画像模块，当前核心函数：

- `profile_dataframe(df)`
- `analyze_csv(file_path)`

```text
tests/test_profile_upload.py
```

CSV 上传接口测试。

```text
data/sample_sales.csv
```

当前用于 Swagger 和 pytest 的示例 CSV 文件。

```text
pytest.ini
```

pytest 配置文件，用于让测试可以正确导入 `app` 包。

```text
README.md
```

项目说明和每日开发复盘文档。

## 当前核心业务流程

CSV 上传画像接口的核心流程是：

```text
用户上传 CSV 文件
-> FastAPI 通过 UploadFile 接收文件
-> 校验文件后缀是否为 .csv
-> await file.read() 读取上传内容
-> io.BytesIO 包装二进制内容
-> pandas.read_csv() 读取为 DataFrame
-> profile_dataframe(df) 生成数据画像
-> FastAPI 返回 JSON
```

返回字段包括：

- `filename`
- `shape.rows`
- `shape.columns`
- `columns`
- `dtypes`
- `missing_values`
- `numeric_summary`
- `preview`

## 测试说明

优先使用：

```bash
pytest
```

如果不可用，再尝试：

```bash
python -m pytest
```

测试前不需要先启动 `uvicorn`。

原因：

`pytest + FastAPI TestClient` 会直接加载 `app.main:app`，并在测试进程里模拟 HTTP 请求。

只有做人工展示或 Swagger 验证时，才需要启动：

```bash
uvicorn app.main:app --reload
```

然后访问：

```text
http://127.0.0.1:8000/docs
```

## 下次 Codex 启动建议

下次开始新任务时，建议先阅读：

1. `AGENTS.md`
2. `README.md`
3. `app/main.py`
4. `app/services/data_profile.py`
5. `tests/test_profile_upload.py`

然后再修改代码。

如果用户要求继续写 README，请先理解 `README.md` 的现有结构，再追加当天内容。

## 和用户沟通时的偏好

用户希望项目适合学习和复盘，所以回答时要：

- 使用中文。
- 说明改了哪些文件。
- 说明每个文件改了什么。
- 说明如何启动项目。
- 说明如何运行测试。
- 说明核心业务流程。
- 区分“必须理解的核心逻辑”和“框架固定写法”。

不要只给结论，要能帮助用户理解为什么这样写。
