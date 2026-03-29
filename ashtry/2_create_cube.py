import FreeCAD as App
import FreeCADGui as Gui
import Part
from FreeCAD import Base

# use for rounding up bbox
import math
from dataclasses import dataclass


class Const:
    SHEET_THICKNESS = 2.0
    MIN_INTERVAL = 2.0
    OUTER_INTERVAL = 10.0  # this value represents the distance from the edge.


@dataclass
class sheet_info:
    bounder_length: int
    vec: Base.Vector

    sheet_num: int = 0
    thickness: float = Const.SHEET_THICKNESS
    interval: float = 0
    outer_interval: float = Const.OUTER_INTERVAL

    def __post_init__(self):
        offset_length = self.bounder_length - self.outer_interval
        number: float = (offset_length + Const.MIN_INTERVAL) / (
            Const.MIN_INTERVAL + self.thickness
        )
        self.sheet_num = math.floor(number)
        full_interval = (offset_length - self.thickness * self.sheet_num) / (
            self.sheet_num - 1
        )
        self.interval = round(full_interval, 1)
        App.Console.PrintMessage(f"  sheet_info: {self}\n")


def create_cube(selection):

    if not selection:
        App.Console.PrintMessage("Error: Please select at least one face or object.\n")
        return

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
        return

    # Create a compound to calculate the global Bounding Box
    combined_shape = Part.makeCompound(shapes)
    bbox = combined_shape.BoundBox

    x_dim = math.ceil(bbox.XLength) + 10
    y_dim = math.ceil(bbox.YLength) + 10
    z_dim = 100

    new_box = App.ActiveDocument.addObject("Part::Box", "new_box")

    fixed_pos = App.Vector(-x_dim / 2, -y_dim / 2, -32)
    fixed_rot = App.Rotation()
    fixed_placement = App.Placement(fixed_pos, fixed_rot)

    new_box.Length = x_dim
    new_box.Width = y_dim
    new_box.Height = z_dim
    new_box.Placement = fixed_placement

    App.ActiveDocument.recompute()

    # Output results to the Report View (Console)
    App.Console.PrintMessage("\n--- Geometry Analysis Results ---\n")

    # 1. Bounding Box Dimensions
    App.Console.PrintMessage(f"Bounding Box Sizes:\n")
    App.Console.PrintMessage(f"  X: {bbox.XLength:.4f}\n")
    App.Console.PrintMessage(f"  Y: {bbox.YLength:.4f}\n")
    App.Console.PrintMessage(f"  Z: {bbox.ZLength:.4f}\n")
    App.Console.PrintMessage(f"die box Sizes:\n")
    App.Console.PrintMessage(f"  X: {x_dim:.4f}\n")
    App.Console.PrintMessage(f"  Y: {y_dim:.4f}\n")
    App.Console.PrintMessage(f"  Z: {z_dim:.4f}\n")

    # 2. Normal Vector of the first selected face
    if first_face_normal:
        App.Console.PrintMessage(f"Normal Vector (First Face):\n")
        App.Console.PrintMessage(
            f"  (x, y, z): ({first_face_normal.x:.4f}, {first_face_normal.y:.4f}, {first_face_normal.z:.4f})\n"
        )
    else:
        App.Console.PrintMessage(
            "Normal Vector: No face was selected (only objects/edges).\n"
        )

    App.Console.PrintMessage("---------------------------------\n")

    return new_box


# =================
# === UTILITIES ===
# =================


# return True if even or False if odd
def is_even_odd(checking_number):
    if checking_number % 2 == 0:
        return True
    else:
        return False


def append_wires(shape, vec, offset):
    wires = []
    for i in shape.slice(vec, offset):
        wires.append(i)

    return wires


def create_cutting_planes(shape, sheets: sheet_info):
    sheet_center_interval = sheets.interval + sheets.thickness
    i = 1
    wires = []
    offset = 0.0
    if is_even_odd(sheets.sheet_num):  # is even number
        while i <= sheets.sheet_num / 2:
            App.Console.PrintMessage(f"i :{i}\n")
            App.Console.PrintMessage(f"offset val :{offset}\n")
            if i == 1:
                offset += sheet_center_interval / 2
                wires.extend(append_wires(shape, sheets.vec, offset))
                wires.extend(append_wires(shape, sheets.vec, -offset))
            else:
                offset += sheet_center_interval
                wires.extend(append_wires(shape, sheets.vec, offset))
                wires.extend(append_wires(shape, sheets.vec, -offset))
            i += 1
    else:  # is odd number
        wires.extend(append_wires(shape, sheets.vec, 0))
        while i <= sheets.sheet_num // 2:
            App.Console.PrintMessage(f"i :{i}\n")
            App.Console.PrintMessage(f"offset val :{offset}\n")
            offset += sheet_center_interval
            wires.extend(append_wires(shape, sheets.vec, offset))
            wires.extend(append_wires(shape, sheets.vec, -offset))
            i += 1

    App.Console.PrintMessage(f"wires :{wires}\n")
    comp = Part.makeCompound(wires)
    slice = App.ActiveDocument.addObject("Part::Feature", "Cut_cs")
    slice.Shape = comp
    slice.purgeTouched()
    # del slice, comp, wires


# Execute the function

# create bound box
selection_ex = Gui.Selection.getSelectionEx()
box = create_cube(selection_ex)
# execute boolean cut
x_sheets = sheet_info(bounder_length=box.Length.Value, vec=Base.Vector(1, 0, 0))
y_sheets = sheet_info(bounder_length=box.Width.Value, vec=Base.Vector(0, 1, 0))
# create_cutting_planes(box.Shape, x_sheets)
# create_cutting_planes(box.Shape, y_sheets)

# sheet_num: int
# thickness: int
# interval: int
# outer_interval: int
