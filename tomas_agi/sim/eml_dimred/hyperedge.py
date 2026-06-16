"""
EML 超边数据模型

基于 TOMAS EML 超图五元组定义:
  H = (V, E, ℐ, κ, Asym)

- V: 概念/实体/状态节点
- E subset of 2^V minus empty: n 元语义超边
- ℐ: 信息存在度，满足公理 A1 (∑ℐ = Const, 守恒)
- κ: 谱折叠深度 (κ=7 太一全活, κ→0 Boolean 结合代数极限)
- Asym: 八元数量值，标记超边对是否允许 MUS (互斥稳态/阴平阳秘)

与 EML 二进制格式的映射:
  - 每个 Vertex (80B): vertex_id + octonion[8] + delta(=ℐ)
  - 每个 Edge (32B): src + dst + weight + delta_weight + assoc_flag(=Asym)
"""

from dataclasses import dataclass, field
from typing import Tuple, List, Dict, Set, Optional
import struct
import json
from pathlib import Path


@dataclass
class HypEdge:
    """EML 超边 — 可连接任意数量节点的 n 元语义关系"""
    nodes: Tuple[int, ...]          # 节点 ID 元组
    eid: str                        # 超边唯一标识
    i_val: float                    # ℐ(e) — 信息存在度 [0, 1]
    asym: float = 0.0               # Asym — 非结合残联标记; 0=Boolean, ≠0=MUS-capable
    weight: float = 1.0             # 关联权重 (对应 EML 边 weight)
    delta_weight: float = 0.0       # delta_weight (对应 EML 边 delta_weight)
    source: Optional[int] = None    # 有向边的源节点 (None=无向)
    target: Optional[int] = None    # 有向边的目标节点

    def __post_init__(self):
        """确保 i_val 在 [0, 1] 范围内"""
        self.i_val = max(0.0, min(1.0, self.i_val))

    @property
    def arity(self) -> int:
        """超边的元数 (arity)"""
        return len(self.nodes)

    @property
    def is_mus_capable(self) -> bool:
        """是否允许 MUS (互斥稳态双存)"""
        return abs(self.asym) > 1e-9

    @property
    def is_boolean(self) -> bool:
        """是否为 Boolean 边 (无 MUS 能力)"""
        return abs(self.asym) < 1e-9

    def is_alive(self, dead_threshold: float = 0.15) -> bool:
        """是否高于死零阈值 (theta_dead)"""
        return self.i_val >= dead_threshold

    def __hash__(self):
        return hash(self.eid)

    def __eq__(self, other):
        return isinstance(other, HypEdge) and self.eid == other.eid


@dataclass
class EMLVertex:
    """EML 顶点 — 概念/实体/状态节点"""
    vid: int                        # 顶点 ID
    concept: str = ""               # 概念名称 (从 .concepts.json 恢复)
    phi: List[float] = field(default_factory=lambda: [0.0]*8)  # 八元数 phi 场
    i_val: float = 0.0              # ℐ — 信息存在度 (对应 delta 字段)
    degree_class: int = 0           # 度类 C_i (按 ℐ 分层)

    @property
    def i_bin(self) -> int:
        """ℐ 分层 bin:
        Bin1: (0.9, 1.0] — 核心定律/根本关系
        Bin2: (0.7, 0.9] — 强语境关系
        Bin3: (0.4, 0.7] — 常识关联
        Bin4: (0.1, 0.4] — 弱联想
        Bin5: [0, 0.1]  — 噪声/幻觉候选
        """
        if self.i_val > 0.9:
            return 1
        elif self.i_val > 0.7:
            return 2
        elif self.i_val > 0.4:
            return 3
        elif self.i_val > 0.1:
            return 4
        else:
            return 5


def load_eml_graph(eml_path: str, concepts_json_path: str = None) -> Tuple[List[EMLVertex], List[HypEdge], Dict]:
    """
    从 EML 二进制文件加载图数据，转换为 HypEdge 和 EMLVertex 格式。

    EML 二进制格式 (小端序):
      Header (72B): magic, version, num_vertices, num_edges, laplacian_alpha, graph_delta, timestamp, reserved
      Vertices (80B each): vertex_id, octonion[8], delta
      Edges (32B each): src, dst, weight, delta_weight, assoc_flag, padding

    Args:
        eml_path: .eml 文件路径
        concepts_json_path: .concepts.json 文件路径 (可选，用于恢复概念名称)

    Returns:
        (vertices, edges, metadata)
    """
    with open(eml_path, 'rb') as f:
        data = f.read()

    # 解析 Header (72 bytes, little-endian)
    magic, version, num_v, num_e = struct.unpack_from('<IIII', data, 0)
    if magic != 0x454D4C47:  # 'EMLG'
        raise ValueError(f"Invalid EML magic: 0x{magic:08X}, expected 0x454D4C47")

    laplacian_alpha, graph_delta = struct.unpack_from('<dd', data, 16)
    timestamp = struct.unpack_from('<Q', data, 32)[0]

    metadata = {
        'magic': f'0x{magic:08X}',
        'version': f'0x{version:08X}',
        'num_vertices': num_v,
        'num_edges': num_e,
        'laplacian_alpha': laplacian_alpha,
        'graph_delta': graph_delta,
        'timestamp': timestamp,
    }

    # 加载概念名称
    concept_names = {}
    if concepts_json_path and Path(concepts_json_path).exists():
        with open(concepts_json_path, 'r', encoding='utf-8') as f:
            cdata = json.load(f)
        for c in cdata.get('concepts', []):
            concept_names[c.get('id', -1)] = c.get('concept', '')

    # 解析 Vertices
    vertices = []
    offset = 72
    for i in range(num_v):
        vid, _pad = struct.unpack_from('<ii', data, offset)
        phi = list(struct.unpack_from('<dddddddd', data, offset + 8))
        delta = struct.unpack_from('<d', data, offset + 72)[0]

        v = EMLVertex(
            vid=vid,
            concept=concept_names.get(vid, f'v{vid}'),
            phi=phi,
            i_val=delta,
        )
        vertices.append(v)
        offset += 80

    # 解析 Edges
    edges = []
    for i in range(num_e):
        src, dst = struct.unpack_from('<ii', data, offset)
        weight, delta_weight = struct.unpack_from('<dd', data, offset + 8)
        assoc_flag, _pad = struct.unpack_from('<ii', data, offset + 24)

        # 转换为 HypEdge (二元边 → 超边)
        he = HypEdge(
            nodes=(src, dst),
            eid=f'e_{i}',
            i_val=abs(weight),  # 用 weight 的绝对值作为 ℐ 的近似
            asym=float(assoc_flag),  # assoc_flag 对应 Asym
            weight=weight,
            delta_weight=delta_weight,
            source=src,
            target=dst,
        )
        edges.append(he)
        offset += 32

    return vertices, edges, metadata


def build_degree_map(edges: List[HypEdge]) -> Dict[int, int]:
    """构建节点度映射"""
    deg = {}
    for e in edges:
        for n in e.nodes:
            deg[n] = deg.get(n, 0) + 1
    return deg


def compute_i_stats(edges: List[HypEdge]) -> Dict:
    """计算 ℐ 值统计信息"""
    i_vals = [e.i_val for e in edges]
    if not i_vals:
        return {'count': 0, 'sum': 0, 'mean': 0, 'min': 0, 'max': 0}

    sorted_vals = sorted(i_vals)
    n = len(sorted_vals)
    return {
        'count': n,
        'sum': sum(sorted_vals),
        'mean': sum(sorted_vals) / n,
        'min': sorted_vals[0],
        'max': sorted_vals[-1],
        'q25': sorted_vals[n // 4],
        'median': sorted_vals[n // 2],
        'q75': sorted_vals[3 * n // 4],
    }
