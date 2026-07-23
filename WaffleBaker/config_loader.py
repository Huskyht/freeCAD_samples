from io import text_encoding
import FreeCAD
from dataclasses import dataclass
from pathlib import Path
import os
import math
import tools
import json

file_path = Path(tools.config_dir + "waffle.json")

_cache = {
    "cube_total_height": "75.0",
    "cube_z_offset": "-28.8",  # this value represents lower die height( LDH ). recommend to set value same as -( die holder plates number ) * n .
    "safety_height": "5.0",  # THIS VALUE DECIDE UPPER DIE INTER SECTION Z HEIGHT. IT SHOULD LARGER THAN TARGET SHEET METAL'S THICKNESS.
    "cube_margin": "10.0",  # how large from deep drawing edge
    "sheet_thickness": "1.0",  # Leave a small gap in the sheetse thickness used.
    "thick_gap": "0.08",  # Leave a small gap in the sheetse thickness used.
    "min_interval": "1.5",  # recommend to set value same as sheets thickness or more.
    "outer_gap": "10.0",  # this value represents the distance from the edge.
    "output": "false",
    "sheets_gap": "10.0",  # default: 10.0 , this value should set larger than distance of LASER start point
    "font_path": "/usr/share/fonts/TTF/SauceCodeProNerdFont-Regular.ttf",
    "text_height": "4.0",
    "cutting_mode": "intersection",  # intersection: x/y cut, lamination: x or y cut
}


def set_param(key, value):
    _cache[key] = value


def get_cached_data():
    return _cache


def load_config():
    global _cache

    if not file_path.exists():
        FreeCAD.Console.PrintMessage(f"File not found: {file_path}.\n")
        FreeCAD.Console.PrintMessage(
            f"Trying to create new config file ...: {file_path}.\n"
        )
        save_config()
    try:
        with file_path.open("rb") as f:
            _cache.update(json.load(f))
        FreeCAD.Console.PrintMessage(f"Loaded previous data: {_cache} \n")
    except Exception as e:
        FreeCAD.Console.PrintMessage(
            f"Failed to load config file: {e}. Using defaults. \n"
        )


def save_config():
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(_cache, f, indent=4)
    except Exception as e:
        print(f"failed to save currently settings in config file.: {e}")


def extract_section(toml_data: dict, section_name: str) -> dict:
    return toml_data.get(section_name, {}) or {}


def filter_dict_by_fields(data: dict, fields: set[str]) -> dict:
    return {k: v for k, v in data.items() if k in fields}


# ===============
# === STRUCTS ===
# ===============
@dataclass
class DieInfo:
    # This values are  used if the values were not set in toml file.
    cube_z_offset: float = -32.0
    cube_total_height: float = 100.0
    safety_height: float = 5.0
    cube_margin: float = 10.0

    @classmethod
    def from_toml(cls, toml_data: dict) -> "DieInfo":
        section = extract_section(toml_data, "die_information")
        filtered = filter_dict_by_fields(section, set(cls.__annotations__.keys()))
        return cls(**filtered)

    @classmethod
    def from_cache(
        cls,
    ) -> "DieInfo":
        return cls(
            cube_z_offset=float(_cache.get("cube_z_offset", cls.cube_z_offset)),
            cube_total_height=float(
                _cache.get("cube_total_height", cls.cube_total_height)
            ),
            safety_height=float(_cache.get("safety_height", cls.safety_height)),
            cube_margin=float(_cache.get("cube_margin", cls.cube_margin)),
        )


@dataclass
class IntrSecInfo:
    # This values are  used if the values were not set in toml file.
    sheet_thickness: float = 2.0
    thick_gap: float = 0.10
    min_interval: float = 2.0
    outer_gap: float = 10.0
    cube_z_offset: float = -32.0
    # cube_total_height: float = 100.0
    # safety_height: float = 5.0
    # cube_margin: float = 10.0

    @classmethod
    def from_toml(cls, toml_data: dict) -> "IntrSecInfo":
        section = extract_section(toml_data, "intersection")
        filtered = filter_dict_by_fields(section, set(cls.__annotations__.keys()))
        return cls(**filtered)

    @classmethod
    def from_cache(
        cls,
    ) -> "IntrSecInfo":
        return cls(
            sheet_thickness=float(_cache.get("sheet_thickness", cls.sheet_thickness)),
            thick_gap=float(_cache.get("thick_gap", cls.thick_gap)),
            min_interval=float(_cache.get("min_interval", cls.min_interval)),
            outer_gap=float(_cache.get("outer_gap", cls.outer_gap)),
            cube_z_offset=float(_cache.get("cube_z_offset", cls.cube_z_offset)),
        )


@dataclass
class LamiInfo:
    # This values are  used if the values were not set in toml file.
    sheet_thickness: float = 2.0
    # thick_gap: float = 0.10
    # min_interval: float = 2.0
    outer_gap: float = 0.04
    # cube_z_offset: float = -32.0
    # cube_total_height: float = 100.0
    # safety_height: float = 5.0
    # cube_margin: float = 10.0

    @classmethod
    def from_toml(cls, toml_data: dict) -> "LamiInfo":
        section = extract_section(toml_data, "lamination")
        filtered = filter_dict_by_fields(section, set(cls.__annotations__.keys()))
        return cls(**filtered)

    @classmethod
    def from_cache(
        cls,
    ) -> "LamiInfo":
        return cls(
            sheet_thickness=float(_cache.get("sheet_thickness", cls.sheet_thickness)),
            outer_gap=float(_cache.get("outer_gap", cls.outer_gap)),
        )


@dataclass
class DxfSettings:
    output: bool = False
    sheets_gap: float = 10.0
    font_path: str = os.path.join(
        tools.wb_dir, "fonts/SauceCodeProNerdFont-Regular.ttf"
    )
    text_height: float = 4.0

    @classmethod
    def from_toml(cls, toml_data: dict) -> "DxfSettings":
        section = extract_section(toml_data, "dxf_settings")
        filtered = filter_dict_by_fields(section, set(cls.__annotations__.keys()))
        FreeCAD.Console.PrintMessage(f"DxfSettings: {cls} \n")
        return cls(**filtered)

    @classmethod
    def from_cache(
        cls,
    ) -> "DxfSettings":
        return cls(
            output=bool(_cache.get("output", cls.output)),
            sheets_gap=float(_cache.get("sheets_gap", cls.sheets_gap)),
            font_path=_cache.get("font_path", cls.font_path),
            text_height=float(_cache.get("text_height", cls.text_height)),
        )


@dataclass
class AppPreference:
    cutting_mode: str = "intersection"

    @classmethod
    def from_toml(cls, toml_data: dict) -> "AppPreference":
        section = extract_section(toml_data, "app_preference")
        filtered = filter_dict_by_fields(section, set(cls.__annotations__.keys()))
        return cls(**filtered)

    @classmethod
    def from_cache(
        cls,
    ) -> "AppPreference":
        return cls(
            cutting_mode=_cache.get("cutting_mode", cls.cutting_mode),
        )


@dataclass
class IntrSheetsInfo:
    bounder_length: float
    vec: FreeCAD.Base.Vector
    sheet_num: int = 0
    thickness: float = 0.0
    thick_gap: float = 0.0
    interval: float = 0.0
    outer_gap: float = 0.0

    @classmethod
    def from_intr_sec_info(
        cls,
        bounder_length: float,
        vec: FreeCAD.Base.Vector,
        intr_sec_info: IntrSecInfo,
    ):
        info = IntrSheetsInfo(bounder_length, vec)
        info.thickness = intr_sec_info.sheet_thickness
        info.thick_gap = intr_sec_info.thick_gap
        info.outer_gap = intr_sec_info.outer_gap

        denom = intr_sec_info.min_interval + info.thickness + info.thick_gap

        if denom <= 0:
            raise ValueError("Invalied denominator in sheet calculation.")

        offset_width = info.bounder_length - info.outer_gap
        number: float = (offset_width + intr_sec_info.min_interval) / (denom)
        info.sheet_num = math.floor(number)
        full_interval = (
            offset_width - (info.thickness + info.thick_gap) * info.sheet_num
        ) / (info.sheet_num - 1)
        info.interval = round(full_interval, 1)

        FreeCAD.Console.PrintMessage(f"IntrSheetsInfo: {info} \n")
        return info


@dataclass
class LamiSheetsInfo:
    bounder_length: float
    vec: FreeCAD.Base.Vector
    sheet_num: int = 0
    thickness: float = 0.0
    outer_gap: float = 0.0

    @classmethod
    def from_lami_info(
        cls,
        bounder_length: float,
        vec: FreeCAD.Base.Vector,
        lami_info: LamiInfo,
    ):
        info = LamiSheetsInfo(bounder_length, vec)
        info.thickness = lami_info.sheet_thickness
        info.outer_gap = lami_info.outer_gap

        denom = info.thickness
        if denom <= 0:
            raise ValueError("Invalied denominator in sheet calculation.")

        offset_width = info.bounder_length - info.outer_gap
        number: float = offset_width / denom
        info.sheet_num = math.floor(number)

        FreeCAD.Console.PrintMessage(f"LamiSheetsInfo: {info} \n")
        return info
