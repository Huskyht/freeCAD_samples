import FreeCAD as App
import FreeCADGui as Gui

# 1. Get selected object and sub-element (face)
selection = Gui.Selection.getSelectionEx()
if not selection:
    print("Please select a face.")
else:
    sel_ex = selection[0]
    obj = sel_ex.Object
    face = sel_ex.SubObjects[0]
    
    # 2. Get local normal and coordinates at the center of the face
    u_min, u_max, v_min, v_max = face.ParameterRange
    u_mid = (u_min + u_max) / 2
    v_mid = (v_min + v_max) / 2
    
    local_normal = face.normalAt(u_mid, v_mid)
    local_normal.normalize()
    local_pos = face.valueAt(u_mid, v_mid)
    
    # 3. Calculate and apply rotation to align with Z-axis (0,0,-1)
    target_dir = App.Vector(0, 0, -1)
    rot_diff = App.Rotation(local_normal, target_dir)
    
    # Update rotation (considering existing rotation)
    obj.Placement.Rotation = rot_diff.multiply(obj.Placement.Rotation)
    
    # 4. Calculate world coordinates of the face center after rotation
    # Recompute once to determine the position after rotation is applied
    App.ActiveDocument.recompute()
    world_pos = obj.Placement.multVec(local_pos)
    
    # 5. Offset the position so the face center aligns with origin (0,0,0)
    # Subtract the calculated world coordinates from the current Base position
    obj.Placement.Base.x -= world_pos.x
    obj.Placement.Base.y -= world_pos.y
    obj.Placement.Base.z -= world_pos.z
    
    App.ActiveDocument.recompute()
    print(f"Success: {obj.Label} has been aligned horizontally at the origin (0,0,0).")
