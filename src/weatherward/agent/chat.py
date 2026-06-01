"""衣橱助手 Agent - 基于 LangChain 的对话式 Agent"""

from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.language_models import BaseChatModel

from weatherward.config import Settings
from weatherward.services.llm import create_llm
from weatherward.agent.tools import configure, get_tools


SYSTEM_PROMPT_TEMPLATE = """你是 WeatherWard 智能衣橱助手。你可以帮助用户：

1. 查询任意城市的天气
2. 扫描和分析用户衣橱中的衣服
3. 根据天气和衣橱推荐今日穿搭

用户的默认城市是：{default_city}。当用户问"今天穿什么"但没有指定城市时，直接使用默认城市，不需要追问。

请用中文回答，语气友好自然。如果用户只是闲聊，也可以正常对话。"""


class WardrobeAgent:
    def __init__(self, settings: Settings, wardrobe_path: Path | None = None):
        self.settings = settings
        self.wardrobe_path = wardrobe_path
        self.default_city = settings.weather.default_city
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
            default_city=self.default_city,
        )
        self.messages: list = [SystemMessage(content=system_prompt)]

        configure(settings, wardrobe_path)

        self.llm = create_llm(settings.model)
        tools = get_tools()
        self.agent_llm = self.llm.bind_tools(tools)
        self.tools_map = {t.name: t for t in tools}

    async def chat(self, user_input: str) -> str:
        self.messages.append(HumanMessage(content=user_input))

        response = await self.agent_llm.ainvoke(self.messages)
        self.messages.append(response)

        while response.tool_calls:
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]

                if tool_name in self.tools_map:
                    tool_result = await self.tools_map[tool_name].ainvoke(tool_args)
                else:
                    tool_result = f"未知工具: {tool_name}"

                from langchain_core.messages import ToolMessage
                tool_msg = ToolMessage(
                    content=str(tool_result),
                    tool_call_id=tool_call["id"],
                )
                self.messages.append(tool_msg)

            response = await self.agent_llm.ainvoke(self.messages)
            self.messages.append(response)

        return response.content

    def reset(self) -> None:
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
            default_city=self.default_city,
        )
        self.messages = [SystemMessage(content=system_prompt)]
