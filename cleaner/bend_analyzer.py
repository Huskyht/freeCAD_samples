from dataclasses import dataclass, field
from typing import List, Dict, Any
import rustworkx as rusx
import FreeCAD
import FreeCADGui
import Part


# --- 局所フィーチャの定義 ---


@dataclass
class FormedFeature:
    """絞り・プレス成形などのノード付帯フィーチャ"""

    feature_type: str  # 'emboss' (絞り), 'burring' (バーリング), 'louver' など
    depth: float  # 成形深さ
    bounding_box: tuple
    # 構成する実際のPart::Faceインデックス群を持たせる
    associated_face_ids: List[int] = field(default_factory=list)


@dataclass
class RibFeature:
    """三角リブなどのエッジ付帯フィーチャ"""

    rib_type: str  # 'triangular_rib'
    height: float  # リブの高さ
    width: float  # リブの幅


# --- グラフのノード・エッジ定義 ---


@dataclass
class FlangeNode:
    """ノード：展開のベースとなる平面（Plane）"""

    node_id: int
    face_id: int
    area: float
    normal: tuple
    # ★絞り形状や穴などの局所要素はすべてここに集約する
    formed_features: List[FormedFeature] = field(default_factory=list)
    holes_count: int = 0


@dataclass
class FaceNodeData:
    face_id: int
    area: float
    surface_type: str  # 例: 'Part::GeomPlane', 'Part::GeomCylinder'
    center_of_mass: tuple  # (x, y, z)
    # 必要に応じて元オブジェクトへの参照を残すことも可能（シリアライズ非対応）
    # raw_face: Optional[Part.Face] = None


@dataclass
class BendEdge:
    """エッジ：曲げ部（Cylinder）"""

    edge_id: int
    face_id: int  # 元となったCylinder面のID
    radius: float  # 曲げR
    angle: float  # 曲げ角度
    # ★三角リブなどの補強要素はエッジの属性として持たせる
    ribs: List[RibFeature] = field(default_factory=list)


def build_sheet_metal_graph(shape: Part.Shape) -> rusx.PyGraph:
    graph = rusx.PyGraph()
    faces = shape.Faces
    edges = shape.Edges

    face_hashes = [f.hashCode() for f in shp.Faces]
    index_lookup = {h: i for i, h in enumerate(face_hashes)}
    # Get pairs of faces that share the same edge.
    candidates = [
        (i, shape.ancestorsOfType(e, Part.Face)) for i, e in enumerate(shape.Edges)
    ]

    saw_warning = False
    for edge_index, faces in filter(lambda c: len(c[1]) == 2, candidates):
        shared_edge = shape.Edges[edge_index]

    # 1. ノードの追加
    face_to_node_idx = {}
    # class FaceNodeData:
    #     face_id: int
    #     area: float
    #     surface_type: str  # 例: 'Plane', 'Cylinder'
    #     center_of_mass: tuple  # (x, y, z)
    for idx, face in enumerate(faces):
        node_data = FaceNodeData(
            face_id=idx,
            area=face.Area,
            surface_type=face.Surface.TypeId,
            # surface_type=str(face.Surface),
            center_of_mass=(
                face.CenterOfMass.x,
                face.CenterOfMass.y,
                face.CenterOfMass.z,
            ),
        )
        node_idx = graph.add_node(node_data)
        face_to_node_idx[idx] = node_idx

    for edge_idx, edge in enumerate(edges):
        edge_data = Edge

    # 2. エッジ（共通のEdge）による接合関係の探索と追加
    # （※実際の幾何処理では TopoDS / Shape の共有Edge判定ロジックを挟みます）
    # 例としてエッジ接続を行うイメージ:
    # node_a, node_b 間にエッジを追加
    # edge_data = EdgeData(edge_id=e_idx, length=edge.Length, bend_angle=calculated_angle)
    # graph.add_edge(node_a, node_b, edge_data)

    # 3. 隣接数（Degree）などの動的な特徴量は計算後に設定可能
    for node_idx in graph.node_indices():
        node_data: FaceNodeData = graph[node_idx]
        # rustworkx の degree() メソッドで隣接面の個数を簡単に取得可能
        degree = graph.degree(node_idx)
        # 必要ならプロパティに追加更新（または別管理）

    return graph


def extract_face_node_info(face: Part.Face, face_id: int):
    # face.Wires のうち、1つ目がOuterWire（外形）、2つ目以降がInnerWires（穴）
    all_wires = face.Wires
    outer_wire = face.OuterWire

    inner_wires = [w for w in all_wires if not w.isPartner(outer_wire)]

    holes_data = []
    for hole_wire in inner_wires:
        # Wireから円半径や位置などのパラメータを抽出
        holes_data.append(
            {
                "is_closed": hole_wire.isClosed(),
                "edges_count": len(hole_wire.Edges),
                # 必要に応じて円孔（Circle）判定やバウンディングボックス座標を取得
            }
        )

    return {
        "face_id": face_id,
        "area": face.Area,
        "has_holes": len(holes_data) > 0,
        "holes": holes_data,  # ★ここで抜き穴の情報がNodeに保持される
    }


def main():
    sel_ex = FreeCADGui.Selection.getSelectionEx()[0]
    if not sel_ex:
        FreeCAD.Console.PrintError("No object selected. \n")
        return

    sel_obj = sel_ex.Object
    if sel_obj is None:
        FreeCAD.Console.PrintError("No object detected.")
        return

    shp = sel_obj.Shape
    print(f"shp: {shp}")
    sel_face = sel_ex.SubObjects[0]
    root_face_name = sel_ex.SubElementNames[0]
    # root_idx = int(root_face_name.replace("Face", "")) - 1

    brep_graph = build_sheet_metal_graph(shp)
    print(f"nodes: {brep_graph.nodes()} \n")
    print(f"edges: {brep_graph.edges()} \n")


if __name__ == "__main__":
    main()
