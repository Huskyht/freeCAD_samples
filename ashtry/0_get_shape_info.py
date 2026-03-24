# import FreeCAD as App
# import Part
# import math
# 
# # 1. Get the currently selected object (to use as a size reference)
# selection = Gui.Selection.getSelection()
# 
# if selection:
#     target_obj = selection[0]
#     
#     # 2. Get the dimensions (Bounding Box) of the selected object
#     bbox = target_obj.Shape.BoundBox
#     print(f"Created a box with size {bbox.XLength}x{bbox.YLength}x{bbox.ZLength}. ")
# 
#     # 3. Calculate dimensions: Round up to the nearest integer and add 10mm
#     # Example: 12.3mm -> 13.0mm + 10mm = 23.0mm
#     box_l = math.ceil(bbox.XLength) + 10
#     box_w = math.ceil(bbox.YLength) + 10
#     # box_h = math.ceil(bbox.ZLength) + 10
#     box_h = 100
#     
#     # 4. Set the fixed placement to (0, 0, -32)
#     # Using App.Vector(x, y, z) and an empty App.Rotation() for no rotation
#     fixed_pos = App.Vector( -box_l / 2, - box_w / 2, -32)
#     fixed_rot = App.Rotation()
#     fixed_placement = App.Placement(fixed_pos, fixed_rot)
#     
#     # 5. Create a new Box object in the document
#     doc = App.activeDocument()
#     new_box = doc.addObject("Part::Box", "FixedPosBox")
#     
#     # Set the calculated dimensions and fixed placement
#     new_box.Length = box_l
#     new_box.Width = box_w
#     new_box.Height = box_h
#     new_box.Placement = fixed_placement
#     
#     # Refresh the document to show the changes
#     doc.recompute()
#     print(f"Created a box with size {box_l}x{box_w}x{box_h} at position (0, 0, -32).")
# else:
#     print("Please select a reference object before running the macro.")




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
    z_dim = math.ceil(bbox.ZLength) + 10

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
