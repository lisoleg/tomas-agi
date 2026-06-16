"""
ITC 虚时计算 (Imaginary Time Computation / Wick 旋转)

量子力学中通过 Wick 旋转 t → -iτ 将实时间演化转为欧氏时间演化:
  e^{-iHt/ℏ} → e^{-Hτ/ℏ}

τ → ∞ 时，e^{-Hτ/ℏ}|Ψ₀⟩ 正比于 H 的基态 = Argmin H。

TOMAS 中 H(F) = -∑_{e∈F} ℐ(e)，最小化 H 等价于最大化 ∑ℐ。

ITC 的三个核心用途:
  1. κ 逆问题 (现象 → 源超边): 退火搜索最高 ℐ 配置 (拟阵基)
  2. BL_ε 识别: 变量关联矩阵主特征向量定位高耦合块
  3. β-重连辅助: 退火隧穿帮助逃出局部 ℐ 假峰

定理 6.2: 变量关联矩阵 A_{ij} = Σ_{e⊃{v_i,v_j}} w_e · ℐ(e)
  主特征向量局部化于高耦合团块 → BL_ε (与 GPCT 的 ρ 排序一致)
"""

import math
import random
import numpy as np
from typing import List, Tuple, Dict, Set, Optional
from collections import defaultdict
from .hyperedge import HypEdge, EMLVertex


class ItcAnneal:
    """
    ITC 模拟退火 — 搜索最高 ℐ 超边子集。

    Hamiltonian: H(F) = -∑_{e∈F} ℐ(e)
    目标: 最小化 H → 最大化 ∑ℐ → 找到拟阵基 B。

    退火参数:
      - T_start: 初始温度 (高 → 接受大部分移动)
      - T_end: 终止温度 (低 → 仅接受改进)
      - cooling_rate: 几何冷却率 (通常 0.95-0.99)
      - tau_max: 最大虚时步数
    """

    def __init__(
        self,
        edges: List[HypEdge],
        vertices: List[EMLVertex] = None,
        T_start: float = 10.0,
        T_end: float = 0.01,
        cooling_rate: float = 0.97,
        tau_max: int = 5000,
        seed: int = 42,
    ):
        """
        Args:
            edges: 超边列表
            vertices: 顶点列表
            T_start: 初始温度
            T_end: 终止温度
            cooling_rate: 冷却率
            tau_max: 最大退火步数
            seed: 随机种子
        """
        self.edges = edges
        self.vertices = vertices or []
        self.T_start = T_start
        self.T_end = T_end
        self.cooling_rate = cooling_rate
        self.tau_max = tau_max

        self.rng = random.Random(seed)
        self._n_vertices = len(set(n for e in edges for n in e.nodes))
        self._association_matrix: Optional[np.ndarray] = None
        self._edge_weights = {e.eid: e.i_val for e in edges}

    def _compute_association_matrix(self) -> np.ndarray:
        """
        构建变量关联矩阵 A。

        A_{ij} = Σ_{e⊃{v_i, v_j}} w_e · ℐ(e)

        使用 Perron-Frobenius 定理: A 对称非负 → 主特征向量分量均为正，
        若存在社区结构，主特征向量幅值集中于高耦合节点块 → BL_ε。

        Returns:
            (n, n) 关联矩阵
        """
        n = self._n_vertices
        A = np.zeros((n, n))

        for e in self.edges:
            nodes = list(e.nodes)
            w = e.i_val  # w_e · ℐ(e) — 这里 w_e = 1
            for i in range(len(nodes)):
                for j in range(i + 1, len(nodes)):
                    u, v = nodes[i], nodes[j]
                    if u < n and v < n:
                        A[u, v] += w
                        A[v, u] += w  # 对称

        self._association_matrix = A
        return A

    def identify_boundary_layer(
        self, k: int = None, k_ratio: float = 0.05
    ) -> List[int]:
        """
        使用 ITC 识别边界层 BL_ε。

        方法: 对关联矩阵 A 求主特征向量 v₁，
        v₁ 的幅值集中于高耦合节点 → 对应 GPCT 的边界层。

        Args:
            k: 边界层大小
            k_ratio: 自动 k 的比例

        Returns:
            边界层节点 ID 列表 (按主特征向量幅值降序)
        """
        A = self._compute_association_matrix()
        n = self._n_vertices

        if n == 0:
            return []

        # 幂迭代法求主特征向量
        v = np.ones(n) / np.sqrt(n)
        for _ in range(200):
            v_new = A @ v
            norm = np.linalg.norm(v_new)
            if norm < 1e-12:
                break
            v_new /= norm
            if np.linalg.norm(v_new - v) < 1e-8:
                v = v_new
                break
            v = v_new

        # 按 |v[i]| 降序排列
        node_magnitudes = [(i, abs(v[i])) for i in range(n)]
        node_magnitudes.sort(key=lambda x: x[1], reverse=True)

        k = k or max(3, min(50, int(n * k_ratio)))
        return [node_id for node_id, _ in node_magnitudes[:k]]

    def _compute_energy(self, active_set: Set[str]) -> float:
        """计算 H(F) = -∑ ℐ(e)，越小越好"""
        return -sum(self._edge_weights[eid] for eid in active_set)

    def _get_neighbor(
        self, active_set: Set[str], all_eids: List[str],
    ) -> Tuple[Set[str], str]:
        """
        生成邻居状态: 随机添加或移除一条边。
        返回 (新状态, 操作描述)。
        """
        new_set = set(active_set)
        inactive = [eid for eid in all_eids if eid not in new_set]

        # 以 0.5 概率尝试添加/移除
        if inactive and (not new_set or self.rng.random() < 0.5):
            # 添加操作
            to_add = self.rng.choice(inactive)
            new_set.add(to_add)
            op = f"+{to_add}"
        elif new_set:
            # 移除操作
            to_remove = self.rng.choice(list(new_set))
            new_set.remove(to_remove)
            op = f"-{to_remove}"
        else:
            op = "noop"

        return new_set, op

    def anneal(
        self, dead_threshold: float = 0.15, verbose: bool = False,
    ) -> Tuple[Set[str], List[float], Dict]:
        """
        执行模拟退火，搜索最高 ℐ 超边子集。

        虚时传播: |Ψ(τ)⟩ = e^{-Hτ/ℏ}|Ψ₀⟩
        τ → ∞ 时收敛到 H 的基态 = Argmax ℐ。

        Returns:
            (best_set, energy_history, stats)
        """
        all_eids = [e.eid for e in self.edges if e.is_alive(dead_threshold)]
        if not all_eids:
            return set(), [], {'converged': True, 'steps': 0, 'best_energy': 0, 'best_i': 0}

        # 初始状态: 随机选择约 50% 的边
        n_initial = max(1, len(all_eids) // 2)
        current_set = set(self.rng.sample(all_eids, n_initial))
        current_energy = self._compute_energy(current_set)

        best_set = set(current_set)
        best_energy = current_energy

        T = self.T_start
        energy_history = [current_energy]
        accepted = 0
        improved = 0
        steps = 0

        while T > self.T_end and steps < self.tau_max:
            steps += 1

            # 生成邻居并计算能量差
            neighbor_set, op = self._get_neighbor(current_set, all_eids)
            neighbor_energy = self._compute_energy(neighbor_set)
            delta_E = neighbor_energy - current_energy

            # Metropolis 接受准则
            # p = min(1, e^{-ΔH·β})  where β = 1/T
            if delta_E <= 0:
                # 改进或持平 → 总是接受
                accept = True
            else:
                # 变差 → 以 e^{-ΔE/T} 概率接受 (热隧穿)
                prob = math.exp(-delta_E / T)
                accept = self.rng.random() < prob

            if accept:
                current_set = neighbor_set
                current_energy = neighbor_energy
                accepted += 1

                if current_energy < best_energy:
                    best_set = set(current_set)
                    best_energy = current_energy
                    improved += 1

            energy_history.append(current_energy)

            # 几何冷却
            T *= self.cooling_rate

        best_i = sum(self._edge_weights[eid] for eid in best_set)

        stats = {
            'converged': T <= self.T_end,
            'steps': steps,
            'accepted': accepted,
            'improved': improved,
            'best_energy': best_energy,
            'best_i': best_i,
            'best_set_size': len(best_set),
            'final_temperature': T,
        }

        if verbose:
            print(f"[ITC退火] {steps}步, T={T:.4f}, "
                  f"接受={accepted}, 改进={improved}, "
                  f"最优∑ℐ={best_i:.4f}, |F|={len(best_set)}")

        return best_set, energy_history, stats

    def beta_reconnect(
        self,
        current_set: Set[str],
        candidate_edges: List[HypEdge],
        beta: float = 1.0,
    ) -> Set[str]:
        """
        β-重连辅助: 在拓扑生长中辅助逃出局部 ℐ 假峰。

        模拟退火 Metropolis: p = min(1, e^{-ΔH·β})
        量子/热隧穿可翻越局部 ℐ 假峰，收敛到更高 ℐ 配置。

        Args:
            current_set: 当前超边集
            candidate_edges: 候选新超边
            beta: 逆温度 β = 1/T

        Returns:
            重连后的超边集
        """
        result = set(current_set)
        current_energy = self._compute_energy(result)

        for e in candidate_edges:
            if e.eid in result:
                continue

            # 计算添加此边后的能量变化
            test_set = result | {e.eid}
            new_energy = self._compute_energy(test_set)
            delta_H = new_energy - current_energy

            # Metropolis 准则
            if delta_H <= 0:
                # 改进 → 接受
                result.add(e.eid)
                current_energy = new_energy
            else:
                # 变差 → 以概率 e^{-ΔH·β} 接受 (热隧穿)
                prob = math.exp(-delta_H * beta)
                if self.rng.random() < prob:
                    result.add(e.eid)
                    current_energy = new_energy

        return result


def itc_anneal(
    edges: List[HypEdge],
    vertices: List[EMLVertex] = None,
    T_start: float = 10.0,
    T_end: float = 0.01,
    cooling_rate: float = 0.97,
    tau_max: int = 5000,
    dead_threshold: float = 0.15,
    identify_bl: bool = True,
    bl_k: int = None,
    verbose: bool = False,
) -> Tuple[Set[str], List[HypEdge], Dict]:
    """
    ITC 虚时退火 — EML 瘦身工具箱的物理搜索引擎。

    用途:
      1. Wick 旋转退火搜索最高 ℐ 配置 (拟阵基)
      2. 关联矩阵主特征向量识别 BL_ε 位置

    Args:
        edges: 超边列表
        vertices: 顶点列表
        T_start: 初始温度
        T_end: 终止温度
        cooling_rate: 冷却率
        tau_max: 最大虚时步数
        dead_threshold: 死零阈值
        identify_bl: 是否识别边界层
        bl_k: 边界层大小
        verbose: 调试输出

    Returns:
        (best_edge_ids_set, remaining_edges, stats)
    """
    annealer = ItcAnneal(
        edges=edges,
        vertices=vertices,
        T_start=T_start,
        T_end=T_end,
        cooling_rate=cooling_rate,
        tau_max=tau_max,
    )

    # 退火搜索
    best_set, energy_history, anneal_stats = annealer.anneal(
        dead_threshold=dead_threshold,
        verbose=verbose,
    )

    # 过滤出保留的边
    edge_map = {e.eid: e for e in edges}
    remaining = [edge_map[eid] for eid in best_set if eid in edge_map]

    # 识别边界层
    bl_nodes = []
    if identify_bl:
        bl_nodes = annealer.identify_boundary_layer(k=bl_k)

    stats = {
        **anneal_stats,
        'original_count': len(edges),
        'pruned_count': len(remaining),
        'compression_ratio': len(remaining) / max(len(edges), 1),
        'bl_identified': bl_nodes[:20] if bl_nodes else [],
        'bl_count': len(bl_nodes),
        'energy_initial': energy_history[0] if energy_history else 0,
        'energy_final': energy_history[-1] if energy_history else 0,
        'energy_history': energy_history[:100],  # 截断
    }

    return best_set, remaining, stats
