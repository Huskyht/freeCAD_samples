import FreeCAD
import FreeCADGui as Gui
import Part

import math
from dataclasses import dataclass
import os

# from toml_loader import AppPreference, DieInfo, load_toml, LamiInfo

# from WaffleBaker import config_loader
from config_loader import (
    AppPreference,
    DieInfo,
    LamiInfo,
    get_cached_data,
    load_config,
    set_param,
    save_config,
)
import tools
from PySide6 import QtUiTools


@dataclass
class CubeDim:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    @classmethod
    def define_cube_size_intr(cls, bbox, die_info: DieInfo):
        cube = CubeDim()
        cube.x = math.ceil(bbox.XLength) + die_info.cube_margin
        cube.y = math.ceil(bbox.YLength) + die_info.cube_margin
        cube.z = die_info.cube_total_height

        FreeCAD.Console.PrintMessage("Bounding Box Sizes:\n")
        FreeCAD.Console.PrintMessage(f"  X: {cube.x:.4f}\n")
        FreeCAD.Console.PrintMessage(f"  Y: {cube.y:.4f}\n")
        FreeCAD.Console.PrintMessage(f"  Z: {cube.z:.4f}\n")

        return cube

    @classmethod
    def define_cube_size_lami(cls, bbox, die_info, thickness):
        cube = CubeDim()
        cube.z = die_info.cube_total_height

        if bbox.XLength >= bbox.YLength:
            short_side = bbox.YLength
            long_side = bbox.XLength

        else:
            short_side = bbox.XLength
            long_side = bbox.YLength

        sheet_num = (short_side + die_info.cube_margin) / thickness
        width = math.ceil(sheet_num) * thickness
        length = math.ceil(long_side) + die_info.cube_margin

        if width > length:
            length = width

        if bbox.XLength >= bbox.YLength:
            cube.x = length
            cube.y = width
        else:
            cube.x = width
            cube.y = length

        FreeCAD.Console.PrintMessage("Bounding Box Sizes:\n")
        FreeCAD.Console.PrintMessage(f"  X: {cube.x:.4f}\n")
        FreeCAD.Console.PrintMessage(f"  Y: {cube.y:.4f}\n")
        FreeCAD.Console.PrintMessage(f"  Z: {cube.z:.4f}\n")

        return cube


def get_shape(selection, as_compound=True):
    FreeCAD.Console.PrintMessage(f"  selection: {selection}\n")

    if not selection:
        FreeCAD.Console.PrintMessage(
            "Error: Please select at least one face or object.\n"
        )
        raise ValueError("No valid geometry found.")

    shapes = []
    first_face_normal = None

    for sel in selection:
        if sel.SubObjects:
            for sub in sel.SubObjects:
                shapes.append(sub)
                # ── Capture the normal vector of the first selected Face ──────────────
                if first_face_normal is None and isinstance(sub, Part.Face):
                    # ── Get the normal at the center of ───────────────────────────────────
                    # ── the face's parameter space (u=0.5, v=0.5) ─────────────────────────
                    uv = sub.Surface.parameter(sub.CenterOfMass)
                    first_face_normal = sub.normalAt(uv[0], uv[1])
        else:
            # ── If an entire object is selected ───────────────────────────────────
            if hasattr(sel.Object, "Shape"):
                shapes.append(sel.Object.Shape)

    if not shapes:
        FreeCAD.Console.PrintMessage("Error: No valid geometry found.\n")
        raise ValueError("No valid geometry found.")

    return Part.makeCompound(shapes) if as_compound else shapes


def create_new_cube(z_offset, cube: CubeDim):
    new_box = Part.makeBox(cube.x, cube.y, cube.z)
    placement = FreeCAD.Placement(
        FreeCAD.Vector(-cube.x / 2, -cube.y / 2, z_offset), FreeCAD.Rotation()
    )
    new_box.Placement = placement

    return new_box


class CreateCubeTaskPanel:
    def __init__(self, cache_data):
        ui_path = os.path.join(tools.ui_path, "CreateCubeOptions.ui")
        # ui_path = os.path.join(wb_dir, "/Resources/UnfoldOptions.ui")
        loader = QtUiTools.QUiLoader()
        self.form = loader.load(ui_path)

        self.form.cube_total_height.setValue(float(cache_data["cube_total_height"]))
        self.form.cube_z_offset.setValue(float(cache_data["cube_z_offset"]))
        self.form.safety_height.setValue(float(cache_data["safety_height"]))
        self.form.cube_margin.setValue(float(cache_data["cube_margin"]))

        if cache_data["cutting_mode"] == "intersection":
            self.form.intersection.setChecked(True)
        else:
            self.form.lamination.setChecked(True)

    def accept(self):
        set_param("cube_total_height", self.form.cube_total_height.value())
        set_param("cube_z_offset", self.form.cube_z_offset.value())
        set_param("safety_height", self.form.safety_height.value())
        set_param("cube_margin", self.form.cube_margin.value())

        if self.form.intersection.isChecked():
            set_param("mode", "intersection")
        elif self.form.lamination.isChecked():
            set_param("cutting_mode", "lamination")
        else:
            set_param("cutting_mode", "intersection")

        save_config()
        die_info = DieInfo.from_cache()
        app_preference = AppPreference.from_cache()
        selection_ex = Gui.Selection.getSelectionEx()
        shape = get_shape(selection_ex, True)

        bbox = shape.BoundBox

        if app_preference.cutting_mode == "lamination":
            # sheet_thickness = LamiInfo.from_toml(toml_data).sheet_thickness
            sheet_thickness = LamiInfo.from_cache().sheet_thickness
            cube_dim = CubeDim.define_cube_size_lami(bbox, die_info, sheet_thickness)
        else:
            cube_dim = CubeDim.define_cube_size_intr(bbox, die_info)

        box = create_new_cube(die_info.cube_z_offset, cube_dim)
        Part.show(box)
        FreeCAD.ActiveDocument.recompute()
        FreeCAD.Console.PrintMessage(" Creating bounding box \n")

        return True


class CreateCubeCmd:
    """This class defines the toolbar button and menu action for FreeCAD."""

    def GetResources(self):
        return {
            "Pixmap": "create_cube.png",
            "MenuText": "Create Cube",
            "ToolTip": "Create Intersectional/Laminational blank bounding box cube.",
        }

    # ╔══════════════════════════════════════════════════════════╗
    # ║                       ENTRY POINT                        ║
    # ╚══════════════════════════════════════════════════════════╝
    def Activated(self):
        """This method runs automatically whenever you click the toolbar button."""
        FreeCAD.Console.PrintMessage("  Creating bounding box ...\n")
        try:
            # toml_data = load_toml()
            # die_info = DieInfo.from_toml(toml_data)
            # app_preference = AppPreference.(toml_data)
            cache_data = get_cached_data()
            panel = CreateCubeTaskPanel(cache_data)
            Gui.Control.showDialog(panel)

            # die_info = DieInfo.from_cache()
            # app_preference = AppPreference.from_cache()
            # selection_ex = Gui.Selection.getSelectionEx()
            # shape = get_shape(selection_ex, True)

            # bbox = shape.BoundBox

            # if app_preference.cutting_mode == "lamination":
            #     # sheet_thickness = LamiInfo.from_toml(toml_data).sheet_thickness
            #     sheet_thickness = LamiInfo.from_cache().sheet_thickness
            #     cube_dim = CubeDim.define_cube_size_lami(
            #         bbox, die_info, sheet_thickness
            #     )
            # else:
            #     cube_dim = CubeDim.define_cube_size_intr(bbox, die_info)

            # box = create_new_cube(die_info.cube_z_offset, cube_dim)
            # Part.show(box)
            # FreeCAD.ActiveDocument.recompute()
            # FreeCAD.Console.PrintMessage(" Creating bounding box \n")

        except Exception as e:
            FreeCAD.Console.PrintError(f"Error executing Create Cube: {str(e)}\n")

    def IsActive(self):
        """Optional: Determines if the button is clickable.
        Returns True if a document is open, otherwise greys out the button."""
        return FreeCAD.ActiveDocument is not None


# Register this script into FreeCAD's global command manager.
# The string 'create_cube' MUST exactly match the item you put into self.list inside InitGui.py
Gui.addCommand("create_cube", CreateCubeCmd())
