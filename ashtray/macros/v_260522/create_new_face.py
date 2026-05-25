import FreeCAD as App
import FreeCADGui as Gui
import Part


# ╔══════════════════════════════════════════════════════════╗
# ║                       ENTRY POINT                        ║
# ╚══════════════════════════════════════════════════════════╝
def main():
    selection_ex = Gui.Selection.getSelectionEx()
    App.Console.PrintMessage(f"selected num : {len(selection_ex)} \n")

    edges = get_selected_edges(selection_ex)
    if not edges:
        App.Console.PrintError("Error: No Edges were selected in the 3D View.\n")
        return
    App.Console.PrintMessage(f"sub element detected. : {edges} \n")

    sorted_edges = process_selected_edges(edges)
    if not sorted_edges:
        return
    App.Console.PrintMessage(f"sorted_edges: {sorted_edges} \n")

    closed_edges = add_missing_edge(sorted_edges)
    App.Console.PrintMessage(f"closed_edges: {closed_edges} \n")
    wire = create_wire(closed_edges)
    face = create_face(wire)
    Part.show(face, "NewFace")
    App.ActiveDocument.recompute()


def get_selected_edges(selection_ex):
    edges = []
    for sel in selection_ex:
        for sub_name in sel.SubElementNames:
            element = sel.Object.Shape.getElement(sub_name)
            if element.ShapeType == "Edge":
                edges.append(element)
    if edges:
        return edges
    else:
        return None


# this function just check if the edges is connected correctly.
# NOTE: it does not return closed wire.
def process_selected_edges(edges):
    # part.sortEdges() returns the edges organized in a continuous head-to-tail path chain (end-to-end).
    # if Edges has gap which is greater than 10e-7, part.sortEdges() returns tupple which express clusters.
    sorted_edges = Part.sortEdges(edges)
    if isinstance(sorted_edges, tuple):
        cluster_count = len(sorted_edges)
        App.Console.PrintError(
            f"Error: The selected edges have a gap and do not connect!\n"
            f"Found {cluster_count} disconnected edge groups.\n"
            f"Please check your geometry alignment.\n"
        )
        return None
    return sorted_edges[0]


def add_missing_edge(sorted_edges):
    App.Console.PrintMessage("running add_missing_edge... \n")

    v_start = sorted_edges[0].Vertexes[0] if len(sorted_edges[0].Vertexes) > 0 else None
    v_end = (
        sorted_edges[-1].Vertexes[-1] if len(sorted_edges[-1].Vertexes) > 0 else None
    )
    # early return if edges is already closed
    if v_start.isSame(v_end):
        App.Console.PrintMessage(
            "Shape is already closed. Skipping bridge generation.\n"
        )
        return sorted_edges
    if len(sorted_edges) <= 1:
        App.Console.PrintError("Please select continous 2 or more edges. \n")
        raise
    elif len(sorted_edges) == 2:
        v_exist = (
            sorted_edges[0].Vertexes[-1] if len(sorted_edges[0].Vertexes) > 0 else None
        )
        vec_start_end = v_end.Point - v_start.Point
        vec_exist_point = v_exist.Point - v_start.Point
        missing_point = (
            v_start.Point + vec_exist_point - vec_start_end - vec_exist_point
        )
        sorted_edges.append(
            Part.makeLine(
                App.Vector(sorted_edges[-1].Vertexes[-1].Point),
                App.Vector(missing_point),
            )
        )
        sorted_edges.append(
            Part.makeLine(
                App.Vector(missing_point), App.Vector(sorted_edges[0].Vertexes[0].Point)
            )
        )

    elif len(sorted_edges) >= 3:
        try:
            # Ensure we didn't pick up matching vertices in between
            if sorted_edges[0].Vertexes[-1].isSame(
                sorted_edges[1].Vertexes[0]
            ) or sorted_edges[0].Vertexes[-1].isSame(sorted_edges[1].Vertexes[-1]):
                pass
            else:
                # Handle reverse vertex indexing if sortsorted_edges inverted them
                v_start = sorted_edges[0].Vertexes[-1]

            if sorted_edges[-1].Vertexes[0].isSame(
                sorted_edges[-2].Vertexes[0]
            ) or sorted_edges[-1].Vertexes[0].isSame(sorted_edges[-2].Vertexes[-1]):
                pass
            else:
                v_end = sorted_edges[-1].Vertexes[0]

            # 4. Generate the 4th missing straight edge to close the U-shape
            bridge_edge = Part.makeLine(v_start.Point, v_end.Point)
            sorted_edges.append(bridge_edge)

        except Exception as e:
            print(f"Geometry error: {str(e)}")

    return sorted_edges


def create_wire(closed_edges):
    return Part.Wire(closed_edges)


def create_face(wire):
    return Part.makeFace(wire, "Part::FaceMakerBullseye")


if __name__ == "__main__":
    main()
