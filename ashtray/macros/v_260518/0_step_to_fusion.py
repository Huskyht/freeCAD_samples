import FreeCAD as App
import FreeCADGui as Gui
import Draft
import Part

# 1. Get the selection
selection = Gui.Selection.getSelection()
if not selection:
    print("Please select the imported STEP object.")
else:
    original_doc = App.ActiveDocument
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
        new_doc = App.newDocument(new_doc_name)

        # 6. Place the refined shape into the NEW document
        final_feature = new_doc.addObject("Part::Feature", "Step_Solid")
        final_feature.Shape = refined_shape

        new_doc.recompute()

        # 7. DELETE THE ORIGINAL MESSY DOCUMENT
        # This instantly wipes out the Revolve, Axis, and all temporary solids
        App.closeDocument(original_doc.Name)

        # Switch the view to the new document
        Gui.setActiveDocument(new_doc)
        Gui.SendMsgToActiveView("ViewFit")

        print(f"Success! Created {new_doc_name}. Original messy doc closed.")
