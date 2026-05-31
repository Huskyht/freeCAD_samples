import FreeCAD as App
import FreeCADGui as Gui
import Part
import math
import csv
import datetime
import platform

COLOR_RED = "#CC241D"
COLOR_BLUE = "#5E81AC"
COLOR_GREEN = "#A3BE8C"
COLOR_YELLOW = "#FABD2F"
COLOR_GRAY = "#D8DEE9"
COLOR_PURPLE = "#B48EAD"
COLOR_ORANGE = "#FE8019"
COLOR_WHITE = "#F9F5D7"


def write_csv(file_path, data):
    try:
        with open(file_path, mode="w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerows(data)
        print(f"csv is created! : {file_path}")
    except Exception as e:
        print(f"An error occured while writing csv ... {e}")


def analyze_face_geometries(obj):
    csv_contents = []
    if not obj or not hasattr(obj, "Shape"):
        print("Shape was not found.")
        return

    shape = obj.Shape
    print(f"=== analyzing ... : {obj.Name} ===")
    print(f"total Faces: {len(shape.Faces)}")
    print(f"TypeID : {obj.TypeId}")
    # print(f"PropertiesList : {obj.ViewObject.PropertiesList}")
    csv_contents.append(["object name", obj.Name])
    csv_contents.append(["total faces", len(shape.Faces)])
    csv_contents.append(["============================="])
    csv_contents.append(
        [
            "surface_type",
            "area",
            "center_x",
            "center_y",
            "center_z",
            "note1",
            "note2",
            "note3",
        ]
    )

    colored_face = []

    for i, face in enumerate(shape.Faces):
        print(f"\n--- Face [{i}] ---")
        hex_color = COLOR_GRAY

        # 1. get surface type
        surf = face.Surface
        surf_type = surf.__class__.__name__
        area = face.Area
        center = face.CenterOfMass
        print(f"  Surface Type : {surf_type}")
        print(f"  Area : {face.Area:.4f} mm2")

        # 2. count topology conection from edge
        # adjacent_count = len(shape.ancestorsOfType(face, Part.Edge))
        print(f"  Edges : {len(face.Edges)}")

        # 3. display surface type's property
        if surf_type == "Plane":
            uv_center = face.ParameterRange
            u_mid = (uv_center[0] + uv_center[1]) / 2
            v_mid = (uv_center[2] + uv_center[3]) / 2
            normal = face.normalAt(u_mid, v_mid)
            print(f"  Normal : ({normal.x:.3f}, {normal.y:.3f}, {normal.z:.3f})")
            csv_contents.append(
                [
                    surf_type,
                    area,
                    center.x,
                    center.y,
                    center.z,
                    normal.x,
                    normal.y,
                    normal.z,
                ]
            )
            hex_color = COLOR_BLUE

        elif surf_type == "Cylinder":
            radius = surf.Radius
            axies = surf.Axis
            print(f"  Radius : {radius:.4f} mm")
            print(f"  Axis : ({axies.x:.3f}, {axies.y:.3f}, {axies.z:.3f})")
            csv_contents.append(
                [surf_type, area, center.x, center.y, center.z, radius, axies]
            )
            hex_color = COLOR_YELLOW

        elif surf_type == "Toroid":
            major_R = surf.MajorRadius
            minor_r = surf.MinorRadius
            print(f"  Major R : {major_R:.4f} mm (distance from rotation axis)")
            print(f"  Minor r : {minor_r:.4f} mm (R size)")
            csv_contents.append(
                [surf_type, area, center.x, center.y, center.z, major_R, minor_r]
            )
            hex_color = COLOR_GREEN

        elif surf_type == "Cone":
            semi_angle = math.degrees(surf.SemiAngle)
            print(f"  Semi-Angle : {semi_angle:.2f} deg")
            csv_contents.append(
                [surf_type, area, center.x, center.y, center.z, semi_angle]
            )
            hex_color = COLOR_PURPLE

        elif surf_type == "Sphere":
            uv = face.ParameterRange
            u_mid = (uv[0] + uv[1]) / 2
            v_mid = (uv[2] + uv[3]) / 2
            normal = face.normalAt(u_mid, v_mid)
            print("complex shape")
            csv_contents.append(
                [
                    surf_type,
                    area,
                    center.x,
                    center.y,
                    center.z,
                    normal.x,
                    normal.y,
                    normal.z,
                ]
            )
            hex_color = COLOR_ORANGE
        elif surf_type == "BSplineSurface":
            uv = face.ParameterRange
            u_mid = (uv[0] + uv[1]) / 2
            v_mid = (uv[2] + uv[3]) / 2
            normal = face.normalAt(u_mid, v_mid)
            print("complex shape")
            csv_contents.append(
                [
                    surf_type,
                    area,
                    center.x,
                    center.y,
                    center.z,
                    normal.x,
                    normal.y,
                    normal.z,
                ]
            )
            hex_color = COLOR_RED
        else:
            uv = face.ParameterRange
            u_mid = (uv[0] + uv[1]) / 2
            v_mid = (uv[2] + uv[3]) / 2
            normal = face.normalAt(u_mid, v_mid)
            print("complex shape")
            csv_contents.append(
                [
                    surf_type,
                    area,
                    center.x,
                    center.y,
                    center.z,
                    normal.x,
                    normal.y,
                    normal.z,
                ]
            )
            hex_color = COLOR_WHITE

        r = int(hex_color[1:3], 16) / 255.0
        g = int(hex_color[3:5], 16) / 255.0
        b = int(hex_color[5:7], 16) / 255.0
        colored_face.append((r, g, b))

    obj.ViewObject.DiffuseColor = colored_face

    return csv_contents


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


def main():
    App.Console.PrintMessage("analizing object ... \n")
    sel_ex = Gui.Selection.getSelectionEx()
    if not sel_ex:
        App.Console.PrintError("No object selected. \n")
        return

    sel_obj = sel_ex[0].Object
    print(f"Label : {sel_obj.Label}")
    obj = get_real_shape_object(sel_obj)
    if not obj:
        App.Console.PrintError("No valid shape object found. \n")
        return

    print(f"TypeID : {obj.TypeId}")

    contents = analyze_face_geometries(obj)
    if contents:
        now = datetime.datetime.now()
        timestamp = now.strftime("%Y%m%d_%H%M%S")
        file_name = f"{obj.Label}_{timestamp}.csv"

        os_name = platform.system()
        if os_name == "Windows":
            dir_path = r"C:\\Users\\XU74644\\hsky\\codes\\FreeCAD\\surface-analyzer\\"
            file_path = dir_path + file_name
        else:
            dir_path = "/home/husky/huskyprojects/freeCAD_samples/cleaner/"
            file_path = dir_path + file_name

        write_csv(file_path, contents)

    App.ActiveDocument.recompute()
    Gui.updateGui()


if __name__ == "__main__":
    main()
