import FreeCAD as App
import FreeCADGui as Gui
import Part

import math
from dataclasses import dataclass

# Macro importing const in another file
import sys
import os

# Get current macro directory
current_dir = os.path.dirname(__file__)
# Add it to Python path
if current_dir not in sys.path:
    sys.path.append(current_dir)

# from const import Const
from toml_loader import AppPreference, DieInfo, load_toml, LamiInfo


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

        App.Console.PrintMessage("Bounding Box Sizes:\n")
        App.Console.PrintMessage(f"  X: {cube.x:.4f}\n")
        App.Console.PrintMessage(f"  Y: {cube.y:.4f}\n")
        App.Console.PrintMessage(f"  Z: {cube.z:.4f}\n")

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

        App.Console.PrintMessage("Bounding Box Sizes:\n")
        App.Console.PrintMessage(f"  X: {cube.x:.4f}\n")
        App.Console.PrintMessage(f"  Y: {cube.y:.4f}\n")
        App.Console.PrintMessage(f"  Z: {cube.z:.4f}\n")

        return cube


def get_shape(selection, as_compound=True):
    App.Console.PrintMessage(f"  selection: {selection}\n")

    if not selection:
        App.Console.PrintMessage("Error: Please select at least one face or object.\n")
        raise ValueError("No valid geometry found.")

    shapes = []
    first_face_normal = None

    for sel in selection:
        if sel.SubObjects:
            for sub in sel.SubObjects:
                shapes.append(sub)
                # Capture the normal vector of the first selected Face
                if first_face_normal is None and isinstance(sub, Part.Face):
                    # Get the normal at the center of the face's parameter space (u=0.5, v=0.5)
                    uv = sub.Surface.parameter(sub.CenterOfMass)
                    first_face_normal = sub.normalAt(uv[0], uv[1])
        else:
            # If an entire object is selected
            if hasattr(sel.Object, "Shape"):
                shapes.append(sel.Object.Shape)

    if not shapes:
        App.Console.PrintMessage("Error: No valid geometry found.\n")
        raise ValueError("No valid geometry found.")

    return Part.makeCompound(shapes) if as_compound else shapes


def create_cube(z_offset, cube: CubeDim):
    new_box = Part.makeBox(cube.x, cube.y, cube.z)
    placement = App.Placement(
        App.Vector(-cube.x / 2, -cube.y / 2, z_offset), App.Rotation()
    )
    new_box.Placement = placement

    return new_box


# ===================
# === ENTRY POINT ===
# ===================
def main():
    App.Console.PrintMessage("Creating bounding box ...\n")
    toml_data = load_toml()
    die_info = DieInfo.from_toml(toml_data)
    app_preference = AppPreference.from_toml(toml_data)

    selection_ex = Gui.Selection.getSelectionEx()
    shape = get_shape(selection_ex, True)
    bbox = shape.BoundBox

    if app_preference.cutting_mode == "lamination":
        sheet_thickness = LamiInfo.from_toml(toml_data).sheet_thickness

        cube_dim = CubeDim.define_cube_size_lami(bbox, die_info, sheet_thickness)
    else:
        cube_dim = CubeDim.define_cube_size_intr(bbox, die_info)

    box = create_cube(die_info.cube_z_offset, cube_dim)
    Part.show(box)
    App.ActiveDocument.recompute()
    App.Console.PrintMessage(" Creating bounding box ...\n")


if __name__ == "__main__":
    main()
