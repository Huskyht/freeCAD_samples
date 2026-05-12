import FreeCAD as App
from dataclasses import dataclass, field, asdict
import os
import math
import tomllib


file_path = os.path.join(App.getUserConfigDir(), "waffle.toml")


@dataclass
class toml_consts:
    # This values are  used if the values were not set in toml file.
    sheet_thickness: float = 2.0
    thick_gap: float = 0.10
    min_interval: float = 2.0
    outer_interval: float = 10.0
    cube_z_offset: float = -32.0
    cube_total_height: float = 100.0
    safety_height: float = 5.0
    cube_margin: float = 10.0
    dxf_sheets_gap: float = 10.0

    def config_loader(self):
        print("    config_loader is running ...")
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}. Using defaults.")
            return self

        try:
            with open(file_path, "rb") as f:
                toml_data = tomllib.load(f)
            # load [sheet_informaion] section's values
            sheet_info_dic = toml_data.get("sheet_information", {})
            allowed_keys = self.__class__.__annotations__.keys()
            filtered_data = {
                k: v for k, v in sheet_info_dic.items() if k in allowed_keys
            }

            # Return a new instance with the loaded data
            config_data = toml_consts(**filtered_data)

            print("    Loaded TOML data:", filtered_data)
            return config_data

        except Exception as e:
            print(f"    Failed to load toml file. Using defaults: {e}")
            return self


@dataclass
class sheet_info:
    bounder_length: int
    vec: App.Base.Vector
    sheet_num: int = 0
    thickness: float = 0.0
    thick_gap: float = 0.0
    interval: float = 0.0
    outer_interval: float = 0.0

    def __post_init__(self):
        consts = toml_consts().config_loader()
        self.thickness = consts.sheet_thickness
        self.thick_gap = consts.thick_gap
        self.outer_interval = consts.outer_interval

        offset_length = self.bounder_length - self.outer_interval
        number: float = offset_length / (
            consts.min_interval + self.thickness + self.thick_gap
        )
        self.sheet_num = math.floor(number)
        full_interval = (
            offset_length - (self.thickness + self.thick_gap) * self.sheet_num
        ) / (self.sheet_num - 1)
        self.interval = round(full_interval, 1)
        App.Console.PrintMessage(f"  sheet_info: {self}\n")
