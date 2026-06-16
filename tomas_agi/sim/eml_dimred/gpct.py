"""
GPCT 边界层分解 (Generalized Prandtl-Cook Theorem)

将流体力学中 Prandtl 边界层思想推广到计算领域:
  CNF SAT 按变量耦合度 ρᵢ 划分:
    BL_ε (边界层): top-k 高 ρ 变量，k 为 FPT 参数
    OR (外区): 其余变量，固定 BL_ε 赋值后退化为 2-SAT/单元传播

定理 5.2 (GPCT — EML-SAT 边界层降解):
  若 k = |BL_ε| 有界，则:
    1. 枚举 2ᵏ 种 BL_ε 赋值
    2. 每种赋值下，外区子句变为单元/二元 → 多项式时间求解
    3. 总复杂度 O(2ᵏ · poly(n))，为 FPT

与 TOMAS 的映射:
  - 变量 = 超边是否被选入独立集
  - 子句 = 语义兼容性约束
  - ρᵢ = 节点的加权关系数 (度 × ℐ 加权)
"""

import math
import heapq
from typing import List, Tuple, Dict, Set, Optional
from collections import defaultdict
from .hyperedge import HypEdge, EMLVertex


class GpctDecomposer:
    """
    GPCT 边界层分解器。

    对 EML 超图执行分层降解:
      1. 计算节点耦合度 ρᵢ
      2. 识别边界层 BL_ε (top-k 高 ρ 节点)
      3. 外区 OR = V minus BL_epsilon
      4. 分层求解: 枚举 BL_ε → 外区单元传播
    """

    def __init__(
        self,
        edges: List[HypEdge],
        vertices: List[EMLVertex] = None,
        k: int = None,
        k_ratio: float = 0.05,
        min_k: int = 3,
        max_k: int = 50,
    ):
        """
        Args:
            edges: 超边列表
            vertices: 顶点列表 (用于 ℐ 信息)
            k: 边界层大小 (None=自动根据 k_ratio 计算)
            k_ratio: 边界层占总节点数的比例
            min_k/max_k: k 的上下界
        """
        self.edges = edges
        self.vertices = vertices or []
        self._n_vertices = len(set(n for e in edges for n in e.nodes))

        # 计算 k
        self.k = k or max(min_k, min(max_k, int(self._n_vertices * k_ratio)))

        # 构建节点 → 超边索引
        self._node_to_edges: Dict[int, List[HypEdge]] = defaultdict(list)
        for e in edges:
            for n in e.nodes:
                self._node_to_edges[n].append(e)

        # 计算耦合度
        self._rho: Dict[int, float] = {}
        self._bl: List[int] = []        # 边界层节点 ID 列表
        self._or: List[int] = []        # 外区节点 ID 列表
        self._compute_coupling()

    def _compute_coupling(self):
        """
        计算每个变量的耦合度 ρᵢ。

        ρᵢ = Σ_{e∋vᵢ} |e| · ℐ(e)

        其中 |e| 是超边的元数 (参与节点数)，ℐ(e) 是信息存在度。
        物理意义: 节点参与的语义关系越多元且 ℐ 越高，ρ 越大。
        """
        for vid, incident_edges in self._node_to_edges.items():
            rho = 0.0
            for e in incident_edges:
                rho += e.arity * e.i_val
            self._rho[vid] = rho

        # 按 ρ 降序排列
        sorted_nodes = sorted(self._rho.items(), key=lambda x: x[1], reverse=True)

        # 划分边界层和外区
        self._bl = [vid for vid, _ in sorted_nodes[:self.k]]
        bl_set = set(self._bl)
        self._or = [vid for vid in self._node_to_edges if vid not in bl_set]

    @property
    def boundary_layer(self) -> List[int]:
        """边界层节点 ID 列表 (top-k 高耦合度)"""
        return self._bl

    @property
    def outer_region(self) -> List[int]:
        """外区节点 ID 列表"""
        return self._or

    @property
    def coupling_map(self) -> Dict[int, float]:
        """节点耦合度映射"""
        return dict(self._rho)

    def get_bl_edges(self) -> List[HypEdge]:
        """获取边界层相关的超边"""
        bl_set = set(self._bl)
        bl_edges = []
        for e in self.edges:
            if any(n in bl_set for n in e.nodes):
                bl_edges.append(e)
        return bl_edges

    def get_or_edges(self) -> List[HypEdge]:
        """获取纯外区超边 (所有节点都在外区)"""
        bl_set = set(self._bl)
        or_edges = []
        for e in self.edges:
            if all(n not in bl_set for n in e.nodes):
                or_edges.append(e)
        return or_edges

    def get_mixed_edges(self) -> List[HypEdge]:
        """获取跨区超边 (同时含 BL 和 OR 节点)"""
        bl_set = set(self._bl)
        mixed = []
        for e in self.edges:
            has_bl = any(n in bl_set for n in e.nodes)
            has_or = any(n not in bl_set for n in e.nodes)
            if has_bl and has_or:
                mixed.append(e)
        return mixed

    def decompose(self) -> Dict:
        """
        执行边界层分解，返回分层结果。

        Returns:
            包含 BL, OR, 边分类, 统计信息的字典
        """
        bl_edges = self.get_bl_edges()
        or_edges = self.get_or_edges()
        mixed_edges = self.get_mixed_edges()

        bl_i_sum = sum(e.i_val for e in bl_edges)
        or_i_sum = sum(e.i_val for e in or_edges)
        mixed_i_sum = sum(e.i_val for e in mixed_edges)
        total_i = sum(e.i_val for e in self.edges)

        return {
            'k': self.k,
            'n_total': self._n_vertices,
            'n_bl': len(self._bl),
            'n_or': len(self._or),
            'bl_nodes': self._bl[:20],  # 仅返回前 20 个
            'rho_top10': sorted(self._rho.items(), key=lambda x: x[1], reverse=True)[:10],
            'edges_total': len(self.edges),
            'edges_bl': len(bl_edges),
            'edges_or': len(or_edges),
            'edges_mixed': len(mixed_edges),
            'i_total': total_i,
            'i_bl': bl_i_sum,
            'i_or': or_i_sum,
            'i_mixed': mixed_i_sum,
            'i_bl_ratio': bl_i_sum / max(total_i, 1e-9),
            'fpt_bound': 2 ** min(self.k, 20),  # O(2ᵏ) upper bound
            'is_fpt': self.k <= 20,
        }

    def estimate_complexity(self) -> Dict:
        """
        估算分层求解的计算复杂度。

        GPCT: O(2ᵏ · poly(n))
        若 k ≤ 20 → 2ᵏ ≈ 10⁶，完全可行
        若 k ≤ 15 → 2ᵏ ≈ 3×10⁴，非常快
        若 k → n → 2ⁿ，退化为 NP 难
        """
        k = self.k
        n = self._n_vertices
        complexity = 2 ** min(k, 60)  # 防止溢出

        return {
            'k': k,
            'n': n,
            'complexity_class': 'FPT' if k <= 20 else 'Exp (NP-Hard zone)',
            'operations_2k': complexity if k <= 60 else float('inf'),
            'poly_factor': n * math.log2(n) if n > 0 else 0,
            'feasible': k <= 20,
            'note': (
                'FPT 区 (k≤20): 现有硬件可实时推理' if k <= 20 else
                '边界区 (20<k≤30): 需要更多计算资源' if k <= 30 else
                'NP 难区 (k>30): 需提升 κ 粗粒化或添加更多公理约束'
            ),
        }


def gpct_decompose(
    edges: List[HypEdge],
    vertices: List[EMLVertex] = None,
    k: int = None,
    k_ratio: float = 0.05,
    verbose: bool = False,
) -> Tuple[GpctDecomposer, Dict]:
    """
    GPCT 边界层分解 — EML 瘦身工具箱的第二层降解。

    将超图划分为高耦合边界层 (BL_ε) 和弱耦合外区 (OR)，
    外区在固定 BL_ε 赋值后可退化为多项式时间求解。

    Args:
        edges: 超边列表
        vertices: 顶点列表 (可选)
        k: 边界层大小 (None=自动)
        k_ratio: 自动 k 的比例
        verbose: 是否输出调试信息

    Returns:
        (decomposer, result_dict)
    """
    decomp = GpctDecomposer(
        edges=edges,
        vertices=vertices,
        k=k,
        k_ratio=k_ratio,
    )

    result = decomp.decompose()
    complexity = decomp.estimate_complexity()
    result.update(complexity)

    if verbose:
        print(f"[GPCT] k={result['k']} BL节点={result['n_bl']} OR节点={result['n_or']} "
              f"BL ℐ占比={result['i_bl_ratio']:.1%} "
              f"复杂度={result['complexity_class']} "
              f"({complexity['note']})")

    return decomp, result
