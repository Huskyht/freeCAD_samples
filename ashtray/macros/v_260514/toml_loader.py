import FreeCAD as App
from dataclasses import dataclass, field, asdict
from pathlib import Path
import os
import math
import tomllib


def load_toml() -> dict:
    file_path = Path(App.getUserConfigDir() + "waffle.toml")

    if not file_path.exists():
        App.Console.PrintMessage(f"File not found: {file_path}. Using defaults. \n")
        return {}
    try:
        with file_path.open("rb") as f:
            data = tomllib.load(f)
        App.Console.PrintMessage(f"Loaded TOML data: {data} \n")
        return data
    except Exception as e:
        App.Console.PrintMessage(f"Failed to load TOML file: {e}. Using defaults. \n")
        return {}


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


@dataclass
class LamiInfo:
    # This values are  used if the values were not set in toml file.
    sheet_thickness: float = 2.0
    # thick_gap: float = 0.10
    # min_interval: float = 2.0
    outer_gap: float = 10.0
    cube_z_offset: float = -32.0
    # cube_total_height: float = 100.0
    # safety_height: float = 5.0
    # cube_margin: float = 10.0

    @classmethod
    def from_toml(cls, toml_data: dict) -> "LamiInfo":
        section = extract_section(toml_data, "lamination")
        filtered = filter_dict_by_fields(section, set(cls.__annotations__.keys()))
        return cls(**filtered)


@dataclass
class DxfSettings:
    output: bool = False
    sheets_gap: float = 10.0

    @classmethod
    def from_toml(cls, toml_data: dict) -> "DxfSettings":
        section = extract_section(toml_data, "dxf_settings")
        filtered = filter_dict_by_fields(section, set(cls.__annotations__.keys()))
        return cls(**filtered)


@dataclass
class AppPreference:
    cutting_mode: str = "intersection"

    @classmethod
    def from_toml(cls, toml_data: dict) -> "AppPreference":
        section = extract_section(toml_data, "app_preference")
        filtered = filter_dict_by_fields(section, set(cls.__annotations__.keys()))
        return cls(**filtered)


@dataclass
class IntrSheetsInfo:
    bounder_length: float
    vec: App.Base.Vector
    sheet_num: int = 0
    thickness: float = 0.0
    thick_gap: float = 0.0
    interval: float = 0.0
    outer_gap: float = 0.0

    @classmethod
    def from_intr_sec_info(
        cls,
        bounder_length: float,
        vec: App.Base.Vector,
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

        App.Console.PrintMessage(f"IntrSheetsInfo: {info} \n")
        return info


@dataclass
class LamiSheetsInfo:
    bounder_length: float
    vec: App.Base.Vector
    sheet_num: int = 0
    thickness: float = 0.0
    outer_gap: float = 0.0

    @classmethod
    def from_lami_info(
        cls,
        bounder_length: float,
        vec: App.Base.Vector,
        lami_info: LamiInfo,
    ):
        info = LamiSheetsInfo(bounder_length, vec)
        info.thickness = lami_info.sheet_thickness
        info.outer_gap = lami_info.outer_gap

        denom = info.thickness
        if denom <= 0:
            raise ValueError("Invalied denominator in sheet calculation.")

        offset_width = info.bounder_length
        number: float = offset_width / denom
        info.sheet_num = math.floor(number)

        App.Console.PrintMessage(f"LamiSheetsInfo: {info} \n")
        return info
