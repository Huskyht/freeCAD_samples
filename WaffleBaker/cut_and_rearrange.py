from tomllib import load
import FreeCAD as App
import FreeCADGui as Gui
import Part
import CompoundTools.Explode as explode

import sys
import os

current_dir = os.path.dirname(__file__)
if current_dir not in sys.path:
    sys.path.append(current_dir)

from toml_loader import (
    load_toml,
    DxfSettings,
)


# ── this tool will return compounded objects list which is different ──
# ── from Part.Cut .
# ── if com_obj has child objects of compounded, return list of compound. ──
def cutting_tool(comp_obj, slicer_obj):
    comp_list = comp_obj.childShapes()
    result = []
    for c in comp_list:
        result.append(c.cut(slicer_obj))

    return result


# NOTE: align all coumpounded faces on XY plane
def align_faces_on_xy_plane(comp_obj, gap):
    processed = [align_and_orient(o) for o in comp_obj]
    arranged = arrange_faces_adaptive(processed, gap=gap, y_position=0)

    return Part.makeCompound(arranged)


def align_and_orient(combined_face):
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


# ╭──────────────────────────────────────────────────────────╮
# │                     Main entry point                     │
# ╰──────────────────────────────────────────────────────────╯
def cut_and_rearrange_wrapper():
    App.Console.PrintMessage("aligning faces ...\n")
    toml_data = load_toml()
    dxf_settings = DxfSettings.from_toml(toml_data)
    # die_info = DieInfo.from_toml(toml_data)
    # app_preference = AppPreference.from_toml(toml_data)

    sel = Gui.Selection.getSelection()

    if not sel:
        App.Console.PrintMessage("Please select cut/slice  objects simultaneously.")
        raise
    elif len(sel) < 2:
        App.Console.PrintMessage("Please select cut/slice  objects simultaneously.")
        raise

    # sheets = []
    obj = sel[0].Shape
    slicer = sel[1].Shape

    comp_obj = cutting_tool(obj, slicer)
    aligned_sheets = align_faces_on_xy_plane(comp_obj, dxf_settings.sheets_gap)

    App.ActiveDocument.addObject("Part::Feature", "sheets").Shape = aligned_sheets
    App.Console.PrintMessage("faces are aligned")


class CutAndRearrangeCmd:
    """This class defines the toolbar button and menu action for FreeCAD."""

    def GetResources(self):
        # TODO: the thumbnail is set to temporary png. NEED TO CREATE AND SET IT.
        return {
            "Pixmap": "2_create_cube.png",
            "MenuText": "Cut and Rearrange dies sheets",
            "ToolTip": "Cut Sheets with solid and make new sheets on xy plane",
        }

    # ╔══════════════════════════════════════════════════════════╗
    # ║                       ENTRY POINT                        ║
    # ╚══════════════════════════════════════════════════════════╝
    def Activated(self):
        """This function turn imported model to easy-to-use Solid model and open in New document."""
        App.Console.PrintMessage("  Create new dies sheets...\n")
        try:
            cut_and_rearrange_wrapper()

        except Exception as e:
            App.Console.PrintError(f"Error executing cut_and_reaarange: {str(e)}\n")

    def IsActive(self):
        """Optional: Determines if the button is clickable.
        Returns True if a document is open, otherwise greys out the button."""
        return App.ActiveDocument is not None


# Register this script into FreeCAD's global command manager.
# The string 'create_cube' MUST exactly match the item you put into self.list inside InitGui.py
Gui.addCommand("cut_and_rearrange", CutAndRearrangeCmd())
