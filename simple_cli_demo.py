from dialogue import DialogueManager 

dm = DialogueManager(model_name="qwen-plus")

# 对话交互
print("小美：我是小美，请问您想了解什么流量套餐?")
while True:
    user_input = input("用户：")
    if user_input.strip().lower() in ["exit", "quit"]:
        print("小美：好的，感谢您的咨询，再见！")
        break
    
    response, action = dm.run(user_input, verbose=True)
    print(f"小美：{response}")
    
    if action == "close":
        print("小美：好的，感谢您的咨询，再见！")
        break