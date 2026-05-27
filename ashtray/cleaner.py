import FreeCAD as App
import Part
import math

def analyze_face_geometries(obj_name):
    obj = App.ActiveDocument.getObject(obj_name)
    if not obj or not hasattr(obj, "Shape"):
        print("有効な形状オブジェクトが見つかりません。")
        return

    shape = obj.Shape
    print(f"=== オブジェクト解析開始: {obj_name} ===")
    print(f"総面数 (Total Faces): {len(shape.Faces)}")
    
    for i, face in enumerate(shape.Faces):
        print(f"\n--- Face [{i}] ---")
        
        # 1. 幾何タイプの取得
        surf = face.Surface
        surf_type = surf.ShapeTypeAsString()
        print(f"  幾何タイプ (Surface Type): {surf_type}")
        print(f"  面積 (Area): {face.Area:.4f} mm2")
        
        # 2. 隣接する面の数を調査 (トポロジー接続)
        # どの面と繋がっているかは、隣り合うFaceを共有するEdgeから追跡可能
        adjacent_count = len(shape.ancestorsOfType(face, "Edge")) # 簡易カウント
        print(f"  境界エッジ数 (Edges): {len(face.Edges)}")
        
        # 3. 幾何タイプ別の詳細パラメータ解析
        if surf_type == "Plane":
            # 平面の法線ベクトル
            uv_center = face.ParameterRange
            u_mid = (uv_center[0] + uv_center[1]) / 2
            v_mid = (uv_center[2] + uv_center[3]) / 2
            normal = face.normalAt(u_mid, v_mid)
            print(f"  法線ベクトル (Normal): ({normal.x:.3f}, {normal.y:.3f}, {normal.z:.3f})")
            
        elif surf_type == "Cylinder":
            # 円筒面の半径と軸
            radius = surf.Radius
            axis = surf.Axis
            print(f"  円筒半径 (Radius): {radius:.4f} mm")
            print(f"  中心軸方向 (Axis): ({axis.x:.3f}, {axis.y:.3f}, {axis.z:.3f})")
            
        elif surf_type == "Toroid":
            # トーラス面（R部）の半径
            major_R = surf.MajorRadius
            minor_r = surf.MinorRadius
            print(f"  大半径 (Major R): {major_R:.4f} mm (回転中心までの距離)")
            print(f"  小半径 (Minor r): {minor_r:.4f} mm (断面のRサイズ)")
            
        elif surf_type == "Cone":
            # 円錐面（テーパー部）
            semi_angle = math.degrees(surf.SemiAngle)
            print(f"  円錐半角 (Semi-Angle): {semi_angle:.2f} 度")
            
        else:
            # BSpline などの自由曲面の場合、ガウス曲率をサンプルチェック
            uv = face.ParameterRange
            u_mid = (uv[0] + uv[1]) / 2
            v_mid = (uv[2] + uv[3]) / 2
            # OpenCASCADEの幾何プロパティから主曲率を取得可能
            try:
                # FreeCADのPart.Faceは直接曲率を返すメソッドがない場合があるため
                # ここでは非平面の種類として記録にとどめる
                print("  ※自由曲面または特殊幾何（ガウス曲率が0でない可能性大）")
            except:
                pass

# 使い方: FreeCAD上で対象のSTEPオブジェクト（例: 'Project_Shape'）を選択するか、名前を指定して実行
# analyze_face_geometries("対象のオブジェクト名")
