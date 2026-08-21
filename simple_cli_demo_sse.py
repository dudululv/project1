import os
import json
import sys

BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

try:
    import requests
    def stream_post(url, payload):
        r = requests.post(url, json=payload, stream=True, timeout=60)
        r.raise_for_status()
        for line in r.iter_lines(decode_unicode=True):
            if not line:
                continue
            yield line
    def post_json(url, payload):
        r = requests.post(url, json=payload, timeout=30)
        r.raise_for_status()
        return r.json()
    def get_json(url):
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        return r.json()
except Exception:
    from urllib.request import Request, urlopen
    def stream_post(url, payload):
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = Request(url, data=data, headers={"Content-Type": "application/json"})
        with urlopen(req, timeout=60) as resp:
            while True:
                line = resp.readline()
                if not line:
                    break
                yield line.decode("utf-8", errors="ignore")
    def post_json(url, payload):
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = Request(url, data=data, headers={"Content-Type": "application/json"})
        with urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    def get_json(url):
        req = Request(url)
        with urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))

def stream_chat(conversation_id, message):
    url = f"{BASE_URL}/chat/sse"
    action = None
    for line in stream_post(url, {"conversation_id": conversation_id, "message": message}):
        line = line.strip()
        if not line:
            continue
        if line.startswith("data:"):
            payload = line[5:].strip()
            try:
                obj = json.loads(payload)
            except Exception:
                continue
            t = obj.get("type")
            if t == "conversation_id":
                pass
            elif t == "content":
                chunk = obj.get("data", "")
                sys.stdout.write(chunk)
                sys.stdout.flush()
            elif t == "error":
                msg = obj.get("message", "")
                print(f"\n小美：发生错误：{msg}")
            elif t == "done":
                action = obj.get("action")
                print()
                break
    return action

def main():
    print("小美：我是小美（流式回复），请问您想了解什么流量套餐?")
    try:
        created = post_json(f"{BASE_URL}/conversation/new", {})
    except Exception as e:
        print(f"小美：服务不可用，请确认已启动。错误：{e}")
        sys.exit(1)
    conversation_id = created.get("conversation_id")
    print(f"(会话ID: {conversation_id})")
    print("-----------")
    while True:
        user_input = input("用户：")
        if user_input.strip().lower() in ["exit", "quit"]:
            print("小美：好的，感谢您的咨询，再见！")
            break
        action = stream_chat(conversation_id, user_input)
        if action == "close":
            print("小美：好的，感谢您的咨询，再见！")
            break
    print("--------conversation history--------")
    try:
        history = get_json(f"{BASE_URL}/conversation/{conversation_id}")
        print(json.dumps(history, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"小美：获取历史失败：{e}")

if __name__ == "__main__":
    main()

