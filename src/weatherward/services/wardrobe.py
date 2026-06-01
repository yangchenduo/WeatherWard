"""衣橱服务 - 管理本地衣服图片"""

import base64
import io
from dataclasses import dataclass
from pathlib import Path

from PIL import Image


@dataclass
class ClothingItem:
    """衣服项目"""

    path: Path
    name: str

    def exists(self) -> bool:
        """检查文件是否存在"""
        return self.path.exists()

    def get_mime_type(self) -> str:
        """获取 MIME 类型"""
        suffix = self.path.suffix.lower()
        mime_map = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp",
            ".gif": "image/gif",
            ".bmp": "image/bmp",
        }
        return mime_map.get(suffix, "image/jpeg")


class WardrobeService:
    """衣橱服务"""

    SUPPORTED_FORMATS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}

    def scan(self, folder_path: Path) -> list[ClothingItem]:
        """
        扫描文件夹中的衣服图片

        Args:
            folder_path: 文件夹路径

        Returns:
            衣服项目列表

        Raises:
            FileNotFoundError: 文件夹不存在
            NotADirectoryError: 路径不是目录
        """
        if not folder_path.exists():
            raise FileNotFoundError(f"Folder not found: {folder_path}")

        if not folder_path.is_dir():
            raise NotADirectoryError(f"Not a directory: {folder_path}")

        items = []
        for file_path in folder_path.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in self.SUPPORTED_FORMATS:
                items.append(ClothingItem(path=file_path, name=file_path.name))

        return items

    def load_image_as_base64(
        self,
        item: ClothingItem,
        max_size_mb: float = 50.0,
    ) -> str:
        """
        加载图片并转换为 Base64

        Args:
            item: 衣服项目
            max_size_mb: 最大文件大小（MB）

        Returns:
            Base64 编码的图片字符串
        """
        img = Image.open(item.path)

        # 如果需要压缩
        if item.path.stat().st_size > max_size_mb * 1024 * 1024:
            img = self._compress_image(img, max_size_mb)

        # 转换为 RGB（如果是 RGBA）
        if img.mode == "RGBA":
            img = img.convert("RGB")

        # 保存为 JPEG 字节流
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=85)
        img_bytes = buffer.getvalue()

        return base64.b64encode(img_bytes).decode("utf-8")

    def _compress_image(self, img: Image.Image, max_size_mb: float) -> Image.Image:
        """压缩图片到指定大小"""
        # 计算目标大小（字节）
        target_size = int(max_size_mb * 1024 * 1024 * 0.9)  # 留 10% 余量

        # 如果图片太大，缩小尺寸
        width, height = img.size
        while width * height * 3 > target_size:  # 3 bytes per pixel (RGB)
            width = int(width * 0.8)
            height = int(height * 0.8)

        return img.resize((width, height), Image.Resampling.LANCZOS)

    def get_clothes_description(self, items: list[ClothingItem]) -> str:
        """
        获取衣服列表的描述

        Args:
            items: 衣服项目列表

        Returns:
            描述字符串
        """
        if not items:
            return "衣橱为空，没有找到衣服图片。"

        descriptions = []
        for i, item in enumerate(items, 1):
            descriptions.append(f"{i}. {item.name}")

        return "衣橱中的衣服：\n" + "\n".join(descriptions)
