# 项目简介

一个用于模拟“手机流量套餐客服”对话的项目，包含自然语言理解（NLU）、对话策略（Dialogue Manager）、自然语言生成（NLG）、检索工具（MockedRetriever），以及可选的会话持久化（SQLite + SQLAlchemy）。

项目使用灵积 DashScope 的 OpenAI 兼容接口，默认模型为 `qwen-plus`。

---

## 目录结构

- `dialogue.py`：无持久化的对话管理器 `DialogueManager`
- `dialogue_persistent.py`：支持持久化的对话管理器 `DialogueManagerPersistent`
- `nlu.py`：NLU 模块，输出用户意图与筛选条件（JSON）
- `nlg.py`：NLG 模块，根据对话动作生成客服回复
- `tools/retriever.py`：Mock 检索器，基于固定数据进行筛选与排序
- `database.py`：SQLAlchemy Core 实现的会话与消息存储
- `simple_cli_demo.py`：无持久化的命令行演示
- `simple_cli_demo_persistent.py`：支持持久化的命令行演示
- `app.py`：FastAPI 服务实现（提供 HTTP 与 SSE 接口）
- `api文档.md`：服务接口说明文档
- `simple_cli_demo_http.py`：基于服务接口的命令行演示（标准请求-响应）
- `simple_cli_demo_sse.py`：基于服务接口的命令行演示（SSE 流式）
- `.env.example`：环境变量示例（DashScope 配置）
- `dialogue.db`：SQLite 数据库文件（运行持久化演示后生成/使用）

---

## 环境准备

1) 安装依赖（建议 Python 3.9+）：

```
pip install openai python-dotenv sqlalchemy fastapi uvicorn pydantic requests
```

2) 配置环境变量：复制 `.env.example` 到 `.env` 并填写真实的 DashScope 密钥。

```
cp .env.example .env
```

编辑 `.env`：

```
DASHSCOPE_API_KEY="<你的 DashScope API Key>"
DASHSCOPE_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"
```

---

## 快速开始

### 1. 运行无持久化 CLI 演示

```
python simple_cli_demo.py
```

- 输入你的问题，输入 `exit` 或 `quit` 结束对话。
- 该演示在内存中维护会话状态与对话历史，不写入数据库。

### 2. 运行持久化 CLI 演示

```
python simple_cli_demo_persistent.py
```

- 启动后会打印新建的会话 ID。
- 输入你的问题，输入 `exit` 或 `quit` 结束对话。
- 对话历史、对话状态（如是否已推荐 `has_offered`）会写入 `dialogue.db`。

---

- 运行基于服务的 CLI（标准请求-响应）：
```
python simple_cli_demo_http.py
```
- 运行基于服务的 CLI（SSE 流式）：
```
python simple_cli_demo_sse.py
```
- 可通过环境变量覆盖服务地址：
```
export API_BASE_URL="http://localhost:8000"
```
（默认使用 http://localhost:8000）

### 3. 运行 Web 服务（FastAPI）

```
uvicorn app:app --host 0.0.0.0 --port 8000
```

- 接口详见 [api文档.md]
- 主要端点：
  - `GET /` 根路径，返回服务信息与接口清单
  - `POST /conversation/new` 创建会话
  - `POST /chat/http` 标准对话（请求体包含 conversation_id、message）
  - `POST /chat/sse` 流式对话（SSE，逐块返回回复内容）
  - `GET /conversation/{conversation_id}` 获取指定会话历史
  - `GET /conversation` 获取会话列表

#### 服务运行说明（步骤）
- 准备 `.env`（包含 `DASHSCOPE_API_KEY` 与 `DASHSCOPE_BASE_URL`），并安装依赖。
- 启动服务：`uvicorn app:app --host 0.0.0.0 --port 8000`
- 验证根路径：
  ```
  curl -X GET http://localhost:8000/
  ```
- 创建会话：
  ```
  curl -X POST http://localhost:8000/conversation/new -H "Content-Type: application/json"
  ```
- 标准对话：
  ```
  curl -X POST http://localhost:8000/chat/http \
    -H "Content-Type: application/json" \
    -d '{"conversation_id":"<替换为上一步返回的ID>","message":"我想要便宜的套餐"}'
  ```
- 流式对话（SSE）：
  ```
  curl -N -H "Accept: text/event-stream" \
    -X POST http://localhost:8000/chat/sse \
    -H "Content-Type: application/json" \
    -d '{"conversation_id":"<替换为会话ID>","message":"100G以内有什么更便宜的？"}'
  ```
- 查看会话历史：
  ```
  curl -X GET http://localhost:8000/conversation/<会话ID>
  ```
- 列出所有会话：
  ```
  curl -X GET http://localhost:8000/conversation
  ```

## 工作原理

### DialogueManager（无持久化）
- 维护内存态：`dialogue_state`（包含最近一次的检索结果与是否已推荐）、`chat_history`。
- 流程：
  - 追加用户消息到 `chat_history`
  - 调用 `NLU.run(chat_history)` 生成筛选条件（JSON），示例字段：
    - `name`: `经济套餐 | 畅游套餐 | 超级套餐`
    - `price`: `{operator: "<=|<|>=|>|=", value: int}`
    - `data`: `{operator: "<=|<|>=|>|=", value: int}`
    - `sort`: `{ordering: "ascend|descend", value: "price|data"}`
  - 用筛选条件调用 `MockedRetriever.retrieve(**nlu_semantics)` 返回匹配的产品记录
  - 根据是否命中记录与是否重复推荐，生成动作 `inform | request | offer | close`
  - 调用 `NLG.run(chat_history, action, record)` 生成客服回复
  - 更新 `dialogue_state` 与 `chat_history`

### DialogueManagerPersistent（持久化）
- 通过 `Database` 管理 `conversations` 与 `messages` 两张表：
  - `create_conversation()` 新建会话并返回 `conversation_id`
  - `add_message()`、`get_messages()`、`get_chat_history()` 管理消息
  - `update_conversation_state()` 更新持久化的 `dialogue_state` 与 `has_offered`
- 流程与无持久化版本一致，但状态与历史从数据库读取/写回。

---

## 配置与可定制项

- 模型：默认 `qwen-plus`，可在 `simple_cli_demo.py` 与 `simple_cli_demo_persistent.py` 中修改传入的 `model_name`。
- 检索器：当前为 `MockedRetriever`，位于 `tools/retriever.py`，可替换为真实检索服务（例如向量库、SQL 查询等）。
- 数据库：默认 `sqlite:///dialogue.db`，可在 `simple_cli_demo_persistent.py` 中通过 `Database(db_url=...)` 修改存储位置或类型。

---

## 常见问题

- 未设置环境变量或密钥错误：`openai` 客户端初始化会失败；请确认 `.env` 中 `DASHSCOPE_API_KEY` 与 `DASHSCOPE_BASE_URL`。
- 依赖缺失：确保已安装 `openai`、`python-dotenv`、`sqlalchemy`。
- 持久化演示首次运行会创建 `dialogue.db` 并初始化表结构。

---

## 后续扩展建议

- 将 `MockedRetriever` 替换为真实检索组件，并完善产品库。
- 为 `NLU/NLG` 增加单元测试与更严格的输出校验。
- 提供 Web UI（例如 FastAPI + 前端）并使用 `DialogueManagerPersistent.run_stream` 做流式输出。
- 增加日志/监控与对话分析报表。
