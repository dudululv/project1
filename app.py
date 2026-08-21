import json
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from database import Database
from dialogue_persistent import DialogueManagerPersistent

load_dotenv(override=True)

db = Database(db_url="sqlite:///dialogue.db")
dm = DialogueManagerPersistent(model_name="qwen-plus", db=db)

class ChatRequest(BaseModel):
    conversation_id: str
    message: str

app = FastAPI()

VERSION = "2.0.0"

@app.get("/")
def root():
    return {
        "name": "流量套餐对话系统",
        "version": VERSION,
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

@app.post("/conversation/new")
def create_conversation():
    try:
        conversation_id = dm.create_conversation()
        return {"conversation_id": conversation_id, "message": "会话创建成功"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat/http")
def chat_http(req: ChatRequest):
    try:
        response, action = dm.run(req.conversation_id, req.message, verbose=True)
        return {"conversation_id": req.conversation_id, "response": response, "action": action}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat/sse")
def chat_sse(req: ChatRequest):
    def gen():
        yield f'data: {json.dumps({"type": "conversation_id", "conversation_id": req.conversation_id}, ensure_ascii=False)}\n\n'
        action_val = None
        try:
            for chunk in dm.run_stream(req.conversation_id, req.message, verbose=True):
                if isinstance(chunk, str) and chunk.startswith("action: "):
                    action_val = chunk.split("action: ", 1)[1]
                else:
                    yield f'data: {json.dumps({"type": "content", "data": chunk}, ensure_ascii=False)}\n\n'
        except ValueError as e:
            yield f'data: {json.dumps({"type": "error", "message": str(e)}, ensure_ascii=False)}\n\n'
        except Exception as e:
            yield f'data: {json.dumps({"type": "error", "message": str(e)}, ensure_ascii=False)}\n\n'
        yield f'data: {json.dumps({"type": "done", "action": action_val}, ensure_ascii=False)}\n\n'
    return StreamingResponse(gen(), media_type="text/event-stream")

@app.get("/conversation/{conversation_id}")
def get_conversation(conversation_id: str):
    try:
        history = dm.get_conversation_history(conversation_id)
        if history is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return [history]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/conversation")
def list_conversations():
    try:
        items = db.get_all_conversations()
        result = []
        for c in items:
            result.append({
                "conversation_id": c["id"],
                "created_time": c["created_at"].isoformat() if c["created_at"] else None,
                "updated_time": c["updated_at"].isoformat() if c["updated_at"] else None
            })
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

