# DataInsight Agent

DataInsight Agent 是一个用于求职展示的 AI 数据分析 Agent 项目。

项目当前阶段先聚焦后端基础能力：FastAPI 服务、LLM 配置、CSV 数据读取、数据画像、上传接口、异常处理和自动化测试。后续再继续扩展 Agent、RAG、数据库、前端和 Docker。

> 说明：下面的日期是按当前项目记录和开发计划整理的阶段日志，用来帮助复盘“每一天做了什么、产出了什么、学到了什么”。

## 每日开发记录

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

- [app/main.py](app/main.py)
- [app/core/config.py](app/core/config.py)
- [app/services/llm_service.py](app/services/llm_service.py)
- [app/services/data_profile.py](app/services/data_profile.py)

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

- [app/main.py](app/main.py)
- [app/services/data_profile.py](app/services/data_profile.py)
- [data/sample_sales.csv](data/sample_sales.csv)
- [tests/test_profile_upload.py](tests/test_profile_upload.py)
- [pytest.ini](pytest.ini)
- [app/__init__.py](app/__init__.py)
- [README.md](README.md)

阶段价值：

- 4.28 已经能上传 CSV 并返回画像。
- 4.29 没有改变核心统计算法，而是增强工程质量：
  - 返回结构更适合展示。
  - 错误信息更清楚。
  - pytest 可以自动验证接口。
  - README 可以支持后续复盘。

## 当前项目结构

```text
DataInsight-Agent/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── core/
│   │   └── config.py
│   └── services/
│       ├── data_profile.py
│       └── llm_service.py
├── data/
│   └── sample_sales.csv
├── tests/
│   └── test_profile_upload.py
├── pytest.ini
├── requirements.txt
└── README.md
```

## 当前功能状态

已完成：

- FastAPI 后端基础服务
- `/health` 健康检查接口
- 智谱 GLM-4.7 默认配置
- `/chat` 基础 LLM 调用接口
- `data_profile.py` 数据画像模块
- `/analyze-csv` 本地 CSV 文件画像接口
- `/profile/upload` CSV 上传画像接口
- CSV 上传接口异常处理
- pytest 自动化测试
- 示例 CSV 数据

暂不做：

- Agent 编排
- RAG
- 数据库
- 前端
- Docker

## 当前接口说明

### 健康检查

```http
GET /health
```

作用：确认 FastAPI 服务是否正常启动。

返回示例：

```json
{
  "status": "ok"
}
```

### 本地 CSV 文件画像

```http
GET /analyze-csv?file_path=data/sample_sales.csv
```

作用：读取项目本地 CSV 文件路径，并返回数据画像结果。

适用场景：

- 快速验证 `data_profile.py` 是否能处理本地 CSV。
- 不经过文件上传，直接分析项目目录里的示例文件。

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
- `dtypes`：每列的数据类型。
- `missing_values`：每列缺失值数量。
- `numeric_summary`：数值列的均值、最小值、最大值。
- `preview`：前 5 行数据预览。

错误处理：

- 非 `.csv` 文件：返回 400。
- 空 CSV 文件：返回 400。
- CSV 格式读取失败：返回 400。
- 服务端未知错误：返回 500。

## 示例数据

文件位置：

```text
data/sample_sales.csv
```

文件内容：

```csv
date,product,region,sales,profit
2026-04-01,A,济南,1200,300
2026-04-02,B,杭州,1800,450
2026-04-03,A,济南,1500,380
2026-04-04,C,上海,,500
2026-04-05,B,杭州,2100,620
```

这个文件用于测试：

- 中文字段值能否正常返回。
- `sales` 列有 1 个缺失值。
- `sales` 和 `profit` 是数值列，可以生成统计摘要。

## 本地启动

安装依赖：

```bash
pip install -r requirements.txt
```

启动服务：

```bash
uvicorn app.main:app --reload
```

Swagger 测试地址：

```text
http://127.0.0.1:8000/docs
```

在 Swagger 中测试上传接口：

1. 打开 `/docs`。
2. 找到 `POST /profile/upload`。
3. 点击 `Try it out`。
4. 点击 `Choose File`。
5. 选择 `data/sample_sales.csv`。
6. 点击 `Execute`。

## 运行测试

运行全部测试：

```bash
pytest
```

如果命令不可用，可以尝试：

```bash
python -m pytest
```

当前测试文件：

```text
tests/test_profile_upload.py
```

测试覆盖：

- 正常 CSV 上传返回 200。
- 非 CSV 文件返回 400。
- 空 CSV 文件返回 400。

## 核心业务流程

当前最重要的业务流程是 CSV 上传画像：

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

## 必须理解的核心逻辑

项目自己的业务逻辑：

- `profile_dataframe(df)`：把 DataFrame 转成数据画像。
- `analyze_csv(file_path)`：分析本地 CSV 文件。
- `/profile/upload`：分析用户上传的 CSV 文件。
- `numeric_summary`：只对数值列计算均值、最小值、最大值。
- `missing_values`：统计每列缺失值数量。
- `preview`：返回前 5 行数据，便于展示。

框架或工具的固定写法：

- `app = FastAPI(...)`：创建 FastAPI 应用。
- `UploadFile = File(...)`：FastAPI 文件上传写法。
- `HTTPException(...)`：接口返回错误状态码。
- `TestClient(app)`：pytest 中测试 FastAPI 接口。
- `pytest.ini`：配置 pytest 的导入路径和测试目录。
- `app/__init__.py`：让 `app` 目录成为可导入的 Python 包。

## 下一步计划

建议下一阶段继续保持小步推进：

1. 给 `data_profile.py` 增加更丰富的画像指标。
2. 把画像结果整理成适合 LLM 使用的摘要文本。
3. 再接入 LLM，让模型基于画像结果生成自然语言分析。
4. 后续再考虑 Agent、RAG、数据库和前端。
