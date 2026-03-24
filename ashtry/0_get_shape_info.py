import FreeCAD as App
import FreeCADGui as Gui
import Part
# use for rounding up bbox
import math
# from dataclasses import dataclass

# @dataclass
# class die_bbox:
#     x: float
#     y: float
#     z: float


def get_geometry_info():
    # Get extended selection information
    selection_ex = Gui.Selection.getSelectionEx()
    
    if not selection_ex:
        App.Console.PrintMessage("Error: Please select at least one face or object.\n")
        return

    shapes = []
    first_face_normal = None

    for sel in selection_ex:
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

    x_dim = math.ceil(bbox.XLength) + 10
    y_dim = math.ceil(bbox.YLength) + 10
    z_dim = 100

    new_box = App.ActiveDocument.addObject("Part::Box", "new_box")

    fixed_pos = App.Vector( -x_dim / 2, - y_dim / 2, -32)
    fixed_rot = App.Rotation()
    fixed_placement = App.Placement(fixed_pos, fixed_rot)


    new_box.Length = x_dim
    new_box.Width = y_dim
    new_box.Height = z_dim
    new_box.Placement = fixed_placement

    App.ActiveDocument.recompute()

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
        App.Console.PrintMessage(f"  (x, y, z): ({first_face_normal.x:.4f}, {first_face_normal.y:.4f}, {first_face_normal.z:.4f})\n")
    else:
        App.Console.PrintMessage("Normal Vector: No face was selected (only objects/edges).\n")
        
    App.Console.PrintMessage("---------------------------------\n")

    # ---
    # --- Use bbox xyzLength for calculating die block
    # --- Use first_face_normal xyz for calculating die block vector
    # ---
    # !NOTE: rounding up bbox + 5mm 



    return (first_face_normal, bbox)

# Execute the function
get_geometry_info()
