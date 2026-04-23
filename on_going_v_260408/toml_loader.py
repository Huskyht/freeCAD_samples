import FreeCAD as App
from dataclasses import dataclass, field, asdict
import importlib
import platform
import subprocess
import sys
import os
import math


file_path = os.path.join(App.getUserConfigDir(), "waffle.toml")


# below codes DOES NOT work for Arch linux. If you want to use this module install via "yay -Syu python-toml" first.
def ensure_toml():
    try:
        return importlib.import_module("toml")
    except ImportError:
        if platform.system() == "Windows":
            print("Windows detected. Attempting to install toml...")
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "toml", "--user"]
            )
            importlib.invalidate_caches()
            return importlib.import_module("toml")
        else:
            raise ImportError(
                "toml library is missing. Please install it via your package manager."
            )

    except Exception as e:
        print(f"Auto-install failed: {e}")
        return None


@dataclass
class toml_consts:
    sheet_thickness: float = 2.1
    min_interval: float = 2.0
    outer_interval: float = 10.0
    cube_z_offset: float = -32.0
    cube_total_height: float = 100.0
    safety_height: float = 5.0
    cube_margin: float = 10.0
    dxf_sheets_gap: float = 10.0

    def config_loader(self):
        toml = ensure_toml()
        print("config_loader is running ...")
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}. Using defaults.")
            return self

        try:
            toml_data = toml.load(file_path)
            sheet_info_dic = toml_data.get("sheet_information", {})

            allowed_keys = self.__class__.__annotations__.keys()

            filtered_data = {
                k: v for k, v in sheet_info_dic.items() if k in allowed_keys
            }

            # Return a new instance with the loaded data
            config_data = toml_consts(**filtered_data)

            print("Loaded TOML data:", filtered_data)
            return config_data

        except Exception as e:
            print(f"Failed to load toml file. Using defaults: {e}")
            return self

    def config_updater(self):
        toml = ensure_toml()
        with open(file_path, mode="w") as f:
            # Wrap in the section name [sheet_information]
            data_to_save = {"sheet_information": asdict(self)}
            toml.dump(data_to_save, f)

        print("Updated TOML file with:", self)


@dataclass
class sheet_info:
    bounder_length: int
    vec: App.Base.Vector
    sheet_num: int = 0
    thickness: float = toml_consts.sheet_thickness
    interval: float = 0
    outer_interval: float = toml_consts.outer_interval

    def __post_init__(self):
        offset_length = self.bounder_length - self.outer_interval
        number: float = (offset_length + toml_consts.min_interval) / (
            toml_consts.min_interval + self.thickness
        )
        self.sheet_num = math.floor(number)
        full_interval = (offset_length - self.thickness * self.sheet_num) / (
            self.sheet_num - 1
        )
        self.interval = round(full_interval, 1)
        App.Console.PrintMessage(f"  sheet_info: {self}\n")
