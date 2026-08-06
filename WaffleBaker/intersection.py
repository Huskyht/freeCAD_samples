import FreeCAD
import Part
import Draft

from config_loader import (
    DieInfo,
    IntrSecInfo,
    IntrSheetsInfo,
    DxfSettings,
)

# ╔══════════════════════════════════════════════════════════╗
# ║                       Intersection                       ║
# ╚══════════════════════════════════════════════════════════╝


def create_faces(shape, sheets: IntrSheetsInfo, as_compound=False):
    interval = sheets.interval + sheets.thickness + sheets.thick_gap
    offsets = []

    if is_even(sheets.sheet_num):
        base = interval / 2.0
        for i in range(sheets.sheet_num // 2):
            offsets.append(base + i * interval)
            offsets.append(-(base + i * interval))
    else:
        offsets.append(0)
        for i in range(1, sheets.sheet_num // 2 + 1):
            offsets.append(i * interval)
            offsets.append(-(i * interval))

    offsets_sorted = quick_sort(offsets)
    wires = []

    for offset in offsets_sorted:
        wires += slice_wires(shape, sheets.vec, offset)

    faces = [Part.Face(w) for w in wires if w.isClosed()]

    return Part.makeCompound(faces) if as_compound else faces


def create_offset_faces(
    shape, sheets: IntrSheetsInfo, offset_to_outside=True, as_compound=False
):
    interval = sheets.interval + sheets.thickness + sheets.thick_gap
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


# ╭──────────────────────────────────────────────────────────╮
# │                        UTILITIES                         │
# ╰──────────────────────────────────────────────────────────╯
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


# ── NOTE: To extrude symmetric, Sepalate treatement as pos or neg ─────
# ──       direction and treat each side of faces. ─────────────────────
def faces_to_solids(faces, sheets: IntrSheetsInfo, as_compound=False):
    direction = sheets.vec.normalize()
    half = (sheets.thickness + sheets.thick_gap) / 2.0

    solids = []
    for f in faces:
        solid = f.extrude(direction * half).fuse(f.extrude(direction * -half))
        solids.append(solid)

    return Part.makeCompound(solids) if as_compound else solids


def create_section_faces(solid, sheets):
    return create_faces(solid, sheets, as_compound=True)


def create_cut_result(base_faces, tool):
    return base_faces.cut(tool)


def add_enumurate_number(comp_obj, is_upper, font, text_height):
    doc = FreeCAD.ActiveDocument

    final_shape = []

    num_shapes = {}
    dummy_ss = Draft.make_shapestring("INIT", font, text_height, 0.0)
    for i in range(10):
        dummy_ss.String = str(i)
        dummy_ss.touch()
        doc.recompute([dummy_ss])
        num_shapes[str(i)] = dummy_ss.Shape.copy()
    doc.removeObject(dummy_ss.Name)

    vec = comp_obj.Faces[0].normalAt(0.5, 0.5)
    # if vec == FreeCAD.Vector(1, 0, 0):
    #     rot = FreeCAD.Rotation(FreeCAD.Vector(0, 0, 1), -90)
    #     dummy_ss.Placement = FreeCAD.Placement(FreeCAD.Vector(0, 0, 0), rot)

    for num, face in enumerate(comp_obj.Faces, start=1):
        # dummy_ss.String = str(num)
        # dummy_ss.touch()
        # doc.recompute([dummy_ss])
        num_str = str(num)
        char_shapes = []
        current_x_offset = 0.0

        for char in num_str:
            s = num_shapes[char].copy()
            if current_x_offset > 0:
                s.translate(FreeCAD.Vector(current_x_offset, 0, 0))
            char_shapes.append(s)
            current_x_offset += s.BoundBox.XLength * 1.1

        text_shape = Part.makeCompound(char_shapes)
        # text_shape = dummy_ss.Shape.copy()

        if vec == FreeCAD.Vector(1, 0, 0):
            rot = FreeCAD.Rotation(FreeCAD.Vector(0, 0, 1), -90)
            text_shape.Placement = FreeCAD.Placement(FreeCAD.Vector(0, 0, 0), rot)

            to_xy_rot = FreeCAD.Rotation(FreeCAD.Vector(0, 1, 0), 90)
            text_shape.transformShape(
                FreeCAD.Placement(FreeCAD.Vector(0, 0, 0), to_xy_rot).toMatrix()
            )
        elif vec == FreeCAD.Vector(0, 1, 0):
            to_xy_rot = FreeCAD.Rotation(FreeCAD.Vector(1, 0, 0), -90)
            text_shape.transformShape(
                FreeCAD.Placement(FreeCAD.Vector(0, 0, 0), to_xy_rot).toMatrix()
            )

        bbox = text_shape.BoundBox
        com = face.CenterOfMass
        face_bbox = face.BoundBox
        x_offset = 0.0
        y_offset = 0.0
        z_offset = 0.0
        if is_upper:
            if vec == FreeCAD.Vector(1, 0, 0):
                x_offset = com.x - (bbox.XMax - bbox.XMin) / 2 + 0.01
                y_offset = (bbox.YMax - bbox.YMin) / 2
                z_offset = face_bbox.ZMin + (bbox.ZMax - bbox.ZMin) + 5
            elif vec == FreeCAD.Vector(0, 1, 0):
                x_offset = (bbox.XMax - bbox.XMin) / 2
                y_offset = com.y - (bbox.YMax - bbox.YMin) / 2 + 0.01
                z_offset = face_bbox.ZMax - (bbox.ZMax - bbox.ZMin) / 2 - 2

        else:
            if vec == FreeCAD.Vector(1, 0, 0):
                x_offset = com.x - (bbox.XMax - bbox.XMin) / 2 + 0.01
                y_offset = face_bbox.YMax - bbox.YMax - 2
                z_offset = face_bbox.ZMax - (bbox.ZMax - bbox.ZMin) / 2 - 2
            elif vec == FreeCAD.Vector(0, 1, 0):
                x_offset = face_bbox.XMax - bbox.XMax - 2
                y_offset = com.y - (bbox.YMax - bbox.YMin) / 2 + 0.01
                z_offset = face_bbox.ZMin + (bbox.ZMax - bbox.ZMin) + 2

        text_move_placement = FreeCAD.Placement(
            FreeCAD.Vector(x_offset, y_offset, z_offset),
            FreeCAD.Rotation(),
        )
        text_shape.transformShape(text_move_placement.toMatrix())

        combined_shape = Part.makeCompound([face, text_shape])

        final_shape.append(combined_shape)

    # doc.removeObject(dummy_ss.Name)

    return final_shape


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


def create_clamp_slots(
    sheets, z_val: float, clamp_width: float, clamp_height: float, clamp_z: float
):
    # get representative face from compound or array[Part::Face] object

    if sheets.ShapeType == "Compound":
        rep_face = sheets.Faces[0]
    elif sheets.ShapeType == "Face":
        rep_face = sheets[0]
    else:
        return None

    # get paramameter range and normal direction
    u0, u1, v0, v1 = rep_face.ParameterRange
    u = (u0 + u1) / 2
    v = (v0 + v1) / 2

    face_normal = rep_face.normalAt(u, v)

    # define the positons of 2 cubes which is used for making clamp slots
    # First, define position on u-v plane
    # cube_v = v1 - z_val
    cube_pos_v = (u1 - u0) - z_val - clamp_height / 2
    cube_pos_u_0 = v0
    cube_pos_u_1 = v1

    pos_0 = rep_face.valueAt(cube_pos_v, cube_pos_u_0)
    pos_1 = rep_face.valueAt(cube_pos_v, cube_pos_u_1)

    # create new box which is used for cutting clamp slots
    cube_x = clamp_height
    cube_y = clamp_width
    cube_z = clamp_z

    # aligned.translate(FreeCAD.Vector(0, 0, 0) - center)
    cutting_tool_0 = Part.makeBox(cube_x, cube_y, cube_z)
    cutting_tool_1 = Part.makeBox(cube_x, cube_y, cube_z)
    cutting_tool_0.translate(FreeCAD.Vector(-cube_x / 2, -cube_y / 2, -cube_z / 10))
    cutting_tool_1.translate(FreeCAD.Vector(-cube_x / 2, -cube_y / 2, -cube_z / 10))
    rotation = FreeCAD.Rotation(FreeCAD.Vector(0, 0, 1), face_normal)

    # center_vec = FreeCAD.Vector(0, 0, -50.0)

    transition_0 = FreeCAD.Placement(pos_0, rotation)
    transition_1 = FreeCAD.Placement(pos_1, rotation)

    cutting_tool_0.transformShape(transition_0.toMatrix())
    cutting_tool_1.transformShape(transition_1.toMatrix())
    # FreeCAD.ActiveDocument.addObject("Part::Feature", "clamp_0").Shape = cutting_tool_0
    # FreeCAD.ActiveDocument.addObject("Part::Feature", "clamp_1").Shape = cutting_tool_1

    comp_cutting_tools = Part.makeCompound([cutting_tool_0, cutting_tool_1])

    return Part.makeCompound(sheets.cut(comp_cutting_tools))


# ── NOTE: align all coumpounded faces on XY plane ─────────────────────
def align_faces_on_xy_plane(list_compound, gap):
    # faces_list = list(compound.Faces)
    processed = [align_and_orient(c) for c in list_compound.childShapes()]
    arranged = arrange_faces_adaptive(processed, gap=gap, y_position=0)

    return Part.makeCompound(arranged)


def align_and_orient(comp):
    # ── align to XY plane ─────────────────────────────────────────────────
    normal = comp.Faces[0].normalAt(0.5, 0.5)
    target = FreeCAD.Vector(0, 0, 1)

    rot = FreeCAD.Rotation(normal, target)
    placement = FreeCAD.Placement(FreeCAD.Vector(0, 0, 0), rot)

    aligned = comp.copy().transformGeometry(placement.toMatrix())

    # ── move to origin ────────────────────────────────────────────────────
    center = aligned.BoundBox.Center
    aligned.translate(FreeCAD.Vector(0, 0, 0) - center)

    bb = aligned.BoundBox
    x_len = bb.XLength
    y_len = bb.YLength

    # --- rotate if needed ---
    if x_len > y_len:
        # ── rotate 90 deg around Z ────────────────────────────────────────────
        rot_z = FreeCAD.Rotation(FreeCAD.Vector(0, 0, 1), 90)
        aligned = aligned.transformGeometry(
            FreeCAD.Placement(FreeCAD.Vector(), rot_z).toMatrix()
        )

        # ── recenter again after rotation ─────────────────────────────────────
        center = aligned.BoundBox.Center
        aligned.translate(FreeCAD.Vector(0, 0, 0) - center)
    return aligned


def arrange_faces_adaptive(faces, gap=5.0, y_position=0):
    arranged = []
    offset = 0

    for f in faces:
        bb = f.BoundBox
        short_side = min(bb.XLength, bb.YLength)

        moved = f.copy()
        moved.translate(FreeCAD.Vector(offset, y_position, 0))

        arranged.append(moved)

        offset += short_side + gap

    return arranged


def align_to_xy(face):
    normal = face.normalAt(0.5, 0.5)
    target = FreeCAD.Vector(0, 0, 1)

    rot = FreeCAD.Rotation(normal, target)
    placement = FreeCAD.Placement(FreeCAD.Vector(0, 0, 0), rot)

    return face.copy().transformGeometry(placement.toMatrix())


def arrange_faces_y(faces_list, gap=5.0):
    arranged = []
    offset = 0

    for fl in faces_list:
        bb = fl.BoundBox

        moved = fl.copy()
        moved.translate(FreeCAD.Vector(0, offset + bb.YLength / 2, 0))
        arranged.append(moved)

        offset += bb.YLength + gap
    return arranged


def move_to_origin(shape):
    center = shape.BoundBox.Center
    vec = FreeCAD.Vector(0, 0, 0) - center

    s = shape.copy()
    s.translate(vec)
    return s


def arrange_faces(faces, pitch=50):
    arranged = []

    for i, f in enumerate(faces):
        moved = f.copy()
        moved.translate(FreeCAD.Vector(0, i * pitch, 0))
        arranged.append(moved)

    return arranged


# ╭──────────────────────────────────────────────────────────╮
# │                    main enrtry point                     │
# ╰──────────────────────────────────────────────────────────╯
def intersection(
    die_info: DieInfo,
    intr_sec_info: IntrSecInfo,
    dxf_settings: DxfSettings,
    step_obj,
    box,
):
    FreeCAD.Console.PrintMessage("Creating Inter-sectional sheets ...\n")

    bbox = box.BoundBox

    # ╭──────────────────────────────────────────────────────────╮
    # │                    FOR CUTTING SHEETS                    │
    # │                    sheet definitions                     │
    # ╰──────────────────────────────────────────────────────────╯
    x_sheets = IntrSheetsInfo.from_intr_sec_info(
        bbox.XLength, FreeCAD.Vector(1, 0, 0), intr_sec_info
    )
    y_sheets = IntrSheetsInfo.from_intr_sec_info(
        bbox.YLength, FreeCAD.Vector(0, 1, 0), intr_sec_info
    )
    FreeCAD.Console.PrintMessage(f"x_sheets: {x_sheets} \n")
    FreeCAD.Console.PrintMessage(f"y_sheets: {y_sheets} \n")

    x_faces = create_faces(box, x_sheets)
    y_faces = create_faces(box, y_sheets)
    FreeCAD.Console.PrintMessage(f"x_faces: {x_faces} \n")
    FreeCAD.Console.PrintMessage(f"y_faces: {y_faces} \n")

    x_cutting_sheets = faces_to_solids(x_faces, x_sheets, True)
    y_cutting_sheets = faces_to_solids(y_faces, y_sheets, True)

    # split die
    # die_solids might has 2 or more solids and is array
    die_solids = box.cut(step_obj.Shape).Solids

    # !TODO: Below codes does NOT REFACTOR YET...

    # x_faces_0 = create_faces(die_solids[0], x_sheets, True)
    # x_faces_1 = create_faces(die_solids[1], x_sheets, True)
    x_faces_0 = create_offset_faces(die_solids[0], x_sheets, False, True)
    x_faces_1 = create_offset_faces(die_solids[1], x_sheets, True, True)
    y_faces_0 = create_offset_faces(die_solids[0], y_sheets, False, True)
    y_faces_1 = create_offset_faces(die_solids[1], y_sheets, True, True)

    # NOTE: LOWER DIE INTER SECTIONAL TREATMENT
    x_lower_offset = -die_info.cube_z_offset / 2 - intr_sec_info.thick_gap / 2
    y_lower_offset = -die_info.cube_total_height - (die_info.cube_z_offset) / 2
    x_cutting_sheets.translate(FreeCAD.Vector(0, 0, x_lower_offset))
    y_cutting_sheets.translate(FreeCAD.Vector(0, 0, y_lower_offset))

    # LOWER:  execute boolean cut
    x_slotted_0 = x_faces_0.cut(y_cutting_sheets)
    y_slotted_0 = y_faces_0.cut(x_cutting_sheets)

    enum_x_faces_0 = add_enumurate_number(
        x_slotted_0, False, dxf_settings.font_path, dxf_settings.text_height
    )
    enum_y_faces_0 = add_enumurate_number(
        y_slotted_0, False, dxf_settings.font_path, dxf_settings.text_height
    )

    comp_x_lower = Part.makeCompound(enum_x_faces_0)
    comp_y_lower = Part.makeCompound(enum_y_faces_0)
    comp_lower = Part.makeCompound([comp_x_lower, comp_y_lower])
    FreeCAD.ActiveDocument.addObject("Part::Feature", "lower_die").Shape = comp_lower

    # NOTE: UPPER DIE INTER SECTIONAL TREATMENT

    # ── first, bring buck sheetes to z = 0 + CUBE_Z_OFFSET ────────────────
    x_upper_offset = (
        +die_info.cube_z_offset / 2
        + intr_sec_info.thick_gap
        + (
            -die_info.cube_total_height
            - die_info.cube_z_offset
            + die_info.safety_height
        )
        / 2
    )
    y_upper_offset = (
        (die_info.cube_total_height + (die_info.cube_z_offset) / 2)
        - die_info.cube_z_offset
        + die_info.safety_height
        + (die_info.cube_total_height + die_info.cube_z_offset - die_info.safety_height)
        / 2
    )
    x_cutting_sheets.translate(FreeCAD.Vector(0, 0, x_upper_offset))
    y_cutting_sheets.translate(FreeCAD.Vector(0, 0, y_upper_offset))
    x_slotted_1 = x_faces_1.cut(y_cutting_sheets)
    y_slotted_1 = y_faces_1.cut(x_cutting_sheets)

    # TODO: ADD clamping slot on x plane faces
    z_offset = (
        die_info.cube_total_height + die_info.cube_z_offset
    ) / 2 + intr_sec_info.sheet_thickness

    x_has_clamp_slots = create_clamp_slots(
        x_slotted_1,
        z_offset,
        intr_sec_info.clamp_slot_width,
        intr_sec_info.clamp_slot_height,
        bbox.XLength,
    )
    if x_has_clamp_slots is None:
        FreeCAD.Console.PrintMessage(f"x_has_clamp_slots: {x_has_clamp_slots} \n")
        return

    enum_x_faces_1 = add_enumurate_number(
        x_has_clamp_slots, True, dxf_settings.font_path, dxf_settings.text_height
    )
    # enum_x_faces_1 = add_enumurate_number(
    #     x_slotted_1, True, dxf_settings.font_path, dxf_settings.text_height
    # )
    enum_y_faces_1 = add_enumurate_number(
        y_slotted_1, True, dxf_settings.font_path, dxf_settings.text_height
    )
    comp_x_upper = Part.makeCompound(enum_x_faces_1)
    comp_y_upper = Part.makeCompound(enum_y_faces_1)
    comp_upper = Part.makeCompound([comp_x_upper, comp_y_upper])
    FreeCAD.ActiveDocument.addObject("Part::Feature", "upper_die").Shape = comp_upper

    x_lower_sheets = align_faces_on_xy_plane(comp_x_lower, gap=dxf_settings.sheets_gap)
    y_lower_sheets = align_faces_on_xy_plane(comp_y_lower, gap=dxf_settings.sheets_gap)
    x_upper_sheets = align_faces_on_xy_plane(comp_x_upper, gap=dxf_settings.sheets_gap)
    y_upper_sheets = align_faces_on_xy_plane(comp_y_upper, gap=dxf_settings.sheets_gap)

    comp_sheets_list = [x_lower_sheets, y_lower_sheets, x_upper_sheets, y_upper_sheets]
    aligned_comp_sheets = arrange_faces_y(comp_sheets_list, gap=dxf_settings.sheets_gap)

    FreeCAD.ActiveDocument.addObject(
        "Part::Feature", "x_lower_sheets"
    ).Shape = aligned_comp_sheets[0]
    FreeCAD.ActiveDocument.addObject(
        "Part::Feature", "y_lower_sheets"
    ).Shape = aligned_comp_sheets[1]
    FreeCAD.ActiveDocument.addObject(
        "Part::Feature", "x_upper_sheets"
    ).Shape = aligned_comp_sheets[2]
    FreeCAD.ActiveDocument.addObject(
        "Part::Feature", "y_upper_sheets"
    ).Shape = aligned_comp_sheets[3]

    FreeCAD.Console.PrintMessage(" Creating Inter-sectional sheets ...\n")
