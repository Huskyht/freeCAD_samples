from tomllib import load
import FreeCAD as App
import FreeCADGui as Gui
import Part
import Draft

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
    LamiInfo,
    LamiSheetsInfo,
    DxfSettings,
)


def lamination(lami_info: LamiInfo, dxf_settings: DxfSettings, step_obj, box):
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
    faces_0 = create_offset_faces(die_solids[0], sheets, False, False)
    faces_1 = create_offset_faces(die_solids[1], sheets, True, False)

    enum_faces_0 = add_enumurate_number(
        faces_0, False, dxf_settings.font_path, dxf_settings.text_height
    )
    enum_faces_1 = add_enumurate_number(
        faces_1, True, dxf_settings.font_path, dxf_settings.text_height
    )

    sheets_0 = align_faces_on_xy_plane(enum_faces_0, gap=dxf_settings.sheets_gap)
    sheets_1 = align_faces_on_xy_plane(enum_faces_1, gap=dxf_settings.sheets_gap)
    # sheets_0 = align_faces_on_xy_plane(faces_0, gap=dxf_settings.sheets_gap)
    # sheets_1 = align_faces_on_xy_plane(faces_1, gap=dxf_settings.sheets_gap)

    comp_sheets_list = [sheets_0, sheets_1]
    aligned_comp_sheets = arrange_faces_y(comp_sheets_list, gap=dxf_settings.sheets_gap)

    # ss_0 = add_enumurate_number(
    #     sheets_0, dxf_settings.font_path, dxf_settings.text_height
    # )
    # ss_1 = add_enumurate_number(
    #     sheets_1, dxf_settings.font_path, dxf_settings.text_height
    # )

    App.ActiveDocument.addObject(
        "Part::Feature", "lower_die"
    ).Shape = Part.makeCompound(enum_faces_0)
    App.ActiveDocument.addObject(
        "Part::Feature", "upper_die"
    ).Shape = Part.makeCompound(enum_faces_1)

    App.ActiveDocument.addObject(
        "Part::Feature", "lower_sheets"
    ).Shape = aligned_comp_sheets[0]
    # App.ActiveDocument.addObject(
    #     "Part::Feature", "enum_number_0"
    # ).Shape = Part.makeCompound(ss_0)
    App.ActiveDocument.addObject(
        "Part::Feature", "upper_sheets"
    ).Shape = aligned_comp_sheets[1]
    # App.ActiveDocument.addObject(
    #     "Part::Feature", "enum_number_1"
    # ).Shape = Part.makeCompound(ss_1)

    App.Console.PrintMessage(" Creating laminating sheets ...\n")


def create_offset_faces(
    shape, sheets: LamiSheetsInfo, offset_to_outside=True, as_compound=False
):
    interval = sheets.thickness
    offsets = []

    if offset_to_outside:
        half_thick = sheets.thickness / 2.0
    else:
        half_thick = -sheets.thickness / 2.0

    if is_even(sheets.sheet_num):
        base = interval / 2.0
        for i in range(0, sheets.sheet_num // 2):
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


def add_enumurate_number(faces_list, is_upper, font, text_height):
    doc = App.ActiveDocument
    # doc.disableRecompute()

    # faces_list = faces_comp.SubShapes
    font_path = font
    final_shape = []
    dummy_ss = Draft.make_shapestring("INIT", font_path, text_height, 0.0)
    # dummy_ss.touch()
    vec = faces_list[0].normalAt(0.5, 0.5)
    if vec == App.Vector(1, 0, 0):
        rot = App.Rotation(App.Vector(0, 0, 1), -90)
        dummy_ss.Placement = App.Placement(App.Vector(0, 0, 0), rot)

    for num, face in enumerate(faces_list, start=1):
        # text_shape = Draft.make_shapestring(str(num), font_path, text_height, 0.0)
        dummy_ss.String = str(num)
        dummy_ss.touch()
        doc.recompute()

        text_shape = dummy_ss.Shape.copy()

        if vec == App.Vector(1, 0, 0):
            to_xy_rot = App.Rotation(App.Vector(0, 1, 0), 90)
            text_shape.transformShape(
                App.Placement(App.Vector(0, 0, 0), to_xy_rot).toMatrix()
            )
            # to_xy_rot = App.Rotation(App.Vector(0, 0, 1), -90)
            # text_shape.transformShape(
            #     App.Placement(App.Vector(0, 0, 0), to_xy_rot).toMatrix()
            # )
        elif vec == App.Vector(0, 1, 0):
            to_xy_rot = App.Rotation(App.Vector(1, 0, 0), -90)
            text_shape.transformShape(
                App.Placement(App.Vector(0, 0, 0), to_xy_rot).toMatrix()
            )

        bbox = text_shape.BoundBox
        com = face.CenterOfMass
        face_bbox = face.BoundBox
        x_offset = 0.0
        y_offset = 0.0
        z_offset = 0.0
        if is_upper:
            if vec == App.Vector(1, 0, 0):
                x_offset = com.x - (bbox.XMax - bbox.XMin) / 2 + 0.01
                y_offset = (bbox.YMax - bbox.YMin) / 2
                z_offset = face_bbox.ZMin + (bbox.ZMax - bbox.ZMin) + 5
            elif vec == App.Vector(0, 1, 0):
                x_offset = (bbox.XMax - bbox.XMin) / 2
                y_offset = com.y - (bbox.YMax - bbox.YMin) / 2 + 0.01
                z_offset = face_bbox.ZMax - (bbox.ZMax - bbox.ZMin) / 2 - 2

        else:
            if vec == App.Vector(1, 0, 0):
                x_offset = com.x - (bbox.XMax - bbox.XMin) / 2 + 0.01
                y_offset = face_bbox.YMax - bbox.YMax - 2
                z_offset = face_bbox.ZMax - (bbox.ZMax - bbox.ZMin) / 2 - 2
            elif vec == App.Vector(0, 1, 0):
                x_offset = face_bbox.XMax - bbox.XMax - 2
                y_offset = com.y - (bbox.YMax - bbox.YMin) / 2 + 0.01
                z_offset = face_bbox.ZMin + (bbox.ZMax - bbox.ZMin) + 2

        text_move_placement = App.Placement(
            App.Vector(x_offset, y_offset, z_offset),
            App.Rotation(),
        )
        text_shape.transformShape(text_move_placement.toMatrix())

        combined_shape = Part.makeCompound([face, text_shape])

        final_shape.append(combined_shape)

    doc.removeObject(dummy_ss.Name)

    return final_shape


# NOTE: align all coumpounded faces on XY plane
def align_faces_on_xy_plane(faces_list, gap):
    processed = [align_and_orient(f) for f in faces_list]
    arranged = arrange_faces_adaptive(processed, gap=gap, y_position=0)

    return Part.makeCompound(arranged)


def align_and_orient(combined_face):
    # --- align to XY plane ---
    normal = combined_face.Faces[0].normalAt(0.5, 0.5)
    target = App.Vector(0, 0, 1)

    rot = App.Rotation(normal, target)
    placement = App.Placement(App.Vector(0, 0, 0), rot)

    aligned = combined_face.copy().transformGeometry(placement.toMatrix())

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
