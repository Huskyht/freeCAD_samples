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

# Now import your module
from const import Const, sheet_info


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
box = selection_ex[1].Object.Shape
box_name = selection_ex[1].Object.Name
step_obj.ViewObject.Visibility = False

bbox = box.BoundBox
# create cutting sheets
x_sheets_info = sheet_info(bounder_length=bbox.XLength, vec=App.Base.Vector(1, 0, 0))
y_sheets_info = sheet_info(bounder_length=bbox.YLength, vec=App.Base.Vector(0, 1, 0))
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
comp_lower = Part.makeCompound([comp_x_lower, comp_y_lower])
App.ActiveDocument.addObject("Part::Feature", "lower_die").Shape = comp_lower
# App.ActiveDocument.addObject("Part::Feature", "x_lower_die").Shape = comp_x_lower
# App.ActiveDocument.addObject("Part::Feature", "y_lower_die").Shape = comp_y_lower


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
# App.ActiveDocument.addObject("Part::Feature", "x_upper_die").Shape = comp_x_upper
# App.ActiveDocument.addObject("Part::Feature", "y_upper_die").Shape = comp_y_upper
comp_upper = Part.makeCompound([comp_x_upper, comp_y_upper])
App.ActiveDocument.addObject("Part::Feature", "upper_die").Shape = comp_upper


x_lower_sheets = align_faces_on_xy_plane(comp_x_lower, y_position=100)
y_lower_sheets = align_faces_on_xy_plane(comp_y_lower, y_position=200)
x_upper_sheets = align_faces_on_xy_plane(comp_x_upper, y_position=300)
y_upper_sheets = align_faces_on_xy_plane(comp_y_upper, y_position=400)
App.ActiveDocument.addObject("Part::Feature", "x_lower_sheets").Shape = x_lower_sheets
App.ActiveDocument.addObject("Part::Feature", "y_lower_sheets").Shape = y_lower_sheets
App.ActiveDocument.addObject("Part::Feature", "x_upper_sheets").Shape = x_upper_sheets
App.ActiveDocument.addObject("Part::Feature", "y_upper_sheets").Shape = y_upper_sheets

App.ActiveDocument.removeObject(box_name)

App.ActiveDocument.recompute()
