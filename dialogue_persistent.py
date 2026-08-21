from nlu import NLU
from nlg import NLG
from tools.retriever import MockedRetriever
from database import Database
from openai import OpenAI
import os
import logging

# 配置基础日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# 获取logger实例
logger = logging.getLogger(__name__)

from dotenv import load_dotenv
load_dotenv(override=True)

class DialogueManagerPersistent:
    '''支持持久化的对话管理器'''
    
    def __init__(self, model_name: str, db: Database):
        """
        初始化对话管理器
        :param db: 数据库实例
        :param model_name: 模型名称
        """
        
        self.client = OpenAI(
            api_key=os.getenv("DASHSCOPE_API_KEY"),
            base_url=os.getenv("DASHSCOPE_BASE_URL"),
        )
        
        self.nlu = NLU(self.client, model_name)
        self.retrieve_tool = MockedRetriever()
        self.nlg = NLG(self.client, model_name)
        
        self.db = db
        
    def create_conversation(self) -> str:
        """
        创建新的会话
        :return: 会话ID
        """
        return self.db.create_conversation()
    
    def get_conversation_history(self, conversation_id: str) -> dict:
        """
        获取会话历史
        :param conversation_id: 会话ID
        :return: 会话信息和消息历史
        """
        conversation = self.db.get_conversation(conversation_id)
        if conversation is None:
            return None
        
        messages = self.db.get_messages(conversation_id)
        
        return {
            "conversation_id": conversation_id,
            "created_at": conversation["created_at"].isoformat(),
            "updated_at": conversation["updated_at"].isoformat(),
            "messages": messages
        }
        
    def run(self, conversation_id: str, user_input: str, verbose: bool=True):
        """
        执行对话轮次
        :param conversation_id: 会话ID
        :param user_input: 用户输入
        :param verbose: 是否打印调试信息
        :return: (回复内容, 对话动作)
        """
        # 1. 从数据库加载会话状态和历史
        conversation = self.db.get_conversation(conversation_id)
        if conversation is None:
            raise ValueError(f"Conversation {conversation_id} not found")
        
        dialogue_state = conversation["dialogue_state"] # nlu semantics
        has_offered = conversation["has_offered"]   
        chat_history = self.db.get_chat_history(conversation_id)
        if not chat_history:
            chat_history = []
        # 更新对话历史
        chat_history.append({"role": "user", "content": user_input})
        
        # 2. 调用NLU模块获取语义理解结果 (NLU是上下文相关的，包含对全部对话历史的理解结果)
        nlu_semantics = self.nlu.run(chat_history)
        if verbose:
            logger.info(f"NLU Semantics: {nlu_semantics}")
            
        # 3. 根据nlu_semantics查流量套餐产品信息
        records = self.retrieve_tool.retrieve(**nlu_semantics)
        if verbose:
            logger.info(f"Retrieved Records: {records}")
            
        # 4. 根据流量套餐产品查询的情况生成dialogue action (inform, request, offer, close_dialogue)
        if len(records) == 0:
                action = "request"
        elif records[0] == dialogue_state["record"]:
            if has_offered:
                action = "close"
            else:
                action = "offer"
                has_offered = True
        else:
            action = "inform"
        
        if verbose:
            logger.info(f"Dialogue Action: {action}")
            
        # 5. 生成自然语言回复
        response = self.nlg.run(chat_history, action, records[0] if len(records) > 0 else [])
        if verbose:
            logger.info(f"Generated Response: {response}")
        
        # 6. 更新数据库：保存消息
        self.db.add_message(conversation_id, "user", user_input)
        self.db.add_message(conversation_id, "assistant", response)
        
        # 7. 更新数据库：保存对话状态
        dialogue_state["nlu_semantics"] = nlu_semantics
        dialogue_state["record"] = records[0] if len(records) > 0 else []
        self.db.update_conversation_state(conversation_id, dialogue_state, has_offered)
        
        return response, action

    def run_stream(self, conversation_id: str, user_input: str, verbose: bool=True):
        """
        执行对话轮次
        :param conversation_id: 会话ID
        :param user_input: 用户输入
        :param verbose: 是否打印调试信息
        :return: (回复内容, 对话动作)
        """
        # 1. 从数据库加载会话状态和历史
        conversation = self.db.get_conversation(conversation_id)
        if conversation is None:
            raise ValueError(f"Conversation {conversation_id} not found")
        
        dialogue_state = conversation["dialogue_state"]
        has_offered = conversation["has_offered"]
        chat_history = self.db.get_chat_history(conversation_id)
        if not chat_history:
            chat_history = []
        chat_history.append({"role": "user", "content": user_input})
        
        # 2. 调用NLU模块获取语义理解结果 (NLU是上下文相关的，包含对全部对话历史的理解结果)
        nlu_semantics = self.nlu.run(chat_history)
        if verbose:
            logger.info(f"NLU Semantics: {nlu_semantics}")
            
        # 3. 根据nlu_semantics查流量套餐产品信息
        records = self.retrieve_tool.retrieve(**nlu_semantics)
        if verbose:
            logger.info(f"Retrieved Records: {records}")
            
        # 4. 根据流量套餐产品查询的情况生成dialogue action (inform, request, offer, close_dialogue)
        if len(records) == 0:
                action = "request"
        elif records[0] == dialogue_state["record"]:
            if has_offered:
                action = "close"
            else:
                action = "offer"
                has_offered = True
        else:
            action = "inform"
        
        if verbose:
            logger.info(f"Dialogue Action: {action}")
            
        # 5. 生成自然语言回复
        chunks = self.nlg.run_stream(chat_history, action, records[0] if len(records) > 0 else [])
        final_response = ""
        for chunk in chunks:
            final_response += chunk
            yield chunk 
        yield f"action: {action}"
            
        if verbose:
            logger.info(f"Generated Response: {final_response}")
        
        # 6. 更新数据库：保存消息
        self.db.add_message(conversation_id, "user", user_input)
        self.db.add_message(conversation_id, "assistant", final_response)
        
        # 7. 更新数据库：保存对话状态
        dialogue_state["nlu_semantics"] = nlu_semantics
        dialogue_state["record"] = records[0] if len(records) > 0 else []
        self.db.update_conversation_state(conversation_id, dialogue_state, has_offered)
