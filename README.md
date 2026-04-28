# DataInsight Agent

DataInsight Agent 是一个基于 RAG 与 Tool Calling 的智能数据分析助手。

## 项目目标

本项目旨在实现一个可以处理文档问答、CSV 数据分析和工具调用的 AI 应用系统。

## 当前功能

- [x] FastAPI 后端基础结构
- [x] 健康检查接口 `/health`
- [x] 智谱 GLM-4.7 API 调用
- [x] 基础聊天接口 `/chat`
- [ ] 文档上传
- [ ] RAG 检索问答
- [ ] CSV 数据分析
- [ ] 图表生成
- [ ] Tool Calling

## 技术栈

- Python
- FastAPI
- ZhipuAI GLM-4.7
- Pydantic
- python-dotenv

## 启动方式

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## 2026-04-27 更新

今日完成 CSV 数据概览模块。

### 新增功能

- 新增 `analyze_csv(file_path: str)` 函数
- 支持读取本地 CSV 文件
- 返回数据集基础信息：
  - 行数 rows
  - 列数 columns
  - 字段名 column_names
  - 字段类型 dtypes
  - 缺失值统计 missing_values
  - 数值列基础统计 numeric_summary
- 新增 FastAPI 接口：

```http
GET /analyze-csv?file_path=data/sample_sales.csv
```

## 2026-04-28 项目进度：CSV 上传与数据画像 API

### 今日目标

在前两天已完成项目基础结构、FastAPI 后端服务和 `data_profile.py` 数据画像模块的基础上，今日目标是将数据画像能力接入 FastAPI，形成第一个可通过 API 调用的核心功能。

本日重点不是新增复杂 Agent 或 RAG 功能，而是先完成一个基础业务闭环：

```text
上传 CSV 文件 → FastAPI 接收文件 → pandas 读取数据 → 调用数据画像模块 → 返回 JSON 分析结果
```
