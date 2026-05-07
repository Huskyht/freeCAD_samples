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
    CUBE_Z_OFFSET = -32.0
    CUBE_TOTAL_HEIGHT = 100.0
    SAFETY_HEIGHT = 5.0  # NOTE: THIS VALUE DECIDE UPPER DIE INTER SECTION Z HEIGHT. IT SHOULD LARGER THAN TARGET SHEET METAL'S THICKNESS IN STEP FILE.
    CUBE_MARGIN = 10.0
    DXF_SHEETS_GAP = 10.0


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

    x_dim = math.ceil(bbox.XLength) + Const.CUBE_MARGIN
    y_dim = math.ceil(bbox.YLength) + Const.CUBE_MARGIN
    z_dim = Const.CUBE_TOTAL_HEIGHT

    new_box = Part.makeBox(x_dim, y_dim, z_dim)
    placement = App.Placement(
        App.Vector(-x_dim / 2, -y_dim / 2, Const.CUBE_Z_OFFSET), App.Rotation()
    )
    new_box.Placement = placement

    # new_box = App.ActiveDocument.addObject("Part::Box", "new_box")
    # fixed_pos = App.Vector(-x_dim / 2, -y_dim / 2, Const.CUBE_Z_OFFSET)
    # fixed_rot = App.Rotation()
    # fixed_placement = App.Placement(fixed_pos, fixed_rot)

    # new_box.Length = x_dim
    # new_box.Width = y_dim
    # new_box.Height = z_dim
    # new_box.Placement = fixed_placement
    # App.ActiveDocument.recompute()

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


def create_faces(shape, sheets: sheet_info, as_coumpound: bool):
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

    # turn wires into faces
    faces = []
    for w in wires:
        if w.isClosed():
            f = Part.Face(w)
            faces.append(f)

    App.Console.PrintMessage(f"faces :{faces}\n")
    if as_coumpound:
        return Part.makeCompound(faces)
    return faces


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


# NOTE: To extrude symmetric, Sepalate treatement as pos or neg direction and treat each side of faces.
def faces_into_solids(faces, sheets: sheet_info, as_compound: bool):
    direction = sheets.vec.normalize()
    half_thickness = sheets.thickness / 2

    vec_pos = direction * half_thickness
    vec_neg = direction * (-half_thickness)

    solids = []

    for f in faces:
        solid_pos = f.extrude(vec_pos)
        solid_neg = f.extrude(vec_neg)

        solid = solid_pos.fuse(solid_neg)
        solids.append(solid)

    App.Console.PrintMessage(f"solids :{solids}\n")

    if as_compound:
        return Part.makeCompound(solids)
    return solids


# NOTE: align all coumpounded faces on XY plane
def align_faces_on_xy_plane(compound, y_position=0, gap=Const.DXF_SHEETS_GAP):
    faces_list = list(compound.Faces)
    processed = [align_and_orient(f) for f in faces_list]
    arranged = arrange_faces_adaptive(processed, gap=gap, y_position=y_position)

    return Part.makeCompound(arranged)


def align_and_orient(face):
    # --- align to XY plane ---
    normal = face.normalAt(0.5, 0.5)
    target = App.Vector(0, 0, 1)

    rot = App.Rotation(normal, target)
    placement = App.Placement(App.Vector(0, 0, 0), rot)

    aligned = face.copy().transformGeometry(placement.toMatrix())

    # --- move to origin ---
    center = aligned.BoundBox.Center
    aligned.translate(App.Vector(0, 0, 0) - center)

    # --- check bbox ---
    bb = aligned.BoundBox
    x_len = bb.XLength
    y_len = bb.YLength

    # --- rotate if needed ---
    if x_len > y_len:
        # rotate 90 deg around Z
        rot_z = App.Rotation(App.Vector(0, 0, 1), 90)
        aligned = aligned.transformGeometry(
            App.Placement(App.Vector(), rot_z).toMatrix()
        )

        # recenter again after rotation
        center = aligned.BoundBox.Center
        aligned.translate(App.Vector(0, 0, 0) - center)

    return aligned


def arrange_faces_adaptive(faces, gap=5, y_position=0):
    arranged = []
    offset = 0

    for f in faces:
        bb = f.BoundBox
        short_side = min(bb.XLength, bb.YLength)

        moved = f.copy()
        moved.translate(App.Vector(offset, y_position, 0))

        arranged.append(moved)

        offset += short_side + gap

    return arranged


def align_to_xy(face):
    normal = face.normalAt(0.5, 0.5)
    target = App.Vector(0, 0, 1)

    rot = App.Rotation(normal, target)
    placement = App.Placement(App.Vector(0, 0, 0), rot)

    return face.copy().transformGeometry(placement.toMatrix())


def move_to_origin(shape):
    center = shape.BoundBox.Center
    vec = App.Vector(0, 0, 0) - center

    s = shape.copy()
    s.translate(vec)
    return s


def arrange_faces(faces, pitch=50):
    arranged = []

    for i, f in enumerate(faces):
        moved = f.copy()
        moved.translate(App.Vector(0, i * pitch, 0))
        arranged.append(moved)

    return arranged


# ===================
# === ENTRY POINT ===
# ===================
selection_ex = Gui.Selection.getSelectionEx()
step_obj = selection_ex[0].Object
step_obj.ViewObject.Visibility = False
# create bound box
box = create_cube(selection_ex)
bbox = box.BoundBox
# create cutting sheets
x_sheets_info = sheet_info(bounder_length=bbox.XLength, vec=Base.Vector(1, 0, 0))
y_sheets_info = sheet_info(bounder_length=bbox.YLength, vec=Base.Vector(0, 1, 0))
x_faces = create_faces(box, x_sheets_info, False)
y_faces = create_faces(box, y_sheets_info, False)
x_cutting_sheets = faces_into_solids(x_faces, x_sheets_info, True)
y_cutting_sheets = faces_into_solids(y_faces, y_sheets_info, True)


# die_solids might has 2 or more solids and is array
die_solids = box.cut(step_obj.Shape).Solids
x_faces_0 = Part.makeCompound(create_faces(die_solids[0], x_sheets_info, True))
x_faces_1 = create_faces(die_solids[1], x_sheets_info, True)
y_faces_0 = create_faces(die_solids[0], y_sheets_info, True)
y_faces_1 = create_faces(die_solids[1], y_sheets_info, True)
# TODO: Should I compare z axis placement between die_solids[0] and die_solids[1]? If always die_solids[0] is lower than [1], it's no problem. Check This behave later

# NOTE: LOWER DIE INTER SECTIONAL TREATMENT
x_lower_offset = -Const.CUBE_Z_OFFSET / 2
y_lower_offset = -Const.CUBE_TOTAL_HEIGHT - (Const.CUBE_Z_OFFSET) / 2
App.Console.PrintMessage(f"  y_lower_offset: {y_lower_offset}\n")
x_cutting_sheets.translate(App.Vector(0, 0, x_lower_offset))
y_cutting_sheets.translate(App.Vector(0, 0, y_lower_offset))

# LOWER:  execute boolean cut
x_slotted_0 = x_faces_0.cut(y_cutting_sheets)
y_slotted_0 = y_faces_0.cut(x_cutting_sheets)
comp_x_lower = Part.makeCompound(x_slotted_0)
comp_y_lower = Part.makeCompound(y_slotted_0)
App.ActiveDocument.addObject("Part::Feature", "x_lower_die").Shape = comp_x_lower
App.ActiveDocument.addObject("Part::Feature", "y_lower_die").Shape = comp_y_lower


# NOTE: UPPER DIE INTER SECTIONAL TREATMENT

# first, bring buck sheetes to z = 0 + CUBE_Z_OFFSET
x_upper_offset = (
    +Const.CUBE_Z_OFFSET / 2
    + (-Const.CUBE_TOTAL_HEIGHT - Const.CUBE_Z_OFFSET + Const.SAFETY_HEIGHT) / 2
)
y_upper_offset = (
    (Const.CUBE_TOTAL_HEIGHT + (Const.CUBE_Z_OFFSET) / 2)
    - Const.CUBE_Z_OFFSET
    + Const.SAFETY_HEIGHT
    + (Const.CUBE_TOTAL_HEIGHT + Const.CUBE_Z_OFFSET - Const.SAFETY_HEIGHT) / 2
)
App.Console.PrintMessage(f"  y_lower_offset: {y_lower_offset}\n")
x_cutting_sheets.translate(App.Vector(0, 0, x_upper_offset))
y_cutting_sheets.translate(App.Vector(0, 0, y_upper_offset))
x_slotted_1 = x_faces_1.cut(y_cutting_sheets)
y_slotted_1 = y_faces_1.cut(x_cutting_sheets)
comp_x_upper = Part.makeCompound(x_slotted_1)
comp_y_upper = Part.makeCompound(y_slotted_1)
App.ActiveDocument.addObject("Part::Feature", "x_upper_die").Shape = comp_x_upper
App.ActiveDocument.addObject("Part::Feature", "y_upper_die").Shape = comp_y_upper


x_lower_sheets = align_faces_on_xy_plane(comp_x_lower, y_position=100)
y_lower_sheets = align_faces_on_xy_plane(comp_y_lower, y_position=200)
x_upper_sheets = align_faces_on_xy_plane(comp_x_upper, y_position=300)
y_upper_sheets = align_faces_on_xy_plane(comp_y_upper, y_position=400)
App.ActiveDocument.addObject("Part::Feature", "x_lower_sheets").Shape = x_lower_sheets
App.ActiveDocument.addObject("Part::Feature", "y_lower_sheets").Shape = y_lower_sheets
App.ActiveDocument.addObject("Part::Feature", "x_upper_sheets").Shape = x_upper_sheets
App.ActiveDocument.addObject("Part::Feature", "y_upper_sheets").Shape = y_upper_sheets

App.ActiveDocument.recompute()
