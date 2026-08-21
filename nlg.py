from openai import OpenAI 

class NLG: 
    '''
    自然语言生成模块，根据对话策略生成系统响应
    '''
    
    def __init__(self, client: OpenAI, model_name: str="qwen-plus"):
        self.client = client 
        self.model_name = model_name
        
    def run(self, chat_history: list, action: str, record: dict, assistant_name="小美")-> str: 
        prompt = self._get_prompt(chat_history, action, record)
        messages = [
            {"role": "system", "content": f"你是一个流量包的销售客服，你叫{assistant_name}，请简洁地回答用户的问题，在回答时不用刻意表明自己的身份。"},
            {"role": "user", "content": prompt}
        ]
        
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=0.2,  # 设置温度为0.0，确保输出的确定性
            stream=False
        )
        
        return response.choices[0].message.content
    
    def run_stream(self, chat_history: list, action: str, record: dict, assistant_name="小美"): 
        prompt = self._get_prompt(chat_history, action, record)
        messages = [
            {"role": "system", "content": f"你是一个流量包的销售客服，你叫{assistant_name}，请简洁地回答用户的问题，在回答时不用刻意表明自己的身份。"},
            {"role": "user", "content": prompt}
        ]
        
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=0.0,  # 设置温度为0.0，确保输出的确定性
            stream=True,
        )
        
        for chunk in response:
            try:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
            except AttributeError:
                pass
    
    def _get_prompt(self, chat_history: list, action: str, record: dict)-> str: 
        # 获得对话历史
        context = self._get_context(chat_history)
        
        # 拼接提示词
        if action == "inform": 
            prompt = f"""
# 目标
向用户介绍如下产品：{record["name"]}, 月费{record["price"]}元, 月流量{record['data']}G。

# 对话上下文
{context}
            """
            
        if action == "request": 
            prompt = f"""
# 目标
没有找到符合条件的流量产品，询问用户是否有其他选择倾向。
只询问用户在流量和月费方面的需求即可，不需要涉及其他更多方面。
只向用户询问即可，不要推荐任何产品。
如果确实没有满足用户需求的产品，礼貌地结束对话即可。
如果用户已经表达出结束对话的意愿，输出“好的，感谢您的咨询，再见！”。
    
# 对话上下文
{context}
            """
            
        if action == "offer":
            prompt = f"""
# 目标
帮助用户下单购买以下产品：{record["name"]}, 月费{record["price"]}元, 月流量{record['data']}G
        
# 对话上下文
{context}
            """
            
        if action == "close":
            prompt = f"""
# 目标
输出简洁的结束语，结束对话。
    
# 对话上下文
{context}
            """
            
        return prompt
    
    def _get_context(self, chat_history: list):
        '''
        获取对话上下文
        :param user_input 用户输入
        :param chat_history 聊天历史
        '''
        
        if chat_history is None:
            chat_history = []
        
        # 将聊天历史转换为字符串格式
        context = "\n".join([f"{msg['role']}: {msg['content']}" for msg in chat_history])
        
        return context.replace("user:", "用户:").replace("assistant:", "客服:")
        
