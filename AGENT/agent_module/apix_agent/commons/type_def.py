from typing import Any, NotRequired, Required, TypedDict, Annotated, Literal
import operator
from langchain_core.messages import AnyMessage 
from langchain.agents.middleware.todo import Todo

#提供商未找到异常类，用于在代理运行时处理特定的错误情况，
class ProviderNotFound(Exception):
    
    def __init__(self, message="Custom provider not found.", provider=None):
        """        
        Args:
            message: error message
            errors: error object
        """
        self.message = message
        self.errors = provider if provider else ''
        super().__init__(self.message)
    
    def __str__(self):
        error_details = f"Errors: {self.errors}" if self.errors else ""
        return f"{self.message}{error_details}"

#平台未注册异常类，用于在代理运行时处理特定的错误情况，
class PlatformNotRegister(Exception):
    
    def __init__(self, message="Platform not register error.", platform=None):
        """        
        Args:
            message: error message
            errors: error object
        """
        self.message = message
        self.errors = platform if platform else ''
        super().__init__(self.message)
    
    def __str__(self):
        error_details = f"Errors: {self.errors}" if self.errors else ""
        return f"{self.message}{error_details}"

#工具调用冲突异常类，用于在代理运行时处理特定的错误情况，
class ConflictToolCalls(Exception):
    
    def __init__(self, message="Invalid tool calls detected", errors=None):
        """        
        Args:
            message: error message
            errors: error object
        """
        self.message = message
        self.errors = errors if errors else []
        super().__init__(self.message)
    
    def __str__(self):
        error_details = f"Errors: {self.errors}" if self.errors else ""
        return f"{self.message}{error_details}"

#无效输出异常类
class InvalidOutputsError(Exception):
    
    def __init__(self, message="Invalid outputs detected", errors=None):
        """        
        Args:
            message: error message
            errors: error object
        """
        self.message = message
        self.errors = errors if errors else []
        super().__init__(self.message)
    
    def __str__(self):
        error_details = f"Errors: {self.errors}" if self.errors else ""
        return f"{self.message}{error_details}"
    

# Role mode in GraphRuntimeContext:

# - agent:
#   Normal role. This agent chats directly with the user,
#   but does not have permission to assign a sub-agent.

# - main_agent:
#   Main agent role. This agent chats directly with the user
#   and has permission to assign one sub-agent per user request.

# - sub_agent:
#   Sub-agent role. This agent does not chat directly with the user
#   and has no permission to assign sub-agents. It acts as a task executor for a main agent.

# - team_leader:
#   Main agent role. This agent chats directly with the user
#   and has permission to assign multiple sub-agents per user request.

# - team_worker:
#   Sub-agent role. This agent does not chat directly with the user
#   and has no permission to assign sub-agents. It acts as a task executor in an agent team.


#用户身份标识 贯穿整个事件系统，标识"这条消息发给谁"
class ApixIdentity(TypedDict):
    id: str 
    platform: str #"default" / "websocket" / "webhook"
    conversation_id: str | None # history_id
    associated_account: NotRequired[dict]

#角色定义 agent的名字，角色描述 在 create_role_prompt_list() 中拼接到 prompt 中
class RoleSchema(TypedDict):
    name: str
    definition: str

#备忘录目录 以yaml文件存储在 running_cache/memo/xia,按sha256（namespace）命名
class MemoItem(TypedDict):
    title: str
    date: str # 2025-06-07
    content: str
    source: Literal["conversation", "workspace"]

#agent完整配置， 流转路径，前端发送-> webSocket -> _ensure_config() 合并缓存-> 
# 传入MainAgentState.config ->各个节点读取
class AgentConfigSchema(TypedDict):
    """
    Config for a single AI agent.
    """

    # User / Session Info 用户信息
    client_id: st
    session_id: str
    history_id: str
    platform: str

    # LLM Runtime llm运行时
    models_provider: str
    model_name: str
    api_key: str
    model_temperature: float
    custom_provider_id: NotRequired[str]

    enable_think: bool
    llm_calls_warning_threshold: int
    use_model_vision: bool  # If true, the picture will be sent to the LLM to analyze if the LLM supports picture input.


    # Agent Runtime Behavior 行为
    work_dir: str
    keep_tools_message: bool  # If true, async returns will save to database.
    pure_chat_on: bool  # If true, the agent will be a simple LLM without tools.


    # Memory Strategy 记忆策略
    enable_longterm_memory: bool
    enable_shortterm_memory: bool  # If is true, message_summary node will invoke llm to compress else just truncate.
    summary_trigger_threshold: int  # If zero, not compress or truncate.
    summary_exempt_tail_length: int


    # Capabilities / Tools 能力开关，每一个开关对应一个工具权限组
    enable_file_opration: bool
    enable_web_search: bool
    enable_knowledge_retrieval: bool
    enable_command_opration: bool
    enable_skill_load: bool
    enable_task_flow: bool
    enable_agent_assign: bool
    enable_agent_swarm: bool


    # External Services 外部服务，搜索，嵌入，清洗的服务提供商和API Key
    link_provider: str
    link_api_key: str
    content_provider: str
    content_api_key: str
    embed_model: str  # The embed model for knowledge retrieval.
    web_cleaner_mode: str
    auto_save_config: bool  # If true, the agent config will auto save when changed.


    # Agent Identity / Prompt
    role_prompt: RoleSchema
    higher_role_prompt_permission: bool  # If true, the role prompt will insert into system prompt.

# WebSocket消息体
class ApixPayloadSchema(TypedDict):
    client_id: str
    session_id: str
    history_id: str
    platform: str
    messages: dict
    re_generate: bool
    config: AgentConfigSchema

# WebSocket完整消息
class ApixEntryDataSchema(TypedDict):
    action: str
    data: ApixPayloadSchema | Any

# 状态类型 -图运行时共享上下文，所有agent图节点的公共基类，定义了图运行中每个节点都能访问的字段：
class GraphRuntimeContext(TypedDict):
    agent_name: str
    agent_role: Literal["team_leader", "team_worker", "main_agent", "sub_agent", "agent"]
    client_id: str
    session_id: NotRequired[str]
    history_id: str
    target: ApixIdentity
    generation_id: str
    node_id: NotRequired[str]
    parent_node_id: NotRequired[str]
    config: AgentConfigSchema
    timestamp: int

#主要agent的完整状态 继承自 GraphRuntimeContext，包含了主要agent在运行时的所有状态信息：
class MainAgentState(GraphRuntimeContext):
    input: dict
    re_generate: bool
    messages: Annotated[list[AnyMessage], operator.add]
    # LangGraph 特有语法：每次节点返回 {"messages": [new_msg]} 时，
    # LangGraph 会自动 append 而不是 replace！
    current_tool_calls: list
    longterm_memory: str # Cross-conversation longterm memory 中文：跨对话长期记忆
    shortterm_memory: str # Recent summary of conversation 中文：近期对话摘要   
    rule_prompt: str
    runtime_prompt: str # Include todos prompt, workspace prompt, memorandum prompt and so on   
    llm_calls: Annotated[int, operator.add] # 每个节点返回 {"llm_calls": 1} 时，自动累加
    llm_retry_count: int
    error: NotRequired[str] # Error type
    error_detail: NotRequired[str] # Error detail
    context_compress_level: int # Level 0: Not compress; 
    #Level 1: Drop tool message content; 
    # Level 2: Context sumary to summary_exempt_tail_length; 
    context_fold_split_mark: NotRequired[str] # Split by completed | in_progress & pending todos, store with message id
    sandbox: str # Docker container id
    todos: NotRequired[list[Todo]]
    memorandum: NotRequired[list[MemoItem]]
    skills: list # Include available skills name and description
    loaded_skills_cache: list[tuple[str, bool, str]] # (name, injected, content): Skill name, injection status, and SKILL.md content
    documents: list # Include available documents name and description

#子Agent状态 继承自 MainAgentState，外加任务管理字段：
class SubAgentState(MainAgentState):
    final_goal: str        #子任务目标
    task_id: str
    parent_task_id: str
    start_timestamp: int    
    finish_timestamp: int
    status: Literal["in_progress", "completed", "pending", "failed", "cancelled"] #进展
    outputs: Annotated[str, operator.add]   #累加输出
    errors: Annotated[str, operator.add] #累加错误

#事件载荷 
class MinimalEnvelopeData(TypedDict, total=False):
    event_name: Required[str]  # 如 "content_chunk_rtn", "tool_exec_chunk_rtn"
    content: Required[Any] # Serializable object 事件携带的数据

#完整事件信封
class ApixEventEnvelope(TypedDict):
    event: str  # AgentStreamEvent 枚举值
    target: NotRequired[ApixIdentity]   #接受方
    generation_id: NotRequired[str] #归属的生成ID
    data: MinimalEnvelopeData          # 实际内容
    timestamp: float
    blocking: NotRequired[bool]     #是否为阻塞事件
    block_id: NotRequired[str]  # 阻塞事件的唯一ID

