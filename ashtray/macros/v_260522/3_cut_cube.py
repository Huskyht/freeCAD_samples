from tomllib import load
import FreeCAD as App
import FreeCADGui as Gui
import Part

# Macro importing const in another file
import sys
import os

# Get current macro directory
current_dir = os.path.dirname(__file__)
# Add it to Python path
if current_dir not in sys.path:
    sys.path.append(current_dir)

# from const import consts, SheetInfo
# from toml_loader import load_toml, TomlConsts, SheetInfo, DxfSettings, AppPreference
from toml_loader import (
    load_toml,
    DieInfo,
    IntrSecInfo,
    LamiInfo,
    LamiSheetsInfo,
    DxfSettings,
    AppPreference,
)
from lamination import lamination
from intersection import intersection


# ===================
# === ENTRY POINT ===
# ===================
def main():
    toml_data = load_toml()
    die_info = DieInfo.from_toml(toml_data)
    dxf_settings = DxfSettings.from_toml(toml_data)
    app_preference = AppPreference.from_toml(toml_data)

    doc = App.ActiveDocument
    sel = Gui.Selection.getSelectionEx()

    step_obj = sel[0].Object
    box_obj = sel[1].Object
    box = box_obj.Shape

    step_obj.ViewObject.Visibility = False

    if app_preference.cutting_mode == "lamination":
        lami_info = LamiInfo.from_toml(toml_data)
        lamination(lami_info, dxf_settings, step_obj, box)
    elif app_preference.cutting_mode == "intersection":
        intr_sec_info = IntrSecInfo.from_toml(toml_data)
        intersection(die_info, intr_sec_info, dxf_settings, step_obj, box)
    else:
        App.Console.PrintMessage("set cutting_mode in waffle.toml.")
        return

    doc.removeObject(box_obj.Name)
    doc.recompute()


if __name__ == "__main__":
    main()
