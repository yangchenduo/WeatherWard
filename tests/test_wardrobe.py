"""衣橱服务测试"""

import pytest
from pathlib import Path
from PIL import Image
import io

from weatherward.services.wardrobe import WardrobeService, ClothingItem


class TestClothingItem:
    """ClothingItem 数据类测试"""

    def test_create_clothing_item(self, tmp_path):
        """测试创建衣服项目"""
        # 创建测试图片
        img_path = tmp_path / "test_shirt.jpg"
        img = Image.new("RGB", (100, 100), color="red")
        img.save(img_path)

        item = ClothingItem(path=img_path, name="test_shirt.jpg")

        assert item.path == img_path
        assert item.name == "test_shirt.jpg"
        assert item.exists()

    def test_clothing_item_not_exists(self):
        """测试不存在的衣服项目"""
        item = ClothingItem(path=Path("/nonexistent/shirt.jpg"), name="shirt.jpg")

        assert not item.exists()

    def test_get_mime_type(self, tmp_path):
        """测试获取 MIME 类型"""
        # 创建不同格式的测试图片
        formats = {
            "test.jpg": "image/jpeg",
            "test.jpeg": "image/jpeg",
            "test.png": "image/png",
            "test.webp": "image/webp",
            "test.gif": "image/gif",
            "test.bmp": "image/bmp",
        }

        for filename, expected_mime in formats.items():
            img_path = tmp_path / filename
            img = Image.new("RGB", (100, 100))
            img.save(img_path)

            item = ClothingItem(path=img_path, name=filename)
            assert item.get_mime_type() == expected_mime


class TestWardrobeService:
    """WardrobeService 测试"""

    def test_scan_empty_folder(self, tmp_path):
        """测试扫描空文件夹"""
        service = WardrobeService()
        items = service.scan(tmp_path)

        assert items == []

    def test_scan_folder_with_images(self, tmp_path):
        """测试扫描包含图片的文件夹"""
        # 创建测试图片
        for i in range(3):
            img_path = tmp_path / f"shirt_{i}.jpg"
            img = Image.new("RGB", (100, 100))
            img.save(img_path)

        service = WardrobeService()
        items = service.scan(tmp_path)

        assert len(items) == 3
        assert all(isinstance(item, ClothingItem) for item in items)

    def test_scan_ignores_non_image_files(self, tmp_path):
        """测试忽略非图片文件"""
        # 创建图片文件
        img_path = tmp_path / "shirt.jpg"
        img = Image.new("RGB", (100, 100))
        img.save(img_path)

        # 创建非图片文件
        (tmp_path / "readme.txt").write_text("This is a readme")
        (tmp_path / "data.json").write_text("{}")

        service = WardrobeService()
        items = service.scan(tmp_path)

        assert len(items) == 1
        assert items[0].name == "shirt.jpg"

    def test_scan_with_subdirectories(self, tmp_path):
        """测试扫描包含子目录的文件夹"""
        # 创建子目录
        tops_dir = tmp_path / "tops"
        tops_dir.mkdir()
        pants_dir = tmp_path / "pants"
        pants_dir.mkdir()

        # 在子目录中创建图片
        for i in range(2):
            img_path = tops_dir / f"shirt_{i}.jpg"
            img = Image.new("RGB", (100, 100))
            img.save(img_path)

        for i in range(2):
            img_path = pants_dir / f"pants_{i}.jpg"
            img = Image.new("RGB", (100, 100))
            img.save(img_path)

        service = WardrobeService()
        items = service.scan(tmp_path)

        assert len(items) == 4

    def test_scan_nonexistent_folder(self):
        """测试扫描不存在的文件夹"""
        service = WardrobeService()

        with pytest.raises(FileNotFoundError):
            service.scan(Path("/nonexistent/folder"))

    def test_scan_not_a_directory(self, tmp_path):
        """测试扫描非目录路径"""
        file_path = tmp_path / "file.txt"
        file_path.write_text("test")

        service = WardrobeService()

        with pytest.raises(NotADirectoryError):
            service.scan(file_path)


class TestWardrobeServiceImageLoading:
    """图片加载测试"""

    def test_load_image_as_base64(self, tmp_path):
        """测试加载图片为 Base64"""
        # 创建测试图片
        img_path = tmp_path / "test.jpg"
        img = Image.new("RGB", (100, 100), color="red")
        img.save(img_path)

        service = WardrobeService()
        item = ClothingItem(path=img_path, name="test.jpg")
        base64_str = service.load_image_as_base64(item)

        assert base64_str
        assert isinstance(base64_str, str)
        # Base64 字符串应该是有效的
        import base64
        try:
            base64.b64decode(base64_str)
        except Exception:
            pytest.fail("Invalid Base64 string")

    def test_load_image_as_base64_with_compression(self, tmp_path):
        """测试加载图片并压缩"""
        # 创建大图片
        img_path = tmp_path / "large.jpg"
        img = Image.new("RGB", (2000, 2000), color="blue")
        img.save(img_path, quality=95)

        service = WardrobeService()
        item = ClothingItem(path=img_path, name="large.jpg")

        # 加载并压缩
        base64_str = service.load_image_as_base64(item, max_size_mb=1)

        assert base64_str
        # 验证压缩后的大小
        import base64
        decoded = base64.b64decode(base64_str)
        assert len(decoded) <= 1 * 1024 * 1024  # 1MB


class TestWardrobeServiceGetClothesDescription:
    """获取衣服描述测试"""

    def test_get_clothes_description(self, tmp_path):
        """测试获取衣服描述列表"""
        # 创建测试图片
        for i in range(3):
            img_path = tmp_path / f"item_{i}.jpg"
            img = Image.new("RGB", (100, 100))
            img.save(img_path)

        service = WardrobeService()
        items = service.scan(tmp_path)
        description = service.get_clothes_description(items)

        assert isinstance(description, str)
        assert "item_0.jpg" in description
        assert "item_1.jpg" in description
        assert "item_2.jpg" in description

    def test_get_clothes_description_empty(self):
        """测试空衣橱描述"""
        service = WardrobeService()
        description = service.get_clothes_description([])

        assert "没有" in description or "空" in description or description == ""
