from dotenv import load_dotenv
from openai import OpenAI
import os 
import json

load_dotenv(override=True)

class NLU:
    '''
    自然语言理解模块，根据对话上下文输出用户当前的意图和槽位信息
    '''
    
    def __init__(self, client: OpenAI, model_name: str="qwen-plus"):
        self.client = client 
        self.model_name = model_name 
        
    def run(self, chat_history : list)->dict:
        prompt = self._get_prompt(chat_history)
        
        messages = [
            {"role": "system", "content": "你是一个自然语言理解专家"},
            {"role": "user", "content": prompt}
        ]
        
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=0.0, # 设置温度为0.0，确保输出的确定性
                response_format={"type": "json_object"}
            )
            
            nlu_semantics = json.loads(response.choices[0].message.content)
        except Exception as e:
            print(f"Error during OpenAI API call: {e}")
            return {}

        
        return nlu_semantics
    
    def _get_prompt(self, chat_history: list):
        '''
        通过填充提示词模版，返回nlu所需要的prompt
        :param chat_history 聊天历史
        '''
        
        # 任务描述
        instruction = f"""
    你的任务是识别用户对手机流量套餐产品的选择条件。
    每种流量套餐产品包含三个属性：名称(name), 月费价格(price), 月流量(data)。
    根据对话上下文，识别用户在上述三种属性上的需求是什么，识别结果需要考虑整个对话的信息。
    如果用户没有了解流量套餐的意图，则输出空的JSON对象。
        """
        
        # 输出描述
        output_format = f"""
    输出格式为JSON，包含以下字段：
    1. name字段的取值为string类型，取值必须为以下之一：经济套餐、畅游套餐、超级套餐。
    
    2. price字段的取值为一个结构体，结构体包含两个字段：
    (1) operator，取值为string类型，取值必须为以下之一："<=" (小于等于), "<" (小于), ">=" (大于等于), ">" (大于), "=" (等于)
    (2) value, 取值为int类型
    
    3. data字段的取值为一个结构体，结构体包含两个字段：
    (1) operator，取值为string类型，取值必须为以下之一："<=" (小于等于), "<" (小于), ">=" (大于等于), ">" (大于), "=" (等于)
    (2) value, 取值为int类型
    
    4. 用户的输入中如果有按price或者data排序的意图，则输出sort字段，取值为一个结构体：
    (1) 结构体中以"ordering"="descend"表示按降序排序，"ordering"="ascend"表示按升序排序
    (2) value字段表示待排序的字段，取值为"price"或者"data"
    
    输出中只包含用户提及的字段，不要猜测任何用户未直接提及的字段，不要输出值为null的字段。
    只输出JSON, 不要输出多余的文字。
        """
        
        # 举例
        examples = """
    用户：100G套餐有什么

    {"data":{"operator":">=","value":100}, "sort":{"ordering":"ascend","value":"price"}}

    用户：200G套餐有什么
    客服：我们现在有超级套餐，流量1000G，月费200元
    用户：太贵了，有100元以内的不

    {"data":{"operator":">=","value":200},"price":{"operator":"<=","value":100}}

    用户：便宜的套餐有什么
    客服：我们现在有经济套餐，每月20元，10G流量
    用户：100G以上的有什么

    {"data":{"operator":">=","value":100},"sort":{"ordering"="ascend","value"="price"}}
    
    用户：想要流量大的套餐。
    客服：我们现在有超级套餐，流量1000G，月费200元
    用户：有便宜些的吗
    
    {"price": {"operator": "<", "value": 200}, "sort": {"ordering": "descend", "value": "data"}}
    
    用户：想要便宜的套餐
    客服：我们现在有经济套餐，每月20元，10G流量
    用户：流量有大一些的吗
    
    {"data": {"operator": ">", "value": 10}, "sort": {"ordering": "ascend", "value": "price"}}
        """
        
        # 对话上下文
        context = self._get_context(chat_history)
        
        # prompt模板
        prompt = f'''
    # 任务
    {instruction}
    
    # 输出
    {output_format}
    
    # 举例
    {examples}
    
    # 对话上下文
    {context}
        '''
        
        return prompt
    
    def _get_context(self, chat_history : list=None):
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
    
if __name__ == "__main__":
    client = OpenAI(
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        base_url=os.getenv("DASHSCOPE_BASE_URL")
    )
    
    nlu = NLU(client)
    
    chat_history = [
        {"role": "user", "content": "便宜的套餐有什么"},
        {"role": "assistant", "content": "我们现在有经济套餐，每月20元，10G流量"},
        {"role": "user", "content": "100G以上的有什么"}
    ]
    
    nlu_semantics = nlu.run(chat_history)
    print(nlu_semantics)