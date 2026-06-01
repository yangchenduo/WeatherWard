"""搭配推荐链 - 根据天气和衣橱推荐穿搭"""

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage


class OutfitStylist:
    """搭配推荐 Chain"""

    PROMPT_TEMPLATE = """你是一个专业的服装搭配师。根据以下信息推荐今天的穿搭：

## 天气信息
- 城市：{city}
- 温度：{temp}°C（体感：{feels_like}°C）
- 天气：{weather}
- 湿度：{humidity}%
- 风速：{wind_speed}m/s

## 可选衣服
{clothing_list}

## 用户偏好
{preference}

请推荐一套完整的穿搭，包括：
1. 上衣
2. 下装
3. 外套（如需要）
4. 鞋子建议
5. 搭配理由（结合天气）
6. 搭配小贴士

请用中文回答，格式清晰。"""

    def __init__(self, llm: BaseChatModel):
        self.llm = llm

    async def recommend(
        self,
        weather: dict,
        clothing_list: str,
        preference: str,
    ) -> str:
        prompt_text = self.PROMPT_TEMPLATE.format(
            city=weather["city"],
            temp=weather["temp"],
            feels_like=weather["feels_like"],
            weather=weather["weather"],
            humidity=weather["humidity"],
            wind_speed=weather["wind_speed"],
            clothing_list=clothing_list,
            preference=preference or "无特殊偏好",
        )

        message = HumanMessage(content=prompt_text)
        response = await self.llm.ainvoke([message])

        # 兼容 AIMessage 和字符串返回
        if hasattr(response, "content"):
            return response.content
        return str(response)
