"""
拟阵剪枝 (Matroid Pruning) — κ-Gate 贪心最优独立集

将 EML 超边集构成拟阵 M = (E, ℐ):
  E = 超边集合
  ℐ = 不形成语义过确定回路的超边集合

核心公理 (Edmonds 1965; Rado 1957):
  (I1) ∅ ∈ ℐ
  (I2) 若 I ∈ ℐ 且 J ⊂ I，则 J ∈ ℐ (遗传性)
  (I3) 若 |I| < |J| 且 I, J in I_set，则 exists e in J minus I 使得 I∪{e} in I_set (增广性)

κ-Gate 剪枝对应: 按 ℐ(e) 降序贪心加边，若加入后引入回路则拒绝。

回路分型 (TOMAS 核心特色):
  - MUS-Circuit: 存在 e_a, e_b 标记 Asym≠0，允许互斥双存 (阴平阳秘)
  - Paradox-Circuit: 所有 Asym≡0，须 XOR 消解或死零拒绝

定理 3.2: 贪心得到的基 B 是最大权独立集，∑ℐ(B) 最大且 |B| = r(E)。
"""

import heapq
from typing import List, Tuple, Set, Dict, Optional
from collections import defaultdict
from .hyperedge import HypEdge, EMLVertex


class Matroid:
    """
    EML 拟阵 — 在超边集合上的独立集系统。
    独立集: 不包含语义过确定回路（含 MUS-Circuit 或 Paradox-Circuit）的超边子集。
    """

    def __init__(self, edges: List[HypEdge], vertices: List[EMLVertex] = None):
        """
        Args:
            edges: 超边列表 (E)
            vertices: 顶点列表 (V)，用于度类信息
        """
        self.edges = {e.eid: e for e in edges}
        self.vertices = vertices or []
        self._vertex_degrees = self._build_vertex_degrees(edges)

        # 缓存
        self._adjacency: Dict[int, Set[str]] = defaultdict(set)
        for e in edges:
            for n in e.nodes:
                self._adjacency[n].add(e.eid)

    @staticmethod
    def _build_vertex_degrees(edges: List[HypEdge]) -> Dict[int, int]:
        deg = defaultdict(int)
        for e in edges:
            for n in e.nodes:
                deg[n] += 1
        return dict(deg)

    def get_degree(self, vid: int) -> int:
        """获取顶点度"""
        return self._vertex_degrees.get(vid, 0)

    def find_base(self, dead_threshold: float = 0.15) -> List[HypEdge]:
        """
        拟阵贪心算法 — 找到最大权独立集基 B。

        算法: 按 ℐ(e) 降序排列超边，依次尝试加入；
        若加入不形成回路则保留，否则拒绝。

        Args:
            dead_threshold: 死零阈值 θ_dead，ℐ < θ_dead 的超边直接丢弃

        Returns:
            基 B (最大权独立集超边列表)
        """
        # 过滤死零边
        alive_edges = [e for e in self.edges.values() if e.is_alive(dead_threshold)]
        # 按 ℐ 降序排列
        alive_edges.sort(key=lambda e: e.i_val, reverse=True)

        base: List[HypEdge] = []
        used_vertices: Set[int] = set()

        for e in alive_edges:
            # 检测是否引入回路
            if self._would_create_circuit(e, base, used_vertices):
                continue  # 拒绝此边
            base.append(e)
            used_vertices.update(e.nodes)

        return base

    def _would_create_circuit(
        self, edge: HypEdge, current_set: List[HypEdge], used_vertices: Set[int]
    ) -> bool:
        """
        检测添加 edge 到 current_set 是否会形成回路。

        判定逻辑:
        1. Paradox-Circuit (Asym≡0): 所有节点已被覆盖 → 回路
        2. MUS-Circuit (Asym≠0): 允许双存，不形成回路

        对应推论 3.3 的 MUS-Circuit 分型。
        """
        if edge.is_mus_capable:
            # MUS-capable 边: 允许节点重复 (互斥稳态双存)
            return False

        # Boolean 边: 检查是否所有节点都已出现在 current_set 中
        for n in edge.nodes:
            if n not in used_vertices:
                return False  # 有新节点，不形成回路

        return True  # 所有节点已覆盖 → Boolean 回路

    def identify_circuits(self, dead_threshold: float = 0.15) -> Dict[str, List[List[HypEdge]]]:
        """
        识别并分类所有回路。

        Returns:
            {'mus_circuits': [...], 'paradox_circuits': [...]}
        """
        mus_circuits = []
        paradox_circuits = []

        edges_sorted = sorted(
            [e for e in self.edges.values() if e.is_alive(dead_threshold)],
            key=lambda e: e.i_val, reverse=True
        )

        # 使用 Union-Find 风格的回路检测
        # 对每个连通分量检测回路
        visited_eids = set()
        for e in edges_sorted:
            if e.eid in visited_eids:
                continue

            # BFS 收集此边的连通分量
            component_edges = []
            component_nodes = set()
            queue = [e.eid]
            while queue:
                eid = queue.pop(0)
                if eid in visited_eids:
                    continue
                visited_eids.add(eid)
                edge_obj = self.edges[eid]
                component_edges.append(edge_obj)
                for n in edge_obj.nodes:
                    component_nodes.add(n)
                    for neighbor_eid in self._adjacency.get(n, set()):
                        if neighbor_eid not in visited_eids:
                            queue.append(neighbor_eid)

            # 在连通分量中检测回路
            # 回路 = 边数 >= 节点数 - 连通分量数 (对超图，回路判定更复杂)
            # 简化: 在连通分量中贪心找基，被拒绝的边构成回路
            sub_matroid = Matroid(component_edges, self.vertices)
            # 用简化版找基
            used_nodes = set()
            base_edges = []
            circuit_edges = []
            for ce in sorted(component_edges, key=lambda x: x.i_val, reverse=True):
                if ce.is_mus_capable:
                    base_edges.append(ce)
                    used_nodes.update(ce.nodes)
                else:
                    all_used = all(n in used_nodes for n in ce.nodes)
                    if all_used:
                        circuit_edges.append(ce)
                    else:
                        base_edges.append(ce)
                        used_nodes.update(ce.nodes)

            # 分类回路
            for ce in circuit_edges:
                circuit = [ce]
                if ce.is_mus_capable:
                    mus_circuits.append(circuit)
                else:
                    paradox_circuits.append(circuit)

        return {
            'mus_circuits': mus_circuits,
            'paradox_circuits': paradox_circuits,
        }

    def get_rank(self) -> int:
        """拟阵秩 r(E) = |B| = 最大独立集大小"""
        base = self.find_base()
        return len(base)

    def get_total_i(self, base: List[HypEdge] = None) -> float:
        """计算独立集的总 ℐ 值"""
        if base is None:
            base = self.find_base()
        return sum(e.i_val for e in base)


def matroid_prune(
    edges: List[HypEdge],
    vertices: List[EMLVertex] = None,
    dead_threshold: float = 0.15,
    verbose: bool = False,
) -> Tuple[List[HypEdge], Dict]:
    """
    拟阵贪心剪枝 — κ-Gate 的最优独立集实现。

    这是 EML 瘦身工具箱的第一层剪枝：
    按 ℐ(e) 降序贪心选择独立超边，保留最大 ∑ℐ 的基 B。

    Args:
        edges: 输入超边列表
        vertices: 顶点列表 (可选)
        dead_threshold: 死零阈值
        verbose: 是否输出调试信息

    Returns:
        (pruned_edges, stats) — 剪枝后的超边集合 + 统计信息
    """
    m = Matroid(edges, vertices)

    # 识别回路
    circuits = m.identify_circuits(dead_threshold)

    # 找基
    base = m.find_base(dead_threshold)

    total_i = sum(e.i_val for e in base)
    total_i_original = sum(e.i_val for e in edges if e.is_alive(dead_threshold))

    stats = {
        'original_count': len(edges),
        'alive_count': sum(1 for e in edges if e.is_alive(dead_threshold)),
        'pruned_count': len(base),
        'removed_count': len(edges) - len(base),
        'compression_ratio': len(base) / max(len(edges), 1),
        'total_i_before': total_i_original,
        'total_i_after': total_i,
        'i_retention': total_i / max(total_i_original, 1e-9),
        'rank': m.get_rank(),
        'mus_circuits': len(circuits['mus_circuits']),
        'paradox_circuits': len(circuits['paradox_circuits']),
    }

    if verbose:
        print(f"[拟阵剪枝] {stats['original_count']}→{stats['pruned_count']} "
              f"(压缩 {stats['compression_ratio']:.1%}, "
              f"ℐ保留 {stats['i_retention']:.1%}, "
              f"MUS回路:{stats['mus_circuits']}, 悖论回路:{stats['paradox_circuits']})")

    return base, stats
