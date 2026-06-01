"""搭配推荐链 - 根据天气和衣橱推荐穿搭"""

import json

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage

from weatherward.models import ClothingProfile


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

    INDEXED_PROMPT_TEMPLATE = """你是一个专业的服装搭配师。根据以下信息从用户衣橱中推荐今天的穿搭：

## 天气信息
- 城市：{city}
- 温度：{temp}°C（体感：{feels_like}°C）
- 天气：{weather}
- 湿度：{humidity}%
- 风速：{wind_speed}m/s

## 用户衣橱（候选衣服）
{clothing_list}

## 用户偏好
{preference}

## 重要规则
1. 只能从上面的候选衣服中选择，不能推荐没有的衣服
2. "套装"类（如旗袍、连衣裙）是上下一体的，选了就不需要另选下装
3. 注意风格协调性，不要混搭冲突的风格

请严格按以下 JSON 格式返回：

```json
{{
  "selected_files": ["选中的衣服文件名1", "文件名2", ...],
  "recommendation": "用 Markdown 格式的穿搭推荐说明，包含搭配理由和小贴士"
}}
```

只返回 JSON，不要有其他文字。"""

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

        if hasattr(response, "content"):
            return response.content
        return str(response)

    async def recommend_from_index(
        self,
        weather: dict,
        candidates: list[ClothingProfile],
        preference: str,
    ) -> dict:
        clothing_list = "\n".join(
            f"- {p.brief()}" for p in candidates
        )

        prompt_text = self.INDEXED_PROMPT_TEMPLATE.format(
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

        content = response.content if hasattr(response, "content") else str(response)
        return self._parse_indexed_response(content, candidates)

    def _parse_indexed_response(
        self, text: str, candidates: list[ClothingProfile]
    ) -> dict:
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:])
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

        try:
            result = json.loads(text)
            selected_files = result.get("selected_files", [])
            selected_profiles = [
                p for p in candidates if p.file in selected_files
            ]
            return {
                "selected_files": selected_files,
                "selected_profiles": selected_profiles,
                "recommendation": result.get("recommendation", ""),
            }
        except json.JSONDecodeError:
            pass

        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                result = json.loads(text[start:end])
                selected_files = result.get("selected_files", [])
                selected_profiles = [
                    p for p in candidates if p.file in selected_files
                ]
                return {
                    "selected_files": selected_files,
                    "selected_profiles": selected_profiles,
                    "recommendation": result.get("recommendation", ""),
                }
            except json.JSONDecodeError:
                pass

        return {
            "selected_files": [],
            "selected_profiles": [],
            "recommendation": text,
        }
