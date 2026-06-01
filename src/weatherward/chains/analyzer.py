"""衣服分析链 - 分析衣服图片"""

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage


class ClothingAnalyzer:
    """分析衣服图片的 Chain"""

    def __init__(self, llm: BaseChatModel):
        """
        初始化分析器

        Args:
            llm: LLM 实例
        """
        self.llm = llm

    async def analyze(self, images_base64: list[str]) -> str:
        """
        分析多张衣服图片

        Args:
            images_base64: Base64 编码的图片列表

        Returns:
            衣服描述

        Raises:
            ValueError: 图片列表为空
        """
        if not images_base64:
            raise ValueError("至少需要一张图片")

        # 构建多图片消息
        content = [
            {
                "type": "text",
                "text": (
                    "请详细描述这些衣服的特征，包括：\n"
                    "1. 款式（T恤、衬衫、裤子、外套等）\n"
                    "2. 颜色\n"
                    "3. 材质（棉、麻、化纤等）\n"
                    "4. 适合的季节\n"
                    "5. 风格（休闲、正式、运动等）\n"
                    "请用中文回答，每件衣服单独描述。"
                ),
            }
        ]

        for img_b64 in images_base64:
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"},
                }
            )

        message = HumanMessage(content=content)
        response = await self.llm.ainvoke([message])

        return response.content
