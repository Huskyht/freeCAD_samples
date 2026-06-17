from tomllib import load
import FreeCAD as App
import FreeCADGui as Gui
import sys
import os

current_dir = os.path.dirname(__file__)
if current_dir not in sys.path:
    sys.path.append(current_dir)

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


# ╔══════════════════════════════════════════════════════════╗
# ║                       ENTRY POINT                        ║
# ╚══════════════════════════════════════════════════════════╝
def cut_cube_wrapper():
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
        App.Console.PrintMessage(
            "Please set cutting_mode in waffle.toml before execute command."
        )
        return

    doc.removeObject(box_obj.Name)
    doc.recompute()


class CutCubeCmd:
    """This class defines the toolbar button and menu action for FreeCAD."""

    def GetResources(self):
        return {
            "Pixmap": "1_align_model.png",
            "MenuText": "Cut Cube",
            "ToolTip": "Create Intersectional/Laminational sheets dies",
        }

    def Activated(self):
        """This method runs automatically whenever you click the toolbar button."""
        App.Console.PrintMessage("  align model on xy plane...\n")
        try:
            cut_cube_wrapper()
            App.Console.PrintMessage(" align model on xy plane\n")
        except Exception as e:
            App.Console.PrintError(f"Error executing align_model: {str(e)}\n")

    def IsActive(self):
        """Optional: Determines if the button is clickable.
        Returns True if a document is open, otherwise greys out the button."""
        return App.ActiveDocument is not None


# Register this script into FreeCAD's global command manager.
# The string 'create_cube' MUST exactly match the item you put into self.list inside InitGui.py
Gui.addCommand("cut_cube", CutCubeCmd())
