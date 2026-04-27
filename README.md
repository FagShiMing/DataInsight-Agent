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