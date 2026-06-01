"""衣橱索引管理 - 增量导入与删除检测"""

import hashlib
import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any

from weatherward.models import ClothingProfile
from weatherward.services.wardrobe import WardrobeService, ClothingItem


INDEX_FILENAME = ".wardrobe_index.json"
INDEX_VERSION = 1


class WardrobeIndex:
    def __init__(self, wardrobe_path: Path):
        self.wardrobe_path = wardrobe_path
        self.index_file = wardrobe_path / INDEX_FILENAME
        self.profiles: list[ClothingProfile] = []
        self._load()

    def _load(self) -> None:
        if self.index_file.exists():
            with open(self.index_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.profiles = [
                ClothingProfile.from_dict(item)
                for item in data.get("items", [])
            ]

    def save(self) -> None:
        data = {
            "version": INDEX_VERSION,
            "indexed_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "count": len(self.profiles),
            "items": [p.to_dict() for p in self.profiles],
        }
        tmp_fd, tmp_path = tempfile.mkstemp(
            dir=self.index_file.parent, suffix=".tmp"
        )
        try:
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, self.index_file)
        except Exception:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise

    def get_indexed_files(self) -> dict[str, str]:
        return {p.file: p.file_hash for p in self.profiles}

    def detect_changes(self) -> tuple[list[ClothingItem], list[str]]:
        wardrobe_service = WardrobeService()
        current_items = wardrobe_service.scan(self.wardrobe_path)

        indexed = self.get_indexed_files()
        current_files: dict[str, ClothingItem] = {}
        for item in current_items:
            current_files[item.name] = item

        new_items: list[ClothingItem] = []
        for name, item in current_files.items():
            if name not in indexed:
                new_items.append(item)
            else:
                current_hash = self._compute_hash(item.path)
                if current_hash != indexed[name]:
                    new_items.append(item)

        deleted_files: list[str] = []
        for name in indexed:
            if name not in current_files:
                deleted_files.append(name)

        return new_items, deleted_files

    def remove_deleted(self, deleted_files: list[str]) -> None:
        self.profiles = [
            p for p in self.profiles if p.file not in deleted_files
        ]

    def add_profiles(self, new_profiles: list[ClothingProfile]) -> None:
        existing_files = {p.file for p in self.profiles}
        for profile in new_profiles:
            if profile.file in existing_files:
                self.profiles = [
                    p for p in self.profiles if p.file != profile.file
                ]
            self.profiles.append(profile)

    def get_all_profiles(self) -> list[ClothingProfile]:
        return self.profiles

    def filter_by_season(self, season: str) -> list[ClothingProfile]:
        return [p for p in self.profiles if season in p.season]

    def filter_by_warmth(self, min_warmth: int, max_warmth: int) -> list[ClothingProfile]:
        return [
            p for p in self.profiles
            if min_warmth <= p.warmth <= max_warmth
        ]

    def filter_by_formality(self, min_formality: int) -> list[ClothingProfile]:
        return [p for p in self.profiles if p.formality >= min_formality]

    def filter_candidates(
        self,
        temp: float,
        weather: str,
        preference: str = "",
    ) -> list[ClothingProfile]:
        candidates = list(self.profiles)

        if temp > 28:
            candidates = [c for c in candidates if c.warmth <= 3]
        elif temp > 20:
            candidates = [c for c in candidates if c.warmth <= 4]
        elif temp > 10:
            candidates = [c for c in candidates if c.warmth >= 2]
        else:
            candidates = [c for c in candidates if c.warmth >= 3]

        rain_keywords = ["雨", "rain", "drizzle", "shower"]
        if any(kw in weather.lower() for kw in rain_keywords):
            candidates = [c for c in candidates if c.waterproof or c.category != "鞋子"]

        if preference:
            pref_lower = preference.lower()
            if "正式" in pref_lower or "商务" in pref_lower:
                candidates = [c for c in candidates if c.formality >= 3]
            elif "休闲" in pref_lower:
                candidates = [c for c in candidates if c.formality <= 4]
            elif "运动" in pref_lower:
                candidates = [
                    c for c in candidates
                    if "运动" in c.style or c.formality <= 2
                ]

        return candidates

    @staticmethod
    def _compute_hash(file_path: Path) -> str:
        hasher = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
