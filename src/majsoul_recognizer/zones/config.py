"""区域配置加载

从 YAML 文件加载区域坐标定义。坐标为 0.0-1.0 的比例值。
"""

from pathlib import Path

import yaml
from pydantic import BaseModel

from majsoul_recognizer.types import ZoneDefinition, ZoneName


class ZoneConfig(BaseModel):
    """区域配置集合"""
    zones: dict[ZoneName, ZoneDefinition]

    def get_zone(self, name: ZoneName) -> ZoneDefinition | None:
        return self.zones.get(name)

    @property
    def zone_names(self) -> list[ZoneName]:
        return list(self.zones.keys())


def load_zone_config(path: Path | str) -> ZoneConfig:
    """从 YAML 文件加载区域配置"""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Zone config not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    zones = {}
    for name_str, coords in raw.get("zones", {}).items():
        zone_name = ZoneName(name_str)
        zones[zone_name] = ZoneDefinition(
            name=zone_name,
            x=coords["x"],
            y=coords["y"],
            width=coords["width"],
            height=coords["height"],
        )

    return ZoneConfig(zones=zones)
