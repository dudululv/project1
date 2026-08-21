from nlu import NLU 
from nlg import NLG
from tools.retriever import MockedRetriever 
from openai import OpenAI 
import os 
from dotenv import load_dotenv 
load_dotenv(override=True)

import logging 

# 配置基础日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# 获取logger实例
logger = logging.getLogger(__name__)

class DialogueManager: 
    '''
    对话管理模块，根据对话历史和NLU结果决定系统的响应策略
    '''
    
    def __init__(self, model_name: str="qwen-plus"):
        self.client = OpenAI(
            api_key=os.getenv("DASHSCOPE_API_KEY"), 
            base_url=os.getenv("DASHSCOPE_BASE_URL")
        )
        self.nlu = NLU(client=self.client, model_name=model_name)
        self.retriever = MockedRetriever()
        self.nlg = NLG(client=self.client, model_name=model_name)
        
        # 初始化对话状态
        self.dialogue_state = {
            "nlu_semantics": None, 
            "record": None, 
            "has_offered": False
        }
        
        # chat history 
        self.chat_history = []
        
    def run(self, user_input: str, verbose: bool=True):
        # 1. 更新对话历史
        self.chat_history.append({"role": "user", "content": user_input})
        
        # 2. 调用NLU模块获取语义理解的结果 (考虑了全部对话历史)
        nlu_semantics = self.nlu.run(self.chat_history)
        if verbose: 
            logger.info(f"NLU Semantics: {nlu_semantics}")
            
        # 3. 生成对话策略 (action: inform, request, offer, close)
        # 3.1. 根据NLU的结果查询产品信息
        records = self.retriever.retrieve(**nlu_semantics)
        
        # 3.2. 生成dialogue action 
        if len(records) == 0:
            action = "request"
        elif records[0] == self.dialogue_state['record']:
            if self.dialogue_state['has_offered']:
                action = "close"
            else: 
                action = "offer"
                self.dialogue_state['has_offered'] = True
        else:
            action = "inform"
            
        if verbose:
            logger.info(f"Dialogue Action: {action}")
        
        # 4. 生成自然语言回复
        response = self.nlg.run(
            chat_history=self.chat_history, 
            action=action, 
            record=records[0] if len(records) > 0 else {}
        )
    
        
        # 5. 更新对话状态和对话历史
        self.dialogue_state["nlu_semantics"] = nlu_semantics
        self.dialogue_state["record"] = records[0] if len(records) > 0 else None
        
        # 更新对话历史，添加系统回复部分  
        self.chat_history.append({"role": "assistant", "content": response})
        
        return response, action 