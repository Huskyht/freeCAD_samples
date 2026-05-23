from tomllib import load
import FreeCAD as App
import FreeCADGui as Gui
import Part

import sys
import os

current_dir = os.path.dirname(__file__)
if current_dir not in sys.path:
    sys.path.append(current_dir)

from toml_loader import (
    load_toml,
    DxfSettings,
)


# NOTE: align all coumpounded faces on XY plane
def align_faces_on_xy_plane(comp_obj, gap):

    processed = [align_and_orient(o) for o in comp_obj.childShapes()]
    arranged = arrange_faces_adaptive(processed, gap=gap, y_position=0)

    return Part.makeCompound(arranged)


def align_and_orient(combined_face):
    App.Console.PrintMessage(f"combined_face: {combined_face.ShapeType} \n")
    # ── align to XY plane ─────────────────────────────────────────────────
    normal = combined_face.Faces[0].normalAt(0.5, 0.5)
    target = App.Vector(0, 0, 1)

    rot = App.Rotation(normal, target)
    placement = App.Placement(App.Vector(0, 0, 0), rot)

    aligned = combined_face.copy().transformGeometry(placement.toMatrix())

    # ── move to origin ────────────────────────────────────────────────────
    center = aligned.BoundBox.Center
    aligned.translate(App.Vector(0, 0, 0) - center)

    # ── check bbox ────────────────────────────────────────────────────────
    bb = aligned.BoundBox
    x_len = bb.XLength
    y_len = bb.YLength

    # ── rotate if needed ──────────────────────────────────────────────────
    if x_len > y_len:
        # ── rotate 90 deg around Z ────────────────────────────────────────────
        rot_z = App.Rotation(App.Vector(0, 0, 1), 90)
        aligned = aligned.transformGeometry(
            App.Placement(App.Vector(), rot_z).toMatrix()
        )

        # ── recenter again after rotation ─────────────────────────────────────
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


def main():
    App.Console.PrintMessage("aligning faces ...\n")
    toml_data = load_toml()
    dxf_settings = DxfSettings.from_toml(toml_data)
    # die_info = DieInfo.from_toml(toml_data)
    # app_preference = AppPreference.from_toml(toml_data)

    sel = Gui.Selection.getSelection()

    if not sel:
        App.Console.PrintMessage("Please select 1 or more object/s.")
        raise

    sheets = []
    for obj in sel:
        if obj.Shape.ShapeType == "Compound":
            sheets.append(align_faces_on_xy_plane(obj.Shape, dxf_settings.sheets_gap))

    if not sheets:
        App.Console.PrintMessage(
            f"failed to aligned faces. Please check obj is compounded correctly. \n"
        )

    aligned_sheets = arrange_faces_y(sheets, gap=dxf_settings.sheets_gap)
    for i, comp_sheets in enumerate(aligned_sheets):
        name = "sheets" + str(i)
        App.ActiveDocument.addObject("Part::Feature", name).Shape = comp_sheets

    App.Console.PrintMessage("faces are aligned")


if __name__ == "__main__":
    main()
