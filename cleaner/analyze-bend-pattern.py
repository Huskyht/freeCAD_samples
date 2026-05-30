from numpy import unsignedinteger
import FreeCAD
import FreeCADGui as Gui
import Part

from math import degrees, log10, pi, radians, sin, tan
from statistics import StatisticsError, mode
# import networkx as nx
# try:
#     import networkx as nx
# except ImportError:
#     App.Console.PrintUserError(
#         "The NetworkX Python package could not be imported. "
#         "Consider checking that it is installed, "
#         "or reinstalling the SheetMetal workbench using the addon manager\n"
#     )
# try:
#     test_graph = nx.Graph
# except AttributeError:
#     App.Console.PrintUserError(
#         "The NetworkX Python package is version "
#         + str(nx.__version__)
#         + "\n"
#         + "Consider checking that it is at least version 3.4.2\n "
#     )

# ╭──────────────────────────────────────────────────────────╮
# │ the standard tolerance value (usually 1 x 10^{-7} )      │
# │ used by the OpenCASCADE (OCCT) kernel for                │
# │ geometry approximation algorithms.                       │
# ╰──────────────────────────────────────────────────────────╯
eps = FreeCAD.Base.Precision.approximation()


def IsParallel(v1, v2):
    return abs(abs(v1.normalize().dot(v2.normalize())) - 1.0) < eps


class EstimateThickness:
    """This class provides helper functions to determine the sheet
    thickness of a solid-modelled sheet metal part.
    """

    @staticmethod
    def from_normal_edges(shp: Part.Shape, selected_face: Part.Face) -> float:
        """Get the modal length of all straight edges that share
        a vertex with the selected root face, and are oriented in line
        with the root faces normal direction. Edges that meet these
        criteria usually correspond to the sheet thickness.
        """
        num_places = abs(int(log10(eps)))
        root_face = selected_face
        normal = root_face.Surface.Axis
        # Checking membership of an edge in a shape directly won't work.
        # We must compare via hashCodes instead.
        root_face_edge_hashes = [e.hashCode() for e in root_face.Edges]
        length_values = []
        for v in root_face.Vertexes:
            for e in shp.ancestorsOfType(v, Part.Edge):
                if (
                    e.hashCode() not in root_face_edge_hashes
                    and e.Curve.TypeId == "Part::GeomLine"
                    and IsParallel(e.Curve.Direction, normal)
                ):
                    length_values.append(round(e.Length, num_places))
        try:
            thickness_value = mode(length_values)
            return thickness_value
        except StatisticsError:
            return 0.0

    @staticmethod
    def from_face(shape: Part.Shape, selected_face: Part.Face) -> float:
        ref_face = selected_face
        # Find all planar faces that are parallel to the chosen face.
        candidates = [
            f
            for f in shape.Faces
            if f.hashCode() != ref_face.hashCode()
            and f.Surface.TypeId == "Part::GeomPlane"
            and IsParallel(ref_face.Surface.Axis, f.Surface.Axis)
        ]
        if not candidates:
            return 0.0
        opposite_face = sorted(candidates, key=lambda x: abs(x.Area - ref_face.Area))[0]
        return abs(
            opposite_face.valueAt(0, 0).distanceToPlane(
                ref_face.Surface.Position, ref_face.Surface.Axis
            )
        )

    @staticmethod
    def using_best_method(shape: Part.Shape, selected_face: Part.Face) -> float:
        thickness = EstimateThickness.from_normal_edges(shape, selected_face)
        if not thickness:
            thickness = EstimateThickness.from_face(shape, selected_face)
        if not thickness:
            errmsg = "Couldn't estimate thickness for shape!"
            raise RuntimeError(errmsg)
        return thickness


def paint_face_by_each_surface_type(obj):
    COLOR_RED = "#CC241D"
    COLOR_BLUE = "#5E81AC"
    COLOR_GREEN = "#A3BE8C"
    COLOR_YELLOW = "#FABD2F"
    COLOR_GRAY = "#D8DEE9"
    COLOR_PURPLE = "#B48EAD"
    COLOR_ORANGE = "#FE8019"
    # COLOR_WHITE = "#F9F5D7"

    hex_color = COLOR_GRAY

    faces = obj.Shape.Faces
    if not faces:
        return None

    colored_faces = []
    for i, face in enumerate(faces):
        # get surface type
        surf = face.Surface
        surf_type = surf.__class__.__name__
        print(f"  Surface Type : {surf_type}")
        print(f"\n--- Face [{i}] ---")
        # display surface type's property
        if surf_type == "Plane":
            hex_color = COLOR_BLUE

        elif surf_type == "Cylinder":
            hex_color = COLOR_YELLOW

        elif surf_type == "Toroid":
            hex_color = COLOR_GREEN

        elif surf_type == "Cone":
            hex_color = COLOR_PURPLE

        elif surf_type == "Sphere":
            hex_color = COLOR_ORANGE

        elif surf_type == "BSplineSurface":
            hex_color = COLOR_RED

        else:
            hex_color = COLOR_GRAY

        r = int(hex_color[1:3], 16) / 255
        g = int(hex_color[3:5], 16) / 255
        b = int(hex_color[5:7], 16) / 255
        colored_faces.append((r, g, b))

    obj.ViewObject.DiffuseColor = colored_faces
    return obj


def get_real_shape_object(obj):
    """
    Recursively search actual shape object.
    Supports:
    - PartDesign::Body
    - App::Part
    - nested containers
    """

    # PartDesign Body
    if obj.TypeId == "PartDesign::Body":
        if hasattr(obj, "Tip") and obj.Tip:
            return get_real_shape_object(obj.Tip)

    # App::Part container
    if obj.TypeId == "App::Part":
        for child in obj.Group:
            result = get_real_shape_object(child)
            if result:
                return result

    # Actual shape object
    if hasattr(obj, "Shape"):
        try:
            if len(obj.Shape.Faces) > 0:
                return obj
        except Exception:
            pass

    return None


class sheet_metal_graph:
    @staticmethod
    def create_graph(obj):
        # graph = nx.Graph()
        do_nothing = None


def main():
    FreeCAD.Console.PrintMessage("analyzing object ... \n")
    sel_ex = Gui.Selection.getSelectionEx()[0]
    if not sel_ex:
        FreeCAD.Console.PrintError("No object selected. \n")
        return

    sel_obj = sel_ex.Object
    sel_face = sel_ex.SubObjects[0]
    print(f"sel_obj : {sel_obj}")
    print(f"sel_face : {sel_face}")

    print(f"Label : {sel_obj.Label}")
    obj = get_real_shape_object(sel_obj)
    if not obj or not hasattr(obj, "Shape"):
        FreeCAD.Console.PrintError("No valid shape object found. \n")
        return

    # shape = obj.Shape
    print(f"TypeID : {obj.TypeId}")
    print(f"total Faces: {len(obj.Shape.Faces)}")
    print(f"TypeID : {obj.TypeId}")

    obj = paint_face_by_each_surface_type(obj)

    thickness = EstimateThickness.using_best_method(obj.Shape, sel_face)
    print(f"thickness : {thickness}")

    FreeCAD.ActiveDocument.recompute()
    Gui.updateGui()


if __name__ == "__main__":
    main()
