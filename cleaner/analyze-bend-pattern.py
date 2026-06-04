from networkx import graph
from numpy import unsignedinteger
import FreeCAD
import FreeCADGui as Gui
import Part

from math import degrees, log10, pi, radians, sin, tan
from statistics import StatisticsError, mode

import time
import csv
import datetime
import platform
import platform


try:
    import networkx as nx
except ImportError:
    FreeCAD.Console.printError("networkx libraly doesn't exist. Trying to install ...")

    import subprocess
    import sys
    import os

    bin_dir = os.path.dirname(sys.executable)
    python_exe = os.path.join(bin_dir, "python.exe")

    subprocess.check_call([python_exe, "-m", "pip", "install", "networkx"])
    FreeCAD.Console.PrintMessage(
        "Depending libraly is installed. Please restart FreeCAD \n"
    )
    sys.exit(1)

# ╭──────────────────────────────────────────────────────────╮
# │ the standard tolerance value (usually 1 x 10^{-7} )      │
# │ used by the OpenCASCADE (OCCT) kernel for                │
# │ geometry approximation algorithms.                       │
# ╰──────────────────────────────────────────────────────────╯
eps = FreeCAD.Base.Precision.approximation()


def is_parallel(v1, v2):
    return abs(abs(v1.normalize().dot(v2.normalize())) - 1.0) < eps


def is_normal(v1, v2):
    return abs(v1.dot(v2)) < eps


def get_normal(face: Part.Face):
    normal = face.Surface.Axis

    if face.Orientation == "Reversed":
        normal = -normal

    if abs(normal.x) <= eps:
        normal.x = 0.0
    if abs(normal.y) <= eps:
        normal.y = 0.0
    if abs(normal.z) <= eps:
        normal.z = 0.0

    return normal


def write_csv(file_path, title, data):
    try:
        with open(file_path, mode="w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow([title])
            writer.writerows(data)
        print(f"csv is created! : {file_path}")
    except Exception as e:
        print(f"An error occured while writing csv ... {e}")


# copy from SheetMetal Workbench's SheetMetalNewUnfolder.py
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
        normal = get_normal(root_face)
        # Checking membership of an edge in a shape directly won't work.
        # We must compare via hashCodes instead.
        root_face_edge_hashes = [e.hashCode() for e in root_face.Edges]
        length_values = []
        for v in root_face.Vertexes:
            for e in shp.ancestorsOfType(v, Part.Edge):
                if (
                    e.hashCode() not in root_face_edge_hashes
                    and e.Curve.TypeId == "Part::GeomLine"
                    and is_parallel(e.Curve.Direction, normal)
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
            and is_parallel(ref_face.Surface.Axis, f.Surface.Axis)
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


# copy from SheetMetal Workbench's SheetMetalTools.py
class TangentFaces:
    """This class provides functions to check if brep faces are tangent
    to each other. each compare_x_x function accepts two surfaces of a
    particular type, and returns a boolean value indicating tangency.
    The compare function accepts two faces and selects the correct
    compare_x_x function automatically.
    """

    @staticmethod
    def compare_plane_plane(p1: Part.Plane, p2: Part.Plane) -> bool:
        # Returns True if the two planes have similar normals and
        # the base point of the first plane is (nearly) coincident with
        # the second plane.
        return (
            is_parallel(p1.Axis, p2.Axis)
            and p1.Position.distanceToPlane(p2.Position, p2.Axis) < eps
        )

    @staticmethod
    def compare_plane_cylinder(p: Part.Plane, c: Part.Cylinder) -> bool:
        # Returns True if the cylinder is tangent to the plane
        # (there is 'line contact' between the surfaces).
        return (
            is_normal(p.Axis, c.Axis)
            and abs(abs(c.Center.distanceToPlane(p.Position, p.Axis)) - c.Radius) < eps
        )

    @staticmethod
    def compare_cylinder_cylinder(c1: Part.Cylinder, c2: Part.Cylinder) -> bool:
        # Returns True if the two cylinders have parallel axis' and
        # those axis' are separated by a distance of
        # approximately r1 + r2.
        return (
            is_parallel(c1.Axis, c2.Axis)
            and (
                abs(
                    c1.Center.distanceToLine(c2.Center, c2.Axis)
                    - (c1.Radius + c2.Radius)
                )
                < eps
            )
            # alternative condition: 2 coaxial cylinders with the same radius
            or (
                abs(c1.Center.distanceToLine(c2.Center, c2.Axis) < eps)
                and is_parallel(c1.Axis, c2.Axis)
                and (abs(c1.Radius - c2.Radius) < eps)
            )
        )

    @staticmethod
    def compare_plane_torus(p: Part.Plane, t: Part.Toroid) -> bool:
        # Imagine a donut sitting flat on a table.
        # That's our tangency condition for a plane and a toroid.
        return (
            is_parallel(p.Axis, t.Axis)
            and abs(abs(t.Center.distanceToPlane(p.Position, p.Axis)) - t.MinorRadius)
            < eps
        )

    @staticmethod
    def compare_cylinder_torus(c: Part.Cylinder, t: Part.Toroid) -> bool:
        # If the surfaces are tangent, either we have:
        # - a donut inside a circular container, with no gap at the
        #     container perimeter;
        # - a donut shoved onto a shaft with no wiggle room;
        # - a cylinder with an axis tangent to the central circle of
        #     the donut.
        return (
            is_parallel(c.Axis, t.Axis)
            and c.Center.distanceToLine(t.Center, t.Axis) < eps
            and (
                abs(c.Radius - abs(t.MajorRadius - t.MinorRadius)) < eps
                or abs(c.Radius - abs(t.MajorRadius + t.MinorRadius)) < eps
            )
        ) or (
            is_normal(c.Axis, t.Axis)
            and abs(abs(t.Center.distanceToLine(c.Center, c.Axis)) - t.MajorRadius)
            < eps
            and abs(c.Radius - t.MinorRadius) < eps
        )

    @staticmethod
    def compare_sphere_sphere(s1: Part.Sphere, s2: Part.Sphere) -> bool:
        # Only segments of identical spheres are tangent to each other.
        return (
            s1.Center.distanceToPoint(s2.Center) < eps
            and abs(s1.Radius - s2.Radius) < eps
        )

    @staticmethod
    def compare_plane_sphere(p: Part.Plane, s: Part.Sphere) -> bool:
        # This function will probably never actually return True,
        # because a plane and a sphere only ever share a vertex if
        # they are tangent to each other.
        return abs(abs(s.Center.distanceToPlane(p.Position, p.Axis)) - s.Radius) < eps

    @staticmethod
    def compare_torus_sphere(t: Part.Toroid, s: Part.Sphere) -> bool:
        return (
            s.Center.distanceToPoint(t.Center) < eps
            and (
                abs(t.MajorRadius - t.MinorRadius - s.Radius) < eps
                or abs(t.MajorRadius + t.MinorRadius - s.Radius) < eps
            )
        ) or (
            abs(s.Radius - t.MinorRadius) < eps
            and is_normal(t.Axis, s.Center - t.Center)
            and abs(t.Center.distanceToPoint(s.Center) - t.MajorRadius) < eps
        )

    @staticmethod
    def compare_torus_torus(t1: Part.Toroid, t2: Part.Toroid) -> bool:
        return (
            t1.Center.distanceToLine(t2.Center, t2.Axis) < eps
            and is_parallel(t1.Axis, t2.Axis)
            and abs(
                t1.Center.distanceToPoint(t2.Center) ** 2
                + (t1.MajorRadius - t2.MajorRadius) ** 2
                - (t1.MinorRadius + t2.MinorRadius) ** 2
            )
            < eps
        )

    @staticmethod
    def compare_cylinder_sphere(c: Part.Cylinder, s: Part.Sphere) -> bool:
        # The sphere must be sized/positioned like a ball sliding down
        # a tube with no wiggle room.
        return (
            (
                s.Center.distanceToLine(c.Center, c.Axis) < eps
                and abs(s.Radius - c.Radius) < eps
            )
            # Point contact case.
            or (
                abs(s.Center.distanceToLine(c.Center, c.Axis) - s.Radius - c.Radius)
                < eps
            )
        )

    @staticmethod
    def compare_plane_cone(p: Part.Plane, cn: Part.Cone) -> bool:
        return abs(cn.Apex.distanceToPlane(p.Position, p.Axis)) < eps and (
            abs(cn.Axis.getAngle(p.Axis) - abs(cn.SemiAngle) - pi / 2) < eps
            or abs(cn.Axis.getAngle(p.Axis) + abs(cn.SemiAngle) - pi / 2) < eps
        )

    @staticmethod
    def compare_cone_cone(cn1: Part.Cone, cn2: Part.Cone) -> bool:
        return (
            cn1.Apex.distanceToPoint(cn2.Apex) < eps
            and abs(cn1.Axis.getAngle(cn2.Axis) - cn1.SemiAngle - cn2.SemiAngle) < eps
        )

    @staticmethod
    def compare_sphere_cone(s: Part.Sphere, cn: Part.Cone) -> bool:
        return (
            s.Center.distanceToLine(cn.Apex, cn.Axis) < eps
            and (cn.Apex.distanceToPoint(s.Center) * sin(cn.SemiAngle) - s.Radius) < eps
        )

    @staticmethod
    def compare_cylinder_cone(c: Part.Cylinder, cn: Part.Cone) -> bool:
        return abs(cn.Apex.distanceToLine(c.Center, c.Axis) - c.Radius) < eps and (
            abs(c.Axis.getAngle(cn.Axis) - cn.SemiAngle) < eps
            or abs(pi - c.Axis.getAngle(cn.Axis) - abs(cn.SemiAngle)) < eps
        )

    @staticmethod
    def compare_torus_cone(t: Part.Toroid, cn: Part.Cone) -> bool:
        return (
            is_parallel(t.Axis, cn.Axis)
            and cn.Apex.distanceToLine(t.Center, t.Axis) < eps
            and (
                abs(
                    t.MajorRadius / tan(cn.SemiAngle)
                    - t.MinorRadius / sin(cn.SemiAngle)
                    - cn.Apex.distanceToPoint(t.Center)
                )
                < eps
                or abs(
                    t.MajorRadius / tan(cn.SemiAngle)
                    + t.MinorRadius / sin(cn.SemiAngle)
                    - cn.Apex.distanceToPoint(t.Center)
                )
                < eps
            )
        )

    @staticmethod
    def compare_surfaces_via_sample(s1, s2, shared_edge: Part.Edge) -> bool:
        # compare surface tangency by sampling at the centerpoint of a linear edge
        if shared_edge.Curve.TypeId != "Part::GeomLine":
            return False
        test_point = shared_edge.CenterOfMass
        value_1 = s1.projectPoint(test_point, "LowerDistanceParameters")
        value_2 = s2.projectPoint(test_point, "LowerDistanceParameters")
        normal_1 = s1.normal(*value_1)
        normal_2 = s2.normal(*value_2)
        return is_parallel(normal_1, normal_2)

    @staticmethod
    def compare_plane_extrusion(
        p: Part.Plane, ex: Part.SurfaceOfExtrusion, shared_edge: Part.Edge
    ) -> bool:
        return TangentFaces.compare_surfaces_via_sample(p, ex, shared_edge)

    @staticmethod
    def compare_cylinder_extrusion(
        c: Part.Cylinder, ex: Part.SurfaceOfExtrusion, shared_edge: Part.Edge
    ) -> bool:
        return TangentFaces.compare_surfaces_via_sample(c, ex, shared_edge)

    @staticmethod
    def compare_torus_extrusion(t: Part.Toroid, ex: Part.SurfaceOfExtrusion) -> bool:
        # a toroid and surface of revolution are only ever tangent at individial points, not across a line.
        # Threefore, just return false
        return False

    @staticmethod
    def compare_sphere_extrusion(s: Part.Sphere, ex: Part.SurfaceOfExtrusion) -> bool:
        # these 2 surface types are never tangent across a line
        return False

    @staticmethod
    def compare_extrusion_extrusion(
        ex1: Part.SurfaceOfExtrusion,
        ex2: Part.SurfaceOfExtrusion,
        shared_edge: Part.Edge,
    ) -> bool:
        return TangentFaces.compare_surfaces_via_sample(ex1, ex2, shared_edge)

    @staticmethod
    def compare_extrusion_cone(
        ex: Part.SurfaceOfExtrusion, cn: Part.Cone, shared_edge: Part.Edge
    ) -> bool:
        return TangentFaces.compare_surfaces_via_sample(ex, cn, shared_edge)

    @staticmethod
    def compare(
        face1: Part.Face, face2: Part.Face, shared_edge: Part.Edge
    ) -> tuple[bool, bool]:
        # determine tangency of two faces, checking as many surface geometry
        # combinations as possible
        s1 = face1.Surface
        s2 = face2.Surface
        type1 = s1.TypeId
        type2 = s2.TypeId
        order = [
            "Part::GeomPlane",
            "Part::GeomCylinder",
            "Part::GeomToroid",
            "Part::GeomSphere",
            "Part::GeomSurfaceOfExtrusion",
            "Part::GeomCone",
        ]
        needs_swap = (
            type1 in order
            and type2 in order
            and order.index(type1) > order.index(type2)
        )
        if needs_swap:
            s2, s1 = s1, s2
        cls = TangentFaces
        res = False
        if s1.TypeId == "Part::GeomPlane":
            # Plane.
            if s2.TypeId == "Part::GeomPlane":
                res = cls.compare_plane_plane(s1, s2)
            elif s2.TypeId == "Part::GeomCylinder":
                res = cls.compare_plane_cylinder(s1, s2)
            elif s2.TypeId == "Part::GeomToroid":
                res = cls.compare_plane_torus(s1, s2)
            elif s2.TypeId == "Part::GeomSphere":
                res = cls.compare_plane_sphere(s1, s2)
            elif s2.TypeId == "Part::GeomSurfaceOfExtrusion":
                res = cls.compare_plane_extrusion(s1, s2, shared_edge)
            elif s2.TypeId == "Part::GeomCone":
                res = cls.compare_plane_cone(s1, s2)
        elif s1.TypeId == "Part::GeomCylinder":
            # Cylinder.
            if s2.TypeId == "Part::GeomCylinder":
                res = cls.compare_cylinder_cylinder(s1, s2)
            elif s2.TypeId == "Part::GeomToroid":
                res = cls.compare_cylinder_torus(s1, s2)
            elif s2.TypeId == "Part::GeomSphere":
                res = cls.compare_cylinder_sphere(s1, s2)
            elif s2.TypeId == "Part::GeomSurfaceOfExtrusion":
                res = cls.compare_cylinder_extrusion(s1, s2, shared_edge)
            elif s2.TypeId == "Part::GeomCone":
                res = cls.compare_cylinder_cone(s1, s2)
        elif s1.TypeId == "Part::GeomToroid":
            # Torus.
            if s2.TypeId == "Part::GeomToroid":
                res = cls.compare_torus_torus(s1, s2)
            elif s2.TypeId == "Part::GeomSphere":
                res = cls.compare_torus_sphere(s1, s2)
            elif s2.TypeId == "Part::GeomSurfaceOfExtrusion":
                res = cls.compare_torus_extrusion(s1, s2)
            elif s2.TypeId == "Part::GeomCone":
                res = cls.compare_torus_cone(s1, s2)
        elif s1.TypeId == "Part::GeomSphere":
            # Sphere.
            if s2.TypeId == "Part::GeomSphere":
                res = cls.compare_sphere_sphere(s1, s2)
            elif s2.TypeId == "Part::GeomSurfaceOfExtrusion":
                res = cls.compare_sphere_extrusion(s1, s2)
            elif s2.TypeId == "Part::GeomCone":
                res = cls.compare_sphere_cone(s1, s2)
        elif s1.TypeId == "Part::GeomSurfaceOfExtrusion":
            # Extrusion.
            if s2.TypeId == "Part::GeomSurfaceOfExtrusion":
                res = cls.compare_extrusion_extrusion(s1, s2, shared_edge)
            elif s2.TypeId == "Part::GeomCone":
                res = cls.compare_extrusion_cone(s1, s2, shared_edge)
        elif s1.TypeId == "Part::GeomCone":
            # Cone.
            if s2.TypeId == "Part::GeomCone":
                res = cls.compare_cone_cone(s1, s2)
        # emit a warning if there are bends across unsupported geometry types
        well_supported_types = {"Part::GeomPlane", "Part::GeomCylinder"}
        warn = res and not set([type1, type2]) <= well_supported_types
        return res, warn


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
        # print(f"\n--- Face [{i}] ---")
        # print(f"  Surface Type : {surf_type}")
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
    if obj.TypeId == "Part::Feature":
        return obj.Shape

    # Actual shape object
    if hasattr(obj, "Shape"):
        try:
            if len(obj.Shape.Faces) > 0:
                return obj
        except Exception:
            pass

    return None


# copy from SheetMetal Workbench's SheetMetalNewUnfolder.py
class sheet_metal_graph:
    class bend_property:
        bend_direction: int  # 1: same direction as base face normal. -1: inverted direction, 0: parallel faces
        edge_idx: int
        is_prallel_bend_line: bool
        connetion_pattern: Part.Face
        angle: float

    @staticmethod
    def build_graph_of_tangent_faces(shp: Part.Shape, root: int) -> nx.Graph:
        # Created a simple undirected graph object.
        graph_of_shape_faces = nx.Graph()
        # Track faces by their indices, because the underlying pointers
        # to faces may get changed around while building the graph.
        face_hashes = [f.hashCode() for f in shp.Faces]
        index_lookup = {h: i for i, h in enumerate(face_hashes)}
        # Get pairs of faces that share the same edge.
        candidates = [
            (i, shp.ancestorsOfType(e, Part.Face)) for i, e in enumerate(shp.Edges)
        ]
        # Filter to remove seams on cylinders or other faces that wrap back
        # onto themselves other than self-adjacent faces, edges should
        # always have 2 face ancestors this assumption is probably only
        # valid for watertight solids.
        saw_warning = False
        for edge_index, faces in filter(lambda c: len(c[1]) == 2, candidates):
            face_a, face_b = faces
            if not (
                (
                    isinstance(face_a.Surface, Part.Plane)
                    and isinstance(face_b.Surface, Part.Cylinder)
                )
                or (
                    isinstance(face_a.Surface, Part.Plane)
                    and isinstance(face_b.Surface, Part.Cylinder)
                )
            ):
                # print("skipped")
                # print(f"type(face_a.Surface) : {face_a.Surface}")
                # print(f"type(face_b.Surface) : {face_b.Surface}")
                pass
            else:
                shared_edge = shp.Edges[edge_index]
                tangent_result, possible_geom_warning = TangentFaces.compare(
                    face_a, face_b, shared_edge
                )
                saw_warning |= possible_geom_warning
                if tangent_result:
                    graph_of_shape_faces.add_edge(
                        index_lookup[face_a.hashCode()],
                        index_lookup[face_b.hashCode()],
                        # Store indexes in the label attr for debugging.
                        label=edge_index,
                    )
        # emit a warning if the shape has bends across unsupported face types
        if saw_warning:
            msg = (
                "This shape appears to have bends across surfaces that are not planes or cylinders."
                " Unfolding it may produce unexpected results.\n"
            )
            FreeCAD.Console.PrintWarning(msg)
        print(f"nodes numbder : {graph_of_shape_faces.number_of_nodes()}")
        # return graph_of_shape_faces.copy()
        for c in nx.connected_components(graph_of_shape_faces):
            if root in c:
                return graph_of_shape_faces.subgraph(c).copy()
        single_face_graph = nx.Graph()
        single_face_graph.add_node(root)
        return single_face_graph

    @staticmethod
    def build_bfs_tree(graph, root):
        return nx.bfs_tree(graph, source=root)


class bend_analyzer:
    @staticmethod
    def get_planes_and_cylinders(bfs_tree: nx.DiGraph, root_idx: int, shp):
        planes = []
        cylinders = []
        for n in bfs_tree.nodes():
            if bfs_tree.out_degree(n) == 0:
                path = nx.shortest_path(bfs_tree, source=root_idx, target=n)
                p = []
                c = []
                for idx in path:
                    if isinstance(shp.Faces[idx].Surface, Part.Plane):
                        p.append(idx)
                    elif isinstance(shp.Faces[idx].Surface, Part.Cylinder):
                        para_bend_line = False
                        if len(c) >= 1:
                            if is_parallel(
                                shp.Faces[c[-1][1]].Surface.Axis,
                                shp.Faces[idx].Surface.Axis,
                            ):
                                para_bend_line = True
                            else:
                                para_bend_line = False

                        c.append((idx, para_bend_line))

                planes.append(p)
                cylinders.append(c)

        return planes, cylinders

    @staticmethod
    def get_normal_directions(shp: Part.Shape, faces_idx):
        return [get_normal(shp.Faces[idx]) for idx in faces_idx]

    @staticmethod
    def up_or_down(shp: Part.Shape, base_idx, cyl_idx):
        base = shp.Faces[base_idx]
        cyl = shp.Faces[cyl_idx]

        base_normal = get_normal(base)

        uv = cyl.ParameterRange
        u_mid = (uv[0] + uv[1]) / 2
        v_mid = (uv[2] + uv[3]) / 2
        cyl_normal = cyl.normalAt(u_mid, v_mid)

        dot_val = base_normal.dot(cyl_normal)

        if dot_val > eps:
            return 1
        elif dot_val < -eps:
            return -1
        else:
            return 0

    # This function return tupple value like (face_idx, is_bend_line_parallel) which is not included root face index.
    @staticmethod
    def detect_bend_directions(shp: Part.Shape, planes_idx, cyl_list):
        first_cyl_idx = cyl_list[0][0]

        print(f"planes_idx: {planes_idx}")
        if len(planes_idx) <= 1:
            # only base
            return [(None, None)]
        elif len(planes_idx) == 2:
            # base face and a bend face
            up_or_down = bend_analyzer.up_or_down(shp, planes_idx[0], first_cyl_idx)
            return [(up_or_down, cyl_list[0][1])]

        up_or_down = bend_analyzer.up_or_down(shp, planes_idx[0], first_cyl_idx)
        bend_sign = []
        bend_sign.append((up_or_down, cyl_list[0][1]))
        plane_0 = shp.Faces[planes_idx[0]]
        plane_1 = shp.Faces[planes_idx[1]]
        p0_normal_base = get_normal(plane_0)
        p1_normal_base = get_normal(plane_1)
        base_vec = p0_normal_base.cross(p1_normal_base)

        for i in range(1, len(planes_idx) - 1):
            print(f"i: {i}")
            p0_normal_cur = get_normal(shp.Faces[planes_idx[i]])
            p1_normal_cur = get_normal(shp.Faces[planes_idx[i + 1]])

            cur_vec = p0_normal_cur.cross(p1_normal_cur)

            dot_val = base_vec.dot(cur_vec)

            if dot_val > eps:
                bend_sign.append((up_or_down, cyl_list[i][1]))
            elif dot_val < -eps:
                bend_sign.append((-up_or_down, cyl_list[i][1]))
            else:
                bend_sign.append((0, cyl_list[i][1]))

        return bend_sign


def main():
    start_time = time.perf_counter()
    FreeCAD.Console.PrintMessage("analyzing object ... \n")
    sel_ex = Gui.Selection.getSelectionEx()[0]
    if not sel_ex:
        FreeCAD.Console.PrintError("No object selected. \n")
        return

    sel_obj = sel_ex.Object
    shp = get_real_shape_object(sel_obj)
    print(f"shp: {shp}")
    sel_face = sel_ex.SubObjects[0]
    root_face_name = sel_ex.SubElementNames[0]
    root_idx = int(root_face_name.replace("Face", "")) - 1

    # obj = get_real_shape_object(sel_obj)
    # if not obj or not hasattr(obj, "Shape"):
    #     FreeCAD.Console.PrintError("No valid shape object found. \n")
    #     return

    # shape = obj.Shape

    thickness = EstimateThickness.using_best_method(shp, sel_face)
    print(f"thickness : {thickness}")

    bend_graph = sheet_metal_graph.build_graph_of_tangent_faces(shp, root_idx)
    bfs_tree = sheet_metal_graph.build_bfs_tree(bend_graph, root_idx)
    print(f"bfs_tree : {bfs_tree.number_of_nodes()}")

    connected_planes, cylinder_hinges = bend_analyzer.get_planes_and_cylinders(
        bfs_tree, root_idx, shp
    )
    print(f"cylinder_hinges: {cylinder_hinges}")
    # neighbors = list(bend_graph.neighbors(root_idx))
    #
    r = []
    for i, f_list in enumerate(connected_planes):
        # first_cyl = cylinder_hinges[i][0][0]
        cyl_list = cylinder_hinges[i]

        r.append(bend_analyzer.detect_bend_directions(shp, f_list, cyl_list))

    print(f"bend_direction : {r}")

    face_all_dirs = []
    # for face_list in connected_planes:
    #     face_all_dirs.append(bend_analyzer.get_normal_directions(shp, face_list))
    # print(f"face_all_dirs : {face_all_dirs}")

    sel_obj = paint_face_by_each_surface_type(sel_obj)
    FreeCAD.ActiveDocument.recompute()
    Gui.updateGui()
    end_time = time.perf_counter()
    elapsed_time = end_time - start_time
    print(f"execution time : {elapsed_time}")
    FreeCAD.Console.PrintMessage(" analyzing object\n")

    parent_name = "default_name"
    try:
        parent_name = sel_obj.getParentGeoFeatureGroup().Name
    except:
        parent_name = sel_obj.Label
    print(f"parent_name: {parent_name}")
    # r.insert(0, parent_name)

    if r:
        now = datetime.datetime.now()
        timestamp = now.strftime("%Y%m%d_%H%M%S")
        file_name = f"{parent_name}_{timestamp}.csv"

        os_name = platform.system()
        if os_name == "Windows":
            dir_path = "C:\\Users\\XU74644hsky\\codes\\FreeCAD\\surface-analyzer\\"
            file_path = dir_path + file_name
        else:
            dir_path = "/home/husky/huskyprojects/freeCAD_samples/cleaner/csv/"
            file_path = dir_path + file_name
        write_csv(file_path, parent_name, r)


if __name__ == "__main__":
    main()
