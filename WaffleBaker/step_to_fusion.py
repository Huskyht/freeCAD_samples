import FreeCAD
import FreeCADGui as Gui
import Draft


def convert_model():
    # 1. Get the selection
    selection = Gui.Selection.getSelection()
    if not selection:
        print("Please select the imported STEP object.")
    else:
        original_doc = FreeCAD.ActiveDocument
        original_obj = selection[0]
        obj_name = original_obj.Name

        print(f"Processing {obj_name}...")

        # 2. Downgrade to get the raw solids
        # We don't care about the return list because we will find them by Shape
        Draft.downgrade(original_obj, delete=True)

        # 3. Collect all valid solids currently in the messy document
        solids = [
            o
            for o in original_doc.Objects
            if hasattr(o, "Shape") and o.Shape.Volume > 0.0001
        ]

        if not solids:
            print("No solids found to unify.")
        else:
            # 4. Perform Fusion and Refine IN MEMORY (No new doc objects yet)
            shapes_only = [s.Shape for s in solids]
            if len(shapes_only) > 1:
                final_shape = shapes_only[0].fuse(shapes_only[1:])
            else:
                final_shape = shapes_only[0]

            # Refine the shape to remove extra edges
            refined_shape = final_shape.removeSplitter()

            # 5. CREATE THE NEW CLEAN DOCUMENT
            new_doc_name = obj_name + "_Cleaned"
            new_doc = FreeCAD.newDocument(new_doc_name)

            # 6. Place the refined shape into the NEW document
            final_feature = new_doc.addObject("Part::Feature", "Step_Solid")
            final_feature.Shape = refined_shape

            new_doc.recompute()

            # 7. DELETE THE ORIGINAL MESSY DOCUMENT
            # This instantly wipes out the Revolve, Axis, and all temporary solids
            FreeCAD.closeDocument(original_doc.Name)

            # Switch the view to the new document
            Gui.setActiveDocument(new_doc)
            Gui.SendMsgToActiveView("ViewFit")

            print(f"Success! Created {new_doc_name}. Original messy doc closed.")


class StepToFusionCmd:
    """This class defines the toolbar button and menu action for FreeCAD."""

    def GetResources(self):
        return {
            "Pixmap": "2_create_cube.png",
            "MenuText": "step to fusion",
            "ToolTip": "Turn 3D model into Solid model.",
        }

    # ╔══════════════════════════════════════════════════════════╗
    # ║                       ENTRY POINT                        ║
    # ╚══════════════════════════════════════════════════════════╝
    def Activated(self):
        """This function turn imported model to easy-to-use Solid model and open in New document."""
        FreeCAD.Console.PrintMessage("  converting 3D model into Solid model...\n")
        try:
            convert_model()

        except Exception as e:
            FreeCAD.Console.PrintError(f"Error executing step_to_fusion: {str(e)}\n")

    def IsActive(self):
        """Optional: Determines if the button is clickable.
        Returns True if a document is open, otherwise greys out the button."""
        return FreeCAD.ActiveDocument is not None


# Register this script into FreeCAD's global command manager.
# The string 'create_cube' MUST exactly match the item you put into self.list inside InitGui.py
Gui.addCommand("step_to_fusion", StepToFusionCmd())
