from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.memory import ConversationBufferMemory
from core.config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL
from core.tools import ALL_TOOLS
from core.rag import rag_search
from core.prompts import SYSTEM_PROMPT
from core.database import init_db

_all_tools = ALL_TOOLS + [rag_search]


def create_agent():
    """创建并返回 AgentExecutor 实例。"""
    if not DEEPSEEK_API_KEY:
        raise ValueError(
            "DEEPSEEK_API_KEY 未设置！请复制 .env.example 为 .env 并填入你的 API Key。"
        )

    init_db()

    llm = ChatOpenAI(
        model=DEEPSEEK_MODEL,
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
        temperature=0,
        max_tokens=1024,
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    memory = ConversationBufferMemory(
        memory_key="chat_history",
        return_messages=True,
        output_key="output",
    )

    agent = create_tool_calling_agent(llm, _all_tools, prompt)

    executor = AgentExecutor(
        agent=agent,
        tools=_all_tools,
        memory=memory,
        verbose=True,
        max_iterations=8,
        handle_parsing_errors=True,
    )

    return executor


_agent_instance = None


def get_agent():
    """单例模式获取 Agent 实例。"""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = create_agent()
    return _agent_instance


def chat(user_input: str) -> str:
    """便捷方法：发送消息给 Agent 并返回回复。"""
    agent = get_agent()
    result = agent.invoke({"input": user_input})
    return result.get("output", "抱歉，我无法处理这个请求。")