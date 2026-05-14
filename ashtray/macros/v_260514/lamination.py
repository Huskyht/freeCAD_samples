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

# from const import consts, IntrSheetsInfo
# from toml_loader import load_toml, DieInfo, IntrSheetsInfo, DxfSettings, AppPreference
from toml_loader import (
    load_toml,
    DieInfo,
    LamiInfo,
    LamiSheetsInfo,
    DxfSettings,
    AppPreference,
)


def lamination(
    die_info: DieInfo, lami_info: LamiInfo, dxf_settings: DxfSettings, step_obj, box
):
    App.Console.PrintMessage("Creating laminating sheets ...\n")
    bbox = box.BoundBox

    if bbox.XLength >= bbox.YLength:
        sheets = LamiSheetsInfo.from_lami_info(
            bbox.YLength, App.Vector(0, 1, 0), lami_info
        )
    else:
        sheets = LamiSheetsInfo.from_lami_info(
            bbox.XLength, App.Vector(1, 0, 0), lami_info
        )

    die_solids = box.cut(step_obj.Shape).Solids
    # 0: lower, 1: upper
    faces_0 = create_offset_faces(die_solids[0], sheets, False)
    faces_1 = create_offset_faces(die_solids[1], sheets, True)

    sheets_0 = align_faces_on_xy_plane(faces_0, gap=dxf_settings.sheets_gap)
    sheets_1 = align_faces_on_xy_plane(faces_1, gap=dxf_settings.sheets_gap)

    comp_sheets_list = [sheets_0, sheets_1]
    aligned_comp_sheets = arrange_faces_y(comp_sheets_list, gap=dxf_settings.sheets_gap)
    App.ActiveDocument.addObject(
        "Part::Feature", "lower_die"
    ).Shape = Part.makeCompound(faces_0)
    App.ActiveDocument.addObject(
        "Part::Feature", "upper_die"
    ).Shape = Part.makeCompound(faces_1)

    App.ActiveDocument.addObject(
        "Part::Feature", "lower_sheets"
    ).Shape = aligned_comp_sheets[0]
    App.ActiveDocument.addObject(
        "Part::Feature", "upper_sheets"
    ).Shape = aligned_comp_sheets[1]

    App.Console.PrintMessage(" Creating laminating sheets ...\n")


def create_offset_faces(
    shape, sheets: LamiSheetsInfo, offset_to_outside=True, as_compound=False
):
    interval = sheets.thickness
    offsets = []

    if offset_to_outside:
        half_thick = sheets.thickness / 2
    else:
        half_thick = -sheets.thickness / 2

    if is_even(sheets.sheet_num):
        base = interval / 2.0
        for i in range(sheets.sheet_num // 2):
            offsets.append(base + i * interval + half_thick)
            offsets.append(-(base + i * interval + half_thick))
    else:
        offsets.append(0)
        for i in range(1, sheets.sheet_num // 2 + 1):
            offsets.append(i * interval + half_thick)
            offsets.append(-(i * interval + half_thick))

    offsets_sorted = quick_sort(offsets)
    wires = []

    for offset in offsets_sorted:
        wires += slice_wires(shape, sheets.vec, offset)

    faces = [Part.Face(w) for w in wires if w.isClosed()]

    return Part.makeCompound(faces) if as_compound else faces


# =================
# === UTILITIES ===
# =================
def is_even(n: int) -> bool:
    return n % 2 == 0


def quick_sort(arr):
    if len(arr) <= 1:
        return arr
    pivot = arr[0]
    left = [x for x in arr[1:] if x < pivot]
    right = [x for x in arr[1:] if x >= pivot]
    return quick_sort(left) + [pivot] + quick_sort(right)


def slice_wires(shape, vec, offset):
    return list(shape.slice(vec, offset))


# NOTE: To extrude symmetric, Sepalate treatement as pos or neg direction and treat each side of faces.
def faces_to_solids(faces, sheets: IntrSheetsInfo, as_compound=False):
    direction = sheets.vec.normalize()
    half = (sheets.thickness + sheets.thick_gap) / 2.0
    print(f"DEBUG: half : {half}")

    solids = []
    for f in faces:
        solid = f.extrude(direction * half).fuse(f.extrude(direction * -half))
        solids.append(solid)

    return Part.makeCompound(solids) if as_compound else solids


def create_section_faces(solid, sheets):
    return create_faces(solid, sheets, as_compound=True)


def create_cut_result(base_faces, tool):
    return base_faces.cut(tool)


def process_lower(x_faces, y_faces, x_tool, y_tool):
    x_result = create_cut_result(x_faces, y_tool)
    y_result = create_cut_result(y_faces, x_tool)

    return Part.makeCompound(
        [
            Part.makeCompound(x_result),
            Part.makeCompound(y_result),
        ]
    )


def process_upper(x_faces, y_faces, x_tool, y_tool):
    x_result = create_cut_result(x_faces, y_tool)
    y_result = create_cut_result(y_faces, x_tool)

    return Part.makeCompound(
        [
            Part.makeCompound(x_result),
            Part.makeCompound(y_result),
        ]
    )


# NOTE: align all coumpounded faces on XY plane
def align_faces_on_xy_plane(faces_list, gap):
    processed = [align_and_orient(f) for f in faces_list]
    arranged = arrange_faces_adaptive(processed, gap=gap, y_position=0)

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


def arrange_faces_adaptive(faces, gap=5.0, y_position=0):
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


def arrange_faces_y(faces_list, gap=5.0):
    arranged = []
    offset = 0

    for fl in faces_list:
        bb = fl.BoundBox

        moved = fl.copy()
        moved.translate(App.Vector(0, offset + bb.YLength / 2, 0))
        arranged.append(moved)

        offset += bb.YLength + gap
    return arranged


def arrange_faces(faces, pitch=50):
    arranged = []

    for i, f in enumerate(faces):
        moved = f.copy()
        moved.translate(App.Vector(0, i * pitch, 0))
        arranged.append(moved)

    return arranged
