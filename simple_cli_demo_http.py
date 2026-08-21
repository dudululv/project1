import os
import json
import sys

BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

try:
    import requests
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
    def post_json(url, payload):
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = Request(url, data=data, headers={"Content-Type": "application/json"})
        with urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    def get_json(url):
        req = Request(url)
        with urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))

def main():
    print("小美：我是小美，请问您想了解什么流量套餐?")
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
        try:
            result = post_json(f"{BASE_URL}/chat/http", {"conversation_id": conversation_id, "message": user_input})
        except Exception as e:
            print(f"小美：调用失败：{e}")
            continue
        response = result.get("response", "")
        action = result.get("action", "")
        print(f"小美：{response}")
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

