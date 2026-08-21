"""
数据库模型和操作模块
使用 SQLAlchemy Core 方式进行数据库操作
"""
from sqlalchemy import create_engine, Table, Column, Integer, String, Text, DateTime, MetaData, ForeignKey, select, insert, update
from sqlalchemy.pool import StaticPool
from datetime import datetime
import uuid
import json


# 创建元数据对象
metadata = MetaData()

# 定义 conversations 表
conversations = Table(
    'conversations',
    metadata,
    Column('id', String(36), primary_key=True),
    Column('created_at', DateTime, default=datetime.now),
    Column('updated_at', DateTime, default=datetime.now, onupdate=datetime.now),
    Column('dialogue_state', Text, nullable=True),  # JSON格式存储对话状态
    Column('has_offered', Integer, default=0),  # 0: False, 1: True
)

# 定义 messages 表
messages = Table(
    'messages',
    metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('conversation_id', String(36), ForeignKey('conversations.id'), nullable=False),
    Column('role', String(20), nullable=False),  # user 或 assistant
    Column('content', Text, nullable=False),
    Column('created_at', DateTime, default=datetime.now),
)


class Database:
    """数据库操作类"""
    
    def __init__(self, db_url: str = "sqlite:///dialogue.db"):
        """
        初始化数据库连接
        :param db_url: 数据库连接URL
        """
        # 创建数据库引擎
        connect_args = {}
        if db_url.startswith("sqlite"):
            # SQLite 特殊配置
            connect_args = {
                "check_same_thread": False,
            }
        
        self.engine = create_engine(
            db_url,
            connect_args=connect_args,
            poolclass=StaticPool if db_url.startswith("sqlite") else None,
            echo=False
        )
        
        # 创建所有表
        metadata.create_all(self.engine)
    
    def create_conversation(self) -> str:
        """
        创建新的会话
        :return: 会话ID
        """
        conversation_id = str(uuid.uuid4())
        
        with self.engine.connect() as conn:
            stmt = insert(conversations).values(
                id=conversation_id,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                dialogue_state=json.dumps({"nlu_semantics": None, "record": None}),
                has_offered=0
            )
            conn.execute(stmt)
            conn.commit()
        
        return conversation_id
    
    def get_all_conversations(self) -> list:
        """
        获取所有会话列表
        :return: 会话列表
        """
        with self.engine.connect() as conn:
            stmt = select(conversations)
            results = conn.execute(stmt).fetchall()
            
            return [
                {
                    "id": row.id,
                    "created_at": row.created_at,
                    "updated_at": row.updated_at,
                    "dialogue_state": json.loads(row.dialogue_state) if row.dialogue_state else None,
                    "has_offered": bool(row.has_offered)
                }
                for row in results
            ]
            
    def get_conversation(self, conversation_id: str) -> dict:
        """
        获取会话信息
        :param conversation_id: 会话ID
        :return: 会话信息字典
        """
        with self.engine.connect() as conn:
            stmt = select(conversations).where(conversations.c.id == conversation_id)
            result = conn.execute(stmt).fetchone()
            
            if result is None:
                return None
            
            return {
                "id": result.id,
                "created_at": result.created_at,
                "updated_at": result.updated_at,
                "dialogue_state": json.loads(result.dialogue_state) if result.dialogue_state else None,
                "has_offered": bool(result.has_offered)
            }
    
    def update_conversation_state(self, conversation_id: str, dialogue_state: dict, has_offered: bool):
        """
        更新会话状态
        :param conversation_id: 会话ID
        :param dialogue_state: 对话状态字典
        :param has_offered: 是否已推荐
        """
        with self.engine.connect() as conn:
            stmt = update(conversations).where(
                conversations.c.id == conversation_id
            ).values(
                dialogue_state=json.dumps(dialogue_state),
                has_offered=1 if has_offered else 0,
                updated_at=datetime.now()
            )
            conn.execute(stmt)
            conn.commit()
    
    def add_message(self, conversation_id: str, role: str, content: str):
        """
        添加消息到会话
        :param conversation_id: 会话ID
        :param role: 角色 (user 或 assistant)
        :param content: 消息内容
        """
        with self.engine.connect() as conn:
            stmt = insert(messages).values(
                conversation_id=conversation_id,
                role=role,
                content=content,
                created_at=datetime.now()
            )
            conn.execute(stmt)
            conn.commit()
    
    def get_messages(self, conversation_id: str) -> list:
        """
        获取会话的所有消息
        :param conversation_id: 会话ID
        :return: 消息列表
        """
        with self.engine.connect() as conn:
            stmt = select(messages).where(
                messages.c.conversation_id == conversation_id
            ).order_by(messages.c.created_at)
            
            results = conn.execute(stmt).fetchall()
            
            return [
                {
                    "id": row.id,
                    "role": row.role,
                    "content": row.content,
                    "created_at": row.created_at
                }
                for row in results
            ]
    
    def get_chat_history(self, conversation_id: str) -> list:
        """
        获取会话的聊天历史（格式化为对话管理器所需格式）
        :param conversation_id: 会话ID
        :return: 聊天历史列表
        """
        messages_list = self.get_messages(conversation_id)
        return [
            {"role": msg["role"], "content": msg["content"]}
            for msg in messages_list
        ]
