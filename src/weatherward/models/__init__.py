"""衣服档案数据模型"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ClothingProfile:
    """单件衣服的结构化档案"""

    file: str
    file_hash: str
    category: str
    type: str
    color: list[str] = field(default_factory=list)
    material: str = ""
    season: list[str] = field(default_factory=list)
    style: list[str] = field(default_factory=list)
    warmth: int = 3
    formality: int = 3
    waterproof: bool = False
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "file": self.file,
            "file_hash": self.file_hash,
            "category": self.category,
            "type": self.type,
            "color": self.color,
            "material": self.material,
            "season": self.season,
            "style": self.style,
            "warmth": self.warmth,
            "formality": self.formality,
            "waterproof": self.waterproof,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ClothingProfile":
        return cls(
            file=data["file"],
            file_hash=data.get("file_hash", ""),
            category=data.get("category", ""),
            type=data.get("type", ""),
            color=data.get("color", []),
            material=data.get("material", ""),
            season=data.get("season", []),
            style=data.get("style", []),
            warmth=data.get("warmth", 3),
            formality=data.get("formality", 3),
            waterproof=data.get("waterproof", False),
            description=data.get("description", ""),
        )

    def brief(self) -> str:
        colors = "/".join(self.color) if self.color else "未知颜色"
        styles = "/".join(self.style) if self.style else ""
        seasons = "/".join(self.season) if self.season else ""
        return (
            f"[{self.file}] {colors}{self.type}"
            f"（{self.material}，{styles}，适合{seasons}，"
            f"保暖{self.warmth}/5，正式{self.formality}/5）"
        )
