import FreeCAD as App
import FreeCADGui as Gui
import Part

# use for rounding up bbox
import math

# Macro importing const in another file
import sys
import os

# Get current macro directory
current_dir = os.path.dirname(__file__)
# Add it to Python path
if current_dir not in sys.path:
    sys.path.append(current_dir)

from const import Const


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

    # Output results to the Report View (Console)
    App.Console.PrintMessage("\n--- Geometry Analysis Results ---\n")

    # 1. Bounding Box Dimensions
    App.Console.PrintMessage("Bounding Box Sizes:\n")
    App.Console.PrintMessage(f"  X: {bbox.XLength:.4f}\n")
    App.Console.PrintMessage(f"  Y: {bbox.YLength:.4f}\n")
    App.Console.PrintMessage(f"  Z: {bbox.ZLength:.4f}\n")

    # 2. Normal Vector of the first selected face
    if first_face_normal:
        App.Console.PrintMessage("Normal Vector (First Face):\n")
        App.Console.PrintMessage(
            f"  (x, y, z): ({first_face_normal.x:.4f}, {first_face_normal.y:.4f}, {first_face_normal.z:.4f})\n"
        )
    else:
        App.Console.PrintMessage(
            "Normal Vector: No face was selected (only objects/edges).\n"
        )

    App.Console.PrintMessage("---------------------------------\n")

    return new_box


# ===================
# === ENTRY POINT ===
# ===================
def main():
    selection_ex = Gui.Selection.getSelectionEx()
    # step_obj.ViewObject.Visibility = False
    # create bound box
    box = create_cube(selection_ex)
    Part.show(box)
    App.ActiveDocument.recompute()


if __name__ == "__main__":
    main()
