# 导入 LangChain 对接 OpenAI 聊天模型的官方工具
from langchain_openai import ChatOpenAI

# 导入你之前写的配置工具，用来读取密钥、模型名等参数
from meeting_agent.config import get_settings

# 定义函数：返回一个初始化好的 AI 模型对象（ChatOpenAI）
def get_llm() -> ChatOpenAI:
    # 1. 读取 .env 里的所有配置（API Key、Base URL、模型名...）
    settings = get_settings()

    # 2. 创建并返回一个配置好的大模型实例
    return ChatOpenAI(
        # 使用哪个模型：gpt-3.5-turbo / gpt-4o 等
        model=settings.model_name,
        # API 密钥（验证身份）
        api_key=settings.openai_api_key,
        # 接口地址（国内访问必须配置）
        base_url=settings.openai_base_url,
        # 温度参数：0.2 保证输出稳定、严谨
        temperature=settings.temperature,
    )