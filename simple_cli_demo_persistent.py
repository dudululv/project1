from dialogue_persistent import DialogueManagerPersistent 
from database import Database
import json 

db = Database(db_url="sqlite:///dialogue.db")

dm = DialogueManagerPersistent(model_name="qwen-plus", db=db)

# 对话交互
print("小美：我是小美，请问您想了解什么流量套餐?")
conversation_id = dm.create_conversation()
print(f"(会话ID: {conversation_id})")
print(f'-----------')

while True:
    user_input = input("用户：")
    if user_input.strip().lower() in ["exit", "quit"]:
        print("小美：好的，感谢您的咨询，再见！")
        break
    
    response, action = dm.run(conversation_id, user_input, verbose=True)
    print(f"小美：{response}")
    
    if action == "close":
        print("小美：好的，感谢您的咨询，再见！")
        break
    
print('--------conversation history--------')
print(dm.get_conversation_history(conversation_id))