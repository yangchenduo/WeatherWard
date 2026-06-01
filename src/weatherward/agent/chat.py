"""衣橱助手 Agent - 基于 LangChain 的对话式 Agent"""

from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.language_models import BaseChatModel

from weatherward.config import Settings
from weatherward.services.llm import create_llm
from weatherward.agent.tools import configure, get_tools

MAX_TOOL_ITERATIONS = 10


SYSTEM_PROMPT_TEMPLATE = """你是 WeatherWard 智能衣橱助手。

## 核心规则
**你必须使用工具来回答问题，禁止使用通用知识猜测。**

## 可用工具
1. `get_weather` - 查询天气
2. `scan_wardrobe` - 查看衣橱里有哪些衣服
3. `recommend_outfit` - 根据天气+衣橱推荐穿搭

## 行为规范
- 用户问"今天穿什么"/"怎么搭配" → 必须调用 `recommend_outfit`
- 用户问"天气怎么样" → 必须调用 `get_weather`
- 用户问"我有什么衣服" → 必须调用 `scan_wardrobe`
- 闲聊时可以正常对话，但涉及穿搭/天气/衣橱时必须用工具

用户的默认城市是：{default_city}。当用户问"今天穿什么"但没有指定城市时，直接使用默认城市，不需要追问。

请用中文回答，语气友好自然。"""


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

        iterations = 0
        while response.tool_calls:
            iterations += 1
            if iterations > MAX_TOOL_ITERATIONS:
                self.messages.append(HumanMessage(
                    content="工具调用次数过多，请直接给出最终回答。"
                ))
                response = await self.agent_llm.ainvoke(self.messages)
                self.messages.append(response)
                break

            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]

                try:
                    if tool_name in self.tools_map:
                        tool_result = await self.tools_map[tool_name].ainvoke(tool_args)
                    else:
                        tool_result = f"未知工具: {tool_name}"
                except Exception as e:
                    tool_result = f"工具执行出错: {e}"

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
