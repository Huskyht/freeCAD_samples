import os
import sys
from dataclasses import dataclass

def ensure_toml():
    try:
        return importlib.import_module('toml')
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "toml", "--user"])
        return importlib.import_module('toml')

toml = ensure_toml()


FILE_PATH = ".config/FreeCAD/waffle.toml"


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
        # toml_data = toml.load(FILE_PATH)

        if not os.path.exists(FILE_PATH):
            print("file is not exist ...")
            return self
        try:
            toml_data = toml.load(FILE_PATH)
            sheet_info_dic = toml_data.get(('sheet_information',{})
            config_data = toml_consts(**{
            k: v for k, v in sheet_info_dic.items() 
            if k in toml_data.__annotations__
        })
            
            print(toml_data)
            App.Console.PrintMessage(toml_data)
        except Exception as e:
            print(f"failed to load toml file. continue with default constants.: {e}")
            return self

    def config_updater(self):
        toml_data = toml.load(FILE_PATH)

        print(toml_data)
        App.Console.PrintMessage(toml_data)
