import FreeCAD as App
import FreeCADGui as Gui
import Part


def align_model():
    selection = Gui.Selection.getSelectionEx()

    if not selection:
        print("Please select shapes.")
    else:
        obj = selection[0].Object

        subs = selection[0].SubObjects

        if len(subs) < 2:
            print("Select at least 1 face + 1 or more shapes.")
            raise

        # -------------------------
        # 1. Bake object to world
        # -------------------------
        shape = obj.Shape.copy()
        shape = shape.transformGeometry(obj.Placement.toMatrix())

        # -------------------------
        # 2. First = face for Z align
        # -------------------------
        face_z = subs[0]

        def get_center_and_normal(face):
            u_min, u_max, v_min, v_max = face.ParameterRange
            u_mid = (u_min + u_max) / 2
            v_mid = (v_min + v_max) / 2

            center = face.valueAt(u_mid, v_mid)
            normal = face.normalAt(u_mid, v_mid)
            normal.normalize()

            return center, normal

        center_z, normal_z = get_center_and_normal(face_z)

        # -------------------------
        # 3. Other shapes → bbox
        # -------------------------
        shapes_for_bbox = subs[1:]

        # combine them
        comp = Part.makeCompound(shapes_for_bbox)
        bbox = comp.BoundBox

        bbox_center = bbox.Center

        # -------------------------
        # 4. ROTATE (align normal → -Z)
        # -------------------------
        target = App.Vector(0, 0, -1)
        rot = App.Rotation(normal_z, target)

        shape = shape.transformGeometry(App.Placement(App.Vector(), rot).toMatrix())

        # rotate reference points too
        center_z = rot.multVec(center_z)
        bbox_center = rot.multVec(bbox_center)

        # -------------------------
        # 5. MOVE XY center → origin
        # -------------------------
        move_xy = App.Vector(-bbox_center.x, -bbox_center.y, 0)
        shape.translate(move_xy)

        center_z = center_z + move_xy

        # -------------------------
        # 6. MOVE Z → 0
        # -------------------------
        shape.translate(App.Vector(0, 0, -center_z.z))

        # -------------------------
        # 7. Show result
        # -------------------------
        result = App.ActiveDocument.addObject("Part::Feature", "Aligned")
        result.Shape = shape

        App.ActiveDocument.removeObject(obj.Name)
        App.ActiveDocument.recompute()

        # print("  Object aligned")


class AlignModelCmd:
    """This class defines the toolbar button and menu action for FreeCAD."""

    def GetResources(self):
        return {
            "Pixmap": "1_move_to_origin.png",
            "MenuText": "Align 3D model to origin",
            "ToolTip": "Select surface which lie on the lower die and center of xy plane surface in order",
        }

    def Activated(self):
        """This method runs automatically whenever you click the toolbar button."""
        App.Console.PrintMessage("  align model on xy plane...\n")
        try:
            align_model()
            App.Console.PrintMessage(" align model on xy plane\n")
        except Exception as e:
            App.Console.PrintError(f"Error executing align_model: {str(e)}\n")

    def IsActive(self):
        """Optional: Determines if the button is clickable.
        Returns True if a document is open, otherwise greys out the button."""
        return App.ActiveDocument is not None


# Register this script into FreeCAD's global command manager.
# The string 'create_cube' MUST exactly match the item you put into self.list inside InitGui.py
Gui.addCommand("align_model", AlignModelCmd())
