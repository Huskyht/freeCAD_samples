import FreeCAD
import FreeCADGui as Gui
import Part


# from toml_loader import (
#     load_toml,
#     DxfSettings,
# )
from config_loader import DxfSettings


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
    target = FreeCAD.Vector(0, 0, 1)

    rot = FreeCAD.Rotation(normal, target)
    placement = FreeCAD.Placement(FreeCAD.Vector(0, 0, 0), rot)

    aligned = combined_face.copy().transformGeometry(placement.toMatrix())

    # ── move to origin ────────────────────────────────────────────────────
    center = aligned.BoundBox.Center
    aligned.translate(FreeCAD.Vector(0, 0, 0) - center)

    # ── check bbox ────────────────────────────────────────────────────────
    bb = aligned.BoundBox
    x_len = bb.XLength
    y_len = bb.YLength

    # ── rotate if needed ──────────────────────────────────────────────────
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


def arrange_faces(faces, pitch=50):
    arranged = []

    for i, f in enumerate(faces):
        moved = f.copy()
        moved.translate(FreeCAD.Vector(0, i * pitch, 0))
        arranged.append(moved)

    return arranged


# ╭──────────────────────────────────────────────────────────╮
# │                     Main entry point                     │
# ╰──────────────────────────────────────────────────────────╯
# def cut_and_rearrange_wrapper():
#     FreeCAD.Console.PrintMessage("aligning faces ...\n")
#     toml_data = load_toml()
#     dxf_settings = DxfSettings.from_toml(toml_data)
#     # die_info = DieInfo.from_toml(toml_data)
#     # app_preference = AppPreference.from_toml(toml_data)
#
#     sel = Gui.Selection.getSelection()
#
#     if not sel:
#         FreeCAD.Console.PrintMessage("Please select cut/slice  objects simultaneously.")
#         return None
#     elif len(sel) < 2:
#         FreeCAD.Console.PrintMessage("Please select cut/slice  objects simultaneously.")
#         return None
#     elif len(sel) == 2:
#         cutting_obj = sel[1].Shape
#     elif len(sel) > 2:
#         cutting_obj = Part.makeCompound(sel[1:-1]).Shape
#
#     # sheets = []
#     obj = sel[0].Shape
#
#     comp_obj = cutting_tool(obj, cutting_obj)
#     aligned_sheets = align_faces_on_xy_plane(comp_obj, dxf_settings.sheets_gap)
#
#     FreeCAD.ActiveDocument.addObject("Part::Feature", "sheets").Shape = aligned_sheets
#     FreeCAD.Console.PrintMessage("faces are aligned")


class CutAndRearrangeCmd:
    """This class defines the toolbar button and menu action for FreeCAD."""

    def GetResources(self):
        # TODO: the thumbnail is set to temporary png. NEED TO CREATE AND SET IT.
        return {
            "Pixmap": "cut_and_rearrange.png",
            "MenuText": "Cut and Rearrange dies sheets",
            "ToolTip": "Cut Sheets with solid and make new sheets on xy plane",
        }

    # ╔══════════════════════════════════════════════════════════╗
    # ║                       ENTRY POINT                        ║
    # ╚══════════════════════════════════════════════════════════╝
    def Activated(self):
        """This function turn imported model to easy-to-use Solid model and open in New document."""
        FreeCAD.Console.PrintMessage("  Create new dies sheets...\n")
        # try:
        # cut_and_rearrange_wrapper()

        FreeCAD.Console.PrintMessage("aligning faces ...\n")
        # toml_data = load_toml()
        # dxf_settings = DxfSettings.from_toml(toml_data)
        dxf_settings = DxfSettings.from_cache()
        # die_info = DieInfo.from_toml(toml_data)
        # app_preference = AppPreference.from_toml(toml_data)

        sel = Gui.Selection.getSelection()

        obj = sel[0].Shape
        name = sel[0].Name
        cutting_obj = None
        if not sel:
            FreeCAD.Console.PrintMessage(
                "Please select cut/slice  objects simultaneously."
            )
            return
        elif len(sel) < 2:
            FreeCAD.Console.PrintMessage(
                "Please select cut/slice  objects simultaneously."
            )
            return
        elif len(sel) == 2:
            cutting_obj = sel[1].Shape
        elif len(sel) > 2:
            shp_list = [s.Shape for s in sel[1:]]
            print(f"shp_list: {shp_list}")
            cutting_obj = Part.makeCompound(shp_list)

        # sheets = []
        if not cutting_obj:
            return

        cutted_sheets_list = cutting_tool(obj, cutting_obj)
        comp_obj = Part.makeCompound(cutted_sheets_list)
        aligned_sheets = align_faces_on_xy_plane(
            cutted_sheets_list, dxf_settings.sheets_gap
        )

        FreeCAD.ActiveDocument.addObject(
            "Part::Feature", "sheets"
        ).Shape = aligned_sheets
        FreeCAD.ActiveDocument.removeObject(name)
        FreeCAD.ActiveDocument.addObject("Part::Feature", name).Shape = comp_obj
        FreeCAD.Console.PrintMessage("faces are aligned")

        # except Exception as e:
        #     FreeCAD.Console.PrintError(f"Error executing cut_and_reaarange: {str(e)}\n")

    def IsActive(self):
        """Optional: Determines if the button is clickable.
        Returns True if a document is open, otherwise greys out the button."""
        return FreeCAD.ActiveDocument is not None


# Register this script into FreeCAD's global command manager.
# The string 'create_cube' MUST exactly match the item you put into self.list inside InitGui.py
Gui.addCommand("cut_and_rearrange", CutAndRearrangeCmd())
