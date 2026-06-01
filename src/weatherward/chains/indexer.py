"""衣服索引链 - AI 分析图片生成结构化档案"""

import json

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage

from weatherward.models import ClothingProfile
from weatherward.services.wardrobe import WardrobeService, ClothingItem
from weatherward.services.index import WardrobeIndex


INDEXER_PROMPT = """你是一个服装分析专家。请分析以下衣服图片，为每件衣服生成结构化描述。

要求严格按照以下 JSON 格式返回，每件衣服对应数组中的一个对象：

```json
[
  {
    "category": "上衣/下装/外套/鞋子/配饰/套装",
    "type": "具体款式，如T恤、衬衫、牛仔裤、连衣裙、旗袍、西装外套等",
    "color": ["主色", "副色"],
    "material": "材质，如棉、麻、丝绸、化纤、牛仔、羊毛等",
    "season": ["春", "夏", "秋", "冬"],
    "style": ["休闲", "正式", "运动", "商务", "优雅", "街头"],
    "warmth": 1到5的整数（1=最凉爽如背心，5=最保暖如羽绒服），
    "formality": 1到5的整数（1=最休闲如运动裤，5=最正式如西装），
    "waterproof": true或false,
    "description": "一句话简述这件衣服的特点和适合场景"
  }
]
```

注意事项：
- category 必须是：上衣、下装、外套、鞋子、配饰、套装 之一
- 套装类（如旗袍、连衣裙）的 category 填"套装"，表示它是上下一体的
- season 数组中只填适合的季节
- 请确保返回的数组长度与图片数量一致
- 只返回 JSON，不要有其他文字"""


class ClothingIndexer:
    def __init__(self, llm: BaseChatModel):
        self.llm = llm

    async def analyze_batch(
        self,
        items: list[ClothingItem],
        wardrobe_service: WardrobeService,
    ) -> list[dict]:
        if not items:
            return []

        content: list[dict] = [
            {"type": "text", "text": INDEXER_PROMPT}
        ]

        for item in items:
            img_b64 = wardrobe_service.load_image_as_base64(item)
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"},
            })

        message = HumanMessage(content=content)
        response = await self.llm.ainvoke([message])

        return self._parse_response(response.content, len(items))

    def _parse_response(self, text: str, expected_count: int) -> list[dict]:
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:])
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

        try:
            result = json.loads(text)
            if isinstance(result, list):
                return result
        except json.JSONDecodeError:
            pass

        start = text.find("[")
        end = text.rfind("]") + 1
        if start >= 0 and end > start:
            try:
                result = json.loads(text[start:end])
                if isinstance(result, list):
                    return result
            except json.JSONDecodeError:
                pass

        return [{}] * expected_count

    async def index_items(
        self,
        items: list[ClothingItem],
        wardrobe_service: WardrobeService,
        batch_size: int = 3,
    ) -> list[ClothingProfile]:
        profiles: list[ClothingProfile] = []

        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            batch_results = await self.analyze_batch(batch, wardrobe_service)

            for item, result in zip(batch, batch_results):
                file_hash = WardrobeIndex._compute_hash(item.path)
                profile = ClothingProfile(
                    file=item.name,
                    file_hash=file_hash,
                    category=result.get("category", ""),
                    type=result.get("type", ""),
                    color=result.get("color", []),
                    material=result.get("material", ""),
                    season=result.get("season", []),
                    style=result.get("style", []),
                    warmth=result.get("warmth", 3),
                    formality=result.get("formality", 3),
                    waterproof=result.get("waterproof", False),
                    description=result.get("description", ""),
                )
                profiles.append(profile)

        return profiles
