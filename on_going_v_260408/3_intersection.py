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

# from const import consts, sheet_info
from toml_loader import toml_consts, sheet_info


def create_faces(shape, sheets: sheet_info, as_compound=False):
    interval = sheets.interval + sheets.thickness
    offsets = []

    if is_even(sheets.sheet_num):
        base = interval / 2
        for i in range(sheets.sheet_num // 2):
            offsets.append(base + i * interval)
    else:
        offsets.append(0)
        for i in range(1, sheets.sheet_num // 2 + 1):
            offsets.append(i * interval)

    wires = []
    for offset in offsets:
        wires += slice_wires(shape, sheets.vec, offset)
        if offset != 0:
            wires += slice_wires(shape, sheets.vec, -offset)

    faces = [Part.Face(w) for w in wires if w.isClosed()]

    return Part.makeCompound(faces) if as_compound else faces


# =================
# === UTILITIES ===
# =================
def is_even(n: int) -> bool:
    return n % 2 == 0


def slice_wires(shape, vec, offset):
    return list(shape.slice(vec, offset))


# NOTE: To extrude symmetric, Sepalate treatement as pos or neg direction and treat each side of faces.
def faces_to_solids(faces, sheets: sheet_info, as_compound=False):
    direction = sheets.vec.normalize()
    half = sheets.thickness / 2

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
def align_faces_on_xy_plane(compound, y_position, gap):
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


def main():
    consts = toml_consts().config_loader()
    doc = App.ActiveDocument
    sel = Gui.Selection.getSelectionEx()
    App.Console.PrintMessage("Creating Inter-sectional sheets ...\n")

    step_obj = sel[0].Object
    box_obj = sel[1].Object
    box = box_obj.Shape

    step_obj.ViewObject.Visibility = False

    bbox = box.BoundBox

    # FOR CUTTING SHEETS
    # sheet definitions
    x_sheets = sheet_info(bbox.XLength, App.Vector(1, 0, 0))
    y_sheets = sheet_info(bbox.YLength, App.Vector(0, 1, 0))

    x_faces = create_faces(box, x_sheets)
    y_faces = create_faces(box, y_sheets)

    x_cutting_sheets = faces_to_solids(x_faces, x_sheets, True)
    y_cutting_sheets = faces_to_solids(y_faces, y_sheets, True)

    # split die
    # die_solids might has 2 or more solids and is array
    die_solids = box.cut(step_obj.Shape).Solids

    # !TODO: Below codes does NOT REFACTOR YET...
    x_faces_0 = create_faces(die_solids[0], x_sheets, True)
    x_faces_1 = create_faces(die_solids[1], x_sheets, True)
    y_faces_0 = create_faces(die_solids[0], y_sheets, True)
    y_faces_1 = create_faces(die_solids[1], y_sheets, True)

    # NOTE: LOWER DIE INTER SECTIONAL TREATMENT
    x_lower_offset = -consts.cube_z_offset / 2
    y_lower_offset = -consts.cube_total_height - (consts.cube_z_offset) / 2
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

    # NOTE: UPPER DIE INTER SECTIONAL TREATMENT

    # first, bring buck sheetes to z = 0 + CUBE_Z_OFFSET
    x_upper_offset = (
        +consts.cube_z_offset / 2
        + (-consts.cube_total_height - consts.cube_z_offset + consts.safety_height) / 2
    )
    y_upper_offset = (
        (consts.cube_total_height + (consts.cube_z_offset) / 2)
        - consts.cube_z_offset
        + consts.safety_height
        + (consts.cube_total_height + consts.cube_z_offset - consts.safety_height) / 2
    )
    App.Console.PrintMessage(f"  y_lower_offset: {y_lower_offset}\n")
    x_cutting_sheets.translate(App.Vector(0, 0, x_upper_offset))
    y_cutting_sheets.translate(App.Vector(0, 0, y_upper_offset))
    x_slotted_1 = x_faces_1.cut(y_cutting_sheets)
    y_slotted_1 = y_faces_1.cut(x_cutting_sheets)
    comp_x_upper = Part.makeCompound(x_slotted_1)
    comp_y_upper = Part.makeCompound(y_slotted_1)
    comp_upper = Part.makeCompound([comp_x_upper, comp_y_upper])
    App.ActiveDocument.addObject("Part::Feature", "upper_die").Shape = comp_upper

    x_lower_sheets = align_faces_on_xy_plane(
        comp_x_lower, y_position=100, gap=consts.dxf_sheets_gap
    )
    y_lower_sheets = align_faces_on_xy_plane(
        comp_y_lower, y_position=200, gap=consts.dxf_sheets_gap
    )
    x_upper_sheets = align_faces_on_xy_plane(
        comp_x_upper, y_position=300, gap=consts.dxf_sheets_gap
    )
    y_upper_sheets = align_faces_on_xy_plane(
        comp_y_upper, y_position=400, gap=consts.dxf_sheets_gap
    )
    App.ActiveDocument.addObject(
        "Part::Feature", "x_lower_sheets"
    ).Shape = x_lower_sheets
    App.ActiveDocument.addObject(
        "Part::Feature", "y_lower_sheets"
    ).Shape = y_lower_sheets
    App.ActiveDocument.addObject(
        "Part::Feature", "x_upper_sheets"
    ).Shape = x_upper_sheets
    App.ActiveDocument.addObject(
        "Part::Feature", "y_upper_sheets"
    ).Shape = y_upper_sheets

    # lower = die_solids[0]
    # upper = die_solids[1]

    # # create section faces
    # x_lower_faces = create_section_faces(lower, x_sheets)
    # y_lower_faces = create_section_faces(lower, y_sheets)

    # x_upper_faces = create_section_faces(upper, x_sheets)
    # y_upper_faces = create_section_faces(upper, y_sheets)

    # # process
    # lower_result = process_lower(x_lower_faces, y_lower_faces, x_tool, y_tool)
    # upper_result = process_upper(x_upper_faces, y_upper_faces, x_tool, y_tool)

    # # show
    # doc.addObject("Part::Feature", "lower_die").Shape = lower_result
    # doc.addObject("Part::Feature", "upper_die").Shape = upper_result

    doc.removeObject(box_obj.Name)
    doc.recompute()
    App.Console.PrintMessage(" Creating Inter-sectional sheets ...\n")


if __name__ == "__main__":
    main()
