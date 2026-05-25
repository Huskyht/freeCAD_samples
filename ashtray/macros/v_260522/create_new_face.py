import FreeCAD as App
import FreeCADGui as Gui
import Part


# ╔══════════════════════════════════════════════════════════╗
# ║                       ENTRY POINT                        ║
# ╚══════════════════════════════════════════════════════════╝
def main():
    App.Console.PrintMessage("running create new face... \n")
    selection_ex = Gui.Selection.getSelectionEx()

    edges = get_selected_edges(selection_ex)
    if not edges:
        App.Console.PrintError(
            "Error: 2 or more continuous Edges should be selected in the 3D View.\n"
        )
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
    App.Console.PrintMessage("complete create new face. \n")


def get_selected_edges(selection_ex):
    edges = []
    for sel in selection_ex:
        for sub_name in sel.SubElementNames:
            element = sel.Object.Shape.getElement(sub_name)
            if element.ShapeType == "Edge":
                edges.append(element)
    if edges:
        if len(edges) <= 1:
            return None
        return edges
    else:
        return None


# this function just check if the edges is connected correctly.
# NOTE: it does not return closed wire.
def process_selected_edges(edges):
    # part.sortEdges() returns the edges organized in a continuous head-to-tail path chain (end-to-end).
    # if Edges has gap which is greater than 10e-7, part.sortEdges() returns tupple which express clusters.
    sorted_edges = Part.sortEdges(edges)

    # if isinstance(sorted_edges, tuple):
    if len(sorted_edges) >= 2:
        cluster_count = len(sorted_edges)
        App.Console.PrintError(
            f"Error: The selected edges have a gap and do not connect!\n"
            f"Found {cluster_count} disconnected edge groups.\n"
            f"Please check your geometry alignment.\n"
        )
        return None
    return sorted_edges[0]


def add_missing_edge(sorted_edges):

    v_start = (
        sorted_edges[0].Vertexes[0].Point if len(sorted_edges[0].Vertexes) > 0 else None
    )
    v_end = (
        sorted_edges[-1].Vertexes[-1].Point
        if len(sorted_edges[-1].Vertexes) > 0
        else None
    )

    # Ensure we didn't pick up matching vertices in between
    if (
        sorted_edges[0].Vertexes[-1].Point == sorted_edges[1].Vertexes[0].Point
        or sorted_edges[0].Vertexes[-1].Point == sorted_edges[1].Vertexes[-1].Point
    ):
        pass
    else:
        # Handle reverse vertex indexing if sorted_edges inverted them
        v_start = sorted_edges[0].Vertexes[-1].Point
        App.Console.PrintMessage("v_start is inverted \n")

    if (
        sorted_edges[-1].Vertexes[0].Point == sorted_edges[-2].Vertexes[0].Point
        or sorted_edges[-1].Vertexes[0].Point == sorted_edges[-2].Vertexes[-1].Point
    ):
        pass
    else:
        v_end = sorted_edges[-1].Vertexes[0].Point
        App.Console.PrintMessage("v_end is inverted \n")

    # early return if edges is already closed
    if v_start == v_end:
        App.Console.PrintMessage(
            "Shape is already closed. Skipping bridge generation.\n"
        )
        return sorted_edges
    if len(sorted_edges) <= 1:
        App.Console.PrintError("Please select continous 2 or more edges. \n")
        return None
    elif len(sorted_edges) == 2:
        v_exist = (
            sorted_edges[0].Vertexes[-1].Point
            if len(sorted_edges[0].Vertexes) > 0
            else None
        )
        if v_exist == v_start:
            v_exist = sorted_edges[0].Vertexes[0].Point
            App.Console.PrintMessage("v_exist is inverted \n")
        if v_end == None or v_start == None or v_exist == None:
            return None

        vec_start_end = v_end - v_start
        vec_exist_point = v_exist - v_start
        missing_point = v_start - vec_exist_point + vec_start_end
        sorted_edges.append(
            Part.makeLine(
                App.Vector(v_end),
                App.Vector(missing_point),
            )
        )
        sorted_edges.append(
            Part.makeLine(App.Vector(missing_point), App.Vector(v_start))
        )

    elif len(sorted_edges) >= 3:
        try:
            # Generate the 4th missing straight edge to close the U-shape
            bridge_edge = Part.makeLine(v_start, v_end)
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
