import FreeCAD
import FreeCADGui as Gui


# from toml_loader import (
#     load_toml,
#     DieInfo,
#     IntrSecInfo,
#     LamiInfo,
#     LamiSheetsInfo,
#     DxfSettings,
#     AppPreference,
# )
from config_loader import (
    DieInfo,
    IntrSecInfo,
    LamiInfo,
    LamiSheetsInfo,
    DxfSettings,
    AppPreference,
    get_cached_data,
    load_config,
    set_param,
    save_config,
)

import os
import tools
from PySide6 import QtUiTools

from lamination import lamination
from intersection import intersection


class CutCubeTaskPanel:
    def __init__(self, cache_data):
        ui_path = os.path.join(tools.ui_path, "CutCubeOptions.ui")
        # ui_path = os.path.join(wb_dir, "/Resources/UnfoldOptions.ui")
        loader = QtUiTools.QUiLoader()
        self.form = loader.load(ui_path)

        self.form.sheet_thickness.setValue(float(cache_data["sheet_thickness"]))
        self.form.thick_gap.setValue(float(cache_data["thick_gap"]))
        self.form.min_interval.setValue(float(cache_data["min_interval"]))
        self.form.outer_gap.setValue(float(cache_data["outer_gap"]))
        self.form.sheets_gap.setValue(float(cache_data["sheets_gap"]))
        self.form.text_height.setValue(float(cache_data["text_height"]))

        if cache_data["cutting_mode"] == "intersection":
            self.form.intersection.setChecked(True)
        else:
            self.form.lamination.setChecked(True)

    def accept(self):
        FreeCAD.Console.PrintMessage("  cutting cube...\n")
        cut_cube_wrapper()
        FreeCAD.Console.PrintMessage(" cutting cube\n")

        set_param("sheet_thickness", self.form.sheet_thickness.value())
        set_param("thick_gap", self.form.thick_gap.value())
        set_param("min_interval", self.form.min_interval.value())
        set_param("outer_gap", self.form.outer_gap.value())

        if self.form.intersection.isChecked():
            set_param("cutting_mode", "intersection")
        elif self.form.lamination.isChecked():
            set_param("cutting_mode", "lamination")
        else:
            set_param("cutting_mode", "intersection")

        save_config()

        return True


# ╔══════════════════════════════════════════════════════════╗
# ║                       ENTRY POINT                        ║
# ╚══════════════════════════════════════════════════════════╝
def cut_cube_wrapper():
    # toml_data = load_toml()
    # die_info = DieInfo.from_toml(toml_data)
    # dxf_settings = DxfSettings.from_toml(toml_data)
    # app_preference = AppPreference.from_toml(toml_data)

    die_info = DieInfo.from_cache()
    dxf_settings = DxfSettings.from_cache()
    app_preference = AppPreference.from_cache()

    doc = FreeCAD.ActiveDocument
    sel = Gui.Selection.getSelectionEx()

    step_obj = sel[0].Object
    box_obj = sel[1].Object
    box = box_obj.Shape

    step_obj.ViewObject.Visibility = False

    if app_preference.cutting_mode == "lamination":
        # lami_info = LamiInfo.from_toml(toml_data)
        lami_info = LamiInfo.from_cache()
        lamination(lami_info, dxf_settings, step_obj, box)
    elif app_preference.cutting_mode == "intersection":
        # intr_sec_info = IntrSecInfo.from_toml(toml_data)
        intr_sec_info = IntrSecInfo.from_cache()
        intersection(die_info, intr_sec_info, dxf_settings, step_obj, box)
    else:
        FreeCAD.Console.PrintMessage(
            "Please set cutting_mode in waffle.toml before execute command."
        )
        return

    doc.removeObject(box_obj.Name)
    doc.recompute()


class CutCubeCmd:
    """This class defines the toolbar button and menu action for FreeCAD."""

    def GetResources(self):
        return {
            "Pixmap": "cut_cube.png",
            "MenuText": "Cut Cube",
            "ToolTip": "Create Intersectional/Laminational sheets dies",
        }

    def Activated(self):
        """This method runs automatically whenever you click the toolbar button."""
        cache_data = get_cached_data()
        panel = CutCubeTaskPanel(cache_data)
        Gui.Control.showDialog(panel)

        # try:
        #     cut_cube_wrapper()
        #     FreeCAD.Console.PrintMessage(" cutting cube\n")
        # except Exception as e:
        #     FreeCAD.Console.PrintError(f"Error executing cut_cube: {str(e)}\n")

    def IsActive(self):
        """Optional: Determines if the button is clickable.
        Returns True if a document is open, otherwise greys out the button."""
        return FreeCAD.ActiveDocument is not None


# Register this script into FreeCAD's global command manager.
# The string 'create_cube' MUST exactly match the item you put into self.list inside InitGui.py
Gui.addCommand("cut_cube", CutCubeCmd())
