"""搭配审查链 - AI 对推荐的搭配进行合理性校验"""

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage

from weatherward.models import ClothingProfile


REVIEW_PROMPT = """你是一个专业的服装搭配审查师。请审查以下搭配推荐是否合理。

## 当前天气
{weather_summary}

## 推荐的搭配
{outfit_description}

## 审查要点
请检查以下方面，判断这套搭配是否存在问题：

1. **逻辑冲突**：是否有不合逻辑的组合？例如：
   - 旗袍/连衣裙 + 另一条裤子或裙子（套装类不应再搭下装）
   - 西装上衣 + 运动裤（风格严重不搭）
   - 背心 + 羽绒服（保暖等级矛盾）
   
2. **风格一致性**：整体风格是否协调？

3. **温度适配**：搭配的保暖程度是否与天气匹配？

4. **颜色搭配**：颜色组合是否和谐？

## 返回格式
请严格返回以下 JSON 格式：

```json
{{
  "approved": true或false,
  "issues": ["问题1", "问题2"],
  "suggestion": "如果不通过，给出修改建议。通过则为空字符串。"
}}
```

只返回 JSON，不要有其他文字。"""


class OutfitReviewer:
    def __init__(self, llm: BaseChatModel):
        self.llm = llm

    async def review(
        self,
        outfit_profiles: list[ClothingProfile],
        weather_summary: str,
    ) -> dict:
        outfit_desc = "\n".join(
            f"- {p.brief()}" for p in outfit_profiles
        )

        prompt = REVIEW_PROMPT.format(
            weather_summary=weather_summary,
            outfit_description=outfit_desc,
        )

        message = HumanMessage(content=prompt)
        response = await self.llm.ainvoke([message])

        return self._parse_response(response.content)

    def _parse_response(self, text: str) -> dict:
        import json

        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:])
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

        try:
            result = json.loads(text)
            return {
                "approved": result.get("approved", True),
                "issues": result.get("issues", []),
                "suggestion": result.get("suggestion", ""),
            }
        except json.JSONDecodeError:
            pass

        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                result = json.loads(text[start:end])
                return {
                    "approved": result.get("approved", True),
                    "issues": result.get("issues", []),
                    "suggestion": result.get("suggestion", ""),
                }
            except json.JSONDecodeError:
                pass

        return {"approved": False, "issues": ["审查结果解析失败"], "suggestion": "请重试"}
