# 流量套餐对话服务 API

**版本**: 2.0.0
**基础 URL**: `http://localhost:8000`

---

## 核心接口

### 0. 根路径

返回服务名称、版本与接口清单。

- Endpoint: `GET /`
- 成功响应 (`200 OK`):
  ```json
  {
    "name": "流量套餐对话系统",
    "version": "2.0.0",
    "endpoints": {
      "create_conversation": {
        "method": "POST",
        "path": "/conversation/new",
        "description": "创建新的会话"
      },
      "get_conversation": {
        "method": "GET",
        "path": "/conversation/{conversation_id}",
        "description": "获取指定会话的历史与消息"
      },
      "chat_http": {
        "method": "POST",
        "path": "/chat/http",
        "description": "标准请求-响应的对话接口"
      },
      "chat_sse": {
        "method": "POST",
        "path": "/chat/sse",
        "description": "SSE 流式对话接口，逐块返回生成内容"
      }
    }
  }
  ```

### 1. 创建会话

创建一次新的对话。

- **Endpoint**: `POST /conversation/new`
- **成功响应** (`200 OK`):
  ```json
  {
     "conversation_id": conversation_id,
     "message": "会话创建成功"
  }
  ```

### 2. 发送消息

在一个会话中发送消息并获取回复。

- **Endpoint**: `POST /chat/http`
- **请求体**:
  ```json
  {
    "conversation_id": "550e8400-e29b-41d4-a716-446655440000"
    "message": "我想要便宜的套餐"
  }
  ```
- **成功响应** (`200 OK`):
  ```json
  {
    "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
    "response": "可以选择经济套餐，月租费20元，月流量50G",
    "action": "inform"
  }
  ```

### 3. 发送消息 (流式)

实时获取对话回复的事件流。

- **Endpoint**: `POST /chat/sse`
- **请求体**: (同上)
- **成功响应** (`200 OK`):
  - **类型**: `text/event-stream`
  - **事件流**:
    ```
    data: {"type": "conversation_id", "conversation_id": "550e8400-e29b-41d4-a716-446655440000"}

    data: {"type": "content", "data": "可以"}

    data: {"type": "content", "data": "选择"}

    ...

    data: {"type": "done", "action": "inform"}
    ```

### 4. 获取消息历史

获取一个会话的所有消息记录。

- **Endpoint**: `GET /conversation/{conversation_id}`
- **成功响应** (`200 OK`):
  ```json
  [
    {
      "conversation_id": "3c40c352-bcc0-4194-832b-093f2511233a",
      "created_at": "2026-01-27T17:34:45",
      "updated_at": "2026-01-27T17:35:30",
      "messages": [
        {
          "id": 88,
          "role": "user",
          "content": "便宜点的套餐"
        },
        {
          "id": 89,
          "role": "assistant",
          "content": "经济套餐，月费20元，含10G流量，性价比很高哦"
        }
        // ...
      ]
    }
  ]
  ```

### 5. 获取会话列表

获取所有会话的基本信息（不含消息列表）。

- **Endpoint**: `GET /conversation`
- **成功响应** (`200 OK`):
  ```json
  [
    {
      "conversation_id": "3c40c352-bcc0-4194-832b-093f2511233a",
      "created_time": "2026-01-27T17:34:45",
      "updated_time": "2026-01-27T17:35:30"
    }
  ]
  ```
