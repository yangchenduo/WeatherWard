"""LLM 工厂 - 根据配置创建不同的 LLM 实例"""

from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI

from weatherward.config import ModelConfig


def create_llm(config: ModelConfig) -> BaseChatModel:
    """
    根据配置创建 LLM 实例

    Args:
        config: 模型配置

    Returns:
        LLM 实例

    Raises:
        ValueError: 未知的提供商
    """
    if config.provider == "mimo":
        return ChatOpenAI(
            model=config.model_id,
            api_key=config.api_key,
            base_url=config.base_url,
            max_tokens=config.max_tokens,
        )
    elif config.provider == "deepseek":
        # DeepSeek 使用 OpenAI 兼容接口
        return ChatOpenAI(
            model=config.model_id or "deepseek-chat",
            api_key=config.api_key,
            base_url="https://api.deepseek.com/v1",
            max_tokens=config.max_tokens,
        )
    elif config.provider == "minimax":
        return ChatOpenAI(
            model=config.model_id or "minimax-text-01",
            api_key=config.api_key,
            base_url=config.base_url or "https://api.minimax.chat/v1",
            max_tokens=config.max_tokens,
        )
    else:
        raise ValueError(f"Unknown provider: {config.provider}")
