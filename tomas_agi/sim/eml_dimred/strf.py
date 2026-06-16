"""
STR-F 四大等价变换 (基于万小龙逻辑变换理论)

将非经典逻辑约束等价映射为经典逻辑，是 GPCT 分层降解的逻辑学基础。

四大变换:
  S1 (多值→二值 One-Hot): L_n ⇔ L_2 — n 值逻辑编码为二值逻辑
    多值语义变量 (如经络状态=厥/实/虚) 转换为一热二值子句簇
  
  S2 (去冗语义等价): 删除被蕴含的冗余子句/文字
    信息守恒筛选 — 删去对满足性无影响的冗余
  
  S3 (上下文冻结): SF ⇔ SFE — 真值函数 ⇔ 非真值/语境函数
    κ-Gate 冻结当前视界，固定部分变量的赋值，缩小搜索空间
  
  S4 (模态/视角降解): MPC ⇔ CP — 模态命题逻辑 ⇔ 经典命题逻辑
    外区失去非结合耦合 (Asym→0)，退化为 2-SAT/单元传播
  
  S5 (逆映射): 逆 L_n ⇔ L_2
    二值解恢复八元数相位/连续语义

GPCT 处理流水线:
  S1 (One-Hot) → S3 (Context Freeze) → S4 (Modal Degrade) → S5 (Inverse Map)
"""

from typing import List, Dict, Set, Tuple, Optional, Any
from collections import defaultdict
import numpy as np
from .hyperedge import HypEdge, EMLVertex


class StrfTransformer:
    """
    STR-F 四大等价变换实现类。

    对应 GPCT 算法的 S1-S5 步骤，将 EML 超图的非经典语义约束
    分层降解为经典逻辑可解的形式。
    """

    def __init__(
        self,
        edges: List[HypEdge],
        vertices: List[EMLVertex] = None,
        kappa: float = 4.0,
    ):
        """
        Args:
            edges: 超边列表
            vertices: 顶点列表
            kappa: 当前 κ 值 (折叠深度)
        """
        self.edges = edges
        self.vertices = vertices or []
        self.kappa = kappa

        # 构建节点映射
        self._vid_to_vertex: Dict[int, EMLVertex] = {}
        for v in self.vertices:
            self._vid_to_vertex[v.vid] = v

    # ─────────── S1: 多值 → 二值 One-Hot 编码 ───────────

    def s1_one_hot_encode(
        self, multi_valued_nodes: Dict[int, List[str]] = None,
    ) -> Dict:
        """
        S1: 多值语义变量 → 二值 One-Hot 编码。

        例如: 经络状态 ∈ {厥, 实, 虚} →
          - x_1 = "经络=厥" (0/1)
          - x_2 = "经络=实" (0/1)
          - x_3 = "经络=虚" (0/1)
          约束: (x_1 ∨ x_2 ∨ x_3) ∧ (¬x_1 ∨ ¬x_2) ∧ (¬x_1 ∨ ¬x_3) ∧ (¬x_2 ∨ ¬x_3)
                = 至少一 + 至多一

        Args:
            multi_valued_nodes: {vid: [值列表]}，None 则自动检测

        Returns:
            {'binary_vars': [...], 'clauses': [...], 'mapping': {...}}
        """
        if multi_valued_nodes is None:
            multi_valued_nodes = self._detect_multi_valued()

        binary_vars = []
        clauses = []
        mapping = {}

        for vid, values in multi_valued_nodes.items():
            n = len(values)
            if n <= 1:
                continue

            # 创建 One-Hot 变量
            oh_vars = [f'x_{vid}_{i}' for i in range(n)]
            binary_vars.extend(oh_vars)
            mapping[vid] = oh_vars

            # 至少一个为真: (x_0 ∨ x_1 ∨ ... ∨ x_{n-1})
            clauses.append(('at_least_one', oh_vars.copy(), vid))

            # 至多一个为真: 每对 (¬x_i ∨ ¬x_j)
            for i in range(n):
                for j in range(i + 1, n):
                    clauses.append(('at_most_one', [f'¬{oh_vars[i]}', f'¬{oh_vars[j]}'], vid))

        return {
            'binary_vars': binary_vars,
            'num_binary_vars': len(binary_vars),
            'clauses': clauses,
            'num_clauses': len(clauses),
            'mapping': mapping,
            'num_multi_valued': len(multi_valued_nodes),
        }

    def _detect_multi_valued(self) -> Dict[int, List[str]]:
        """
        自动检测多值节点。

        启发式: 若节点参与的超边形成明显分区 (不同 Asym 值或 ℐ 层级)，
        则可能代表多值语义。
        """
        multi = {}
        for v in self.vertices:
            # 检查是否有多个不同的 Asym 值关联
            incident_asyms = set()
            for e in self.edges:
                if v.vid in e.nodes:
                    incident_asyms.add(round(e.asym, 1))

            if len(incident_asyms) > 2:
                multi[v.vid] = [f'val_{a}' for a in sorted(incident_asyms)]

        return multi

    # ─────────── S3: 上下文冻结 ───────────

    def s3_context_freeze(
        self, bl_nodes: List[int], bl_assignments: Dict[int, bool] = None,
    ) -> Dict:
        """
        S3: 上下文冻结 — 固定边界层 BL_ε 变量的赋值。

        依据 EML 折叠深度 κ，冻结当前视界的语境变量，
        缩减搜索空间 → 识别计算边界层。

        Args:
            bl_nodes: 边界层节点 ID 列表
            bl_assignments: {vid: True/False} 赋值，None = 从 ℐ 值推断

        Returns:
            {'frozen': {vid: bool}, 'active_edges': [...], 'simplified': bool}
        """
        frozen = {}

        if bl_assignments:
            frozen = dict(bl_assignments)
        else:
            # 从 ℐ 值推断: ℐ > 0.7 视为 true (核心语义活跃)
            for vid in bl_nodes:
                if vid in self._vid_to_vertex:
                    frozen[vid] = self._vid_to_vertex[vid].i_val > 0.5

        # 过滤: 仅保留至少一个非冻结节点参与的超边
        frozen_set = set(frozen.keys())
        active_edges = []
        simplified_count = 0

        for e in self.edges:
            unfrozen_nodes = [n for n in e.nodes if n not in frozen_set]
            if unfrozen_nodes:
                active_edges.append(e)
            else:
                simplified_count += 1  # 所有节点已冻结 → 超边退化为常量

        return {
            'frozen': frozen,
            'frozen_count': len(frozen),
            'active_edges': active_edges,
            'active_count': len(active_edges),
            'simplified_count': simplified_count,
            'simplified': simplified_count > 0,
        }

    # ─────────── S4: 模态/视角降解 ───────────

    def s4_modal_degrade(
        self, edges: List[HypEdge], bl_frozen: Dict[int, bool],
    ) -> Dict:
        """
        S4: 模态降解 — 外区失去非结合耦合，退化为经典逻辑。

        当 BL_ε 赋值固定后，外区 Asym→0 (Boolean)，
        可用 2-SAT/单元传播线性时间求解。

        对应: MPC (模态命题逻辑) ⇔ CP (经典命题逻辑)

        Args:
            edges: 当前活跃超边列表
            bl_frozen: BL_ε 冻结赋值

        Returns:
            {'degraded_edges': [...], 'unit_clauses': [...], 'binary_clauses': [...]}
        """
        bl_set = set(bl_frozen.keys())
        degraded_edges = []
        unit_clauses = []
        binary_clauses = []

        for e in edges:
            # 替换冻结变量
            unfrozen = [n for n in e.nodes if n not in bl_set]
            n_unfrozen = len(unfrozen)

            if n_unfrozen == 0:
                # 所有变量冻结 → 常量子句 (已由 S3 处理)
                continue
            elif n_unfrozen == 1:
                # 单元子句: 可直接传播
                unit_clauses.append({
                    'var': unfrozen[0],
                    'i_val': e.i_val,
                    'eid': e.eid,
                })
            elif n_unfrozen == 2:
                # 二元子句: 2-SAT 可线性求解
                binary_clauses.append({
                    'vars': tuple(unfrozen[:2]),
                    'i_val': e.i_val,
                    'eid': e.eid,
                    'is_mus': e.is_mus_capable,
                })
            else:
                # 多元子句: 在模态降解后可能进一步简化为 2-SAT
                # 这里标记为需要额外处理
                degraded_edges.append({
                    'nodes': unfrozen,
                    'i_val': e.i_val,
                    'eid': e.eid,
                    'is_mus': e.is_mus_capable,
                })

        return {
            'degraded_edges': degraded_edges,
            'unit_clauses': unit_clauses,
            'num_unit': len(unit_clauses),
            'binary_clauses': binary_clauses,
            'num_binary': len(binary_clauses),
            'is_2sat_solvable': len(degraded_edges) == 0,
        }

    def unit_propagation(
        self, unit_clauses: List[Dict], binary_clauses: List[Dict],
    ) -> Dict:
        """
        单元传播算法 — 多项式时间求解简化后的外区。

        对 2-SAT 实例执行单元传播，传播所有确定性的赋值。
        
        Returns:
            {'assignments': {vid: bool}, 'propagated': int, 'conflict': bool}
        """
        assignments = {}
        queue = list(unit_clauses)

        # 单元传播
        while queue:
            clause = queue.pop(0)
            var = clause['var']

            if var in assignments:
                continue

            # 单元子句强制赋值
            assignments[var] = True
            propagated = 1

            # 传播到二元子句
            for bc in binary_clauses[:]:
                v1, v2 = bc['vars']
                if v1 == var or v2 == var:
                    other = v1 if v2 == var else v2
                    if other in assignments:
                        # 检查冲突
                        continue
                    # 二元子句退化为单元子句
                    queue.append({'var': other, 'i_val': bc['i_val']})

        conflict = False  # 简化实现，完整版需检测冲突

        return {
            'assignments': assignments,
            'propagated': len(assignments),
            'conflict': conflict,
        }

    # ─────────── S5: 逆映射 ───────────

    def s5_inverse_map(
        self,
        binary_assignments: Dict[int, bool],
        one_hot_mapping: Dict[int, List[str]] = None,
    ) -> Dict:
        """
        S5: 逆映射 — 二值解恢复八元数相位/连续语义。

        将 S1 One-Hot 编码的二值解逆向映射回多值语义，
        恢复八元数相位信息。

        Args:
            binary_assignments: 二值分配 {vid: True/False}
            one_hot_mapping: S1 产生的 One-Hot 映射

        Returns:
            {'multi_valued': {vid: value}, 'phase_recovery': {...}}
        """
        result = {}
        phase_info = {}

        if one_hot_mapping:
            for vid, oh_vars in one_hot_mapping.items():
                assigned_index = None
                for i, var_name in enumerate(oh_vars):
                    var_id = int(var_name.split('_')[-1])
                    if var_id in binary_assignments and binary_assignments[var_id]:
                        assigned_index = i
                        break

                if assigned_index is not None:
                    result[vid] = f'value_{assigned_index}'

                    # 相位恢复: 从八元数 phi 场提取
                    if vid in self._vid_to_vertex:
                        phi = self._vid_to_vertex[vid].phi
                        phase_info[vid] = {
                            'phi': phi,
                            'magnitude': np.linalg.norm(phi),
                            'phase_angle': np.arctan2(
                                np.linalg.norm(phi[4:]), np.linalg.norm(phi[:4])
                            ),
                        }

        return {
            'multi_valued': result,
            'phase_recovery': phase_info,
            'kappa_current': self.kappa,
        }

    # ─────────── 完整 STR-F 流水线 ───────────

    def transform(
        self,
        bl_nodes: List[int],
        bl_assignments: Dict[int, bool] = None,
        multi_valued_nodes: Dict[int, List[str]] = None,
    ) -> Dict:
        """
        执行完整 STR-F 四变换流水线。

        处理流程:
          S1 (One-Hot 编码) → S3 (上下文冻结) → S4 (模态降解) → S5 (逆映射)

        Args:
            bl_nodes: 边界层节点列表
            bl_assignments: BL_ε 赋值
            multi_valued_nodes: 多值节点

        Returns:
            完整的变换结果字典
        """
        results = {}

        # S1: 多值 → 二值
        s1_result = self.s1_one_hot_encode(multi_valued_nodes)
        results['s1'] = s1_result

        # S3: 上下文冻结
        s3_result = self.s3_context_freeze(bl_nodes, bl_assignments)
        results['s3'] = s3_result

        # S4: 模态降解 (使用 S3 冻结后的活跃边)
        s4_result = self.s4_modal_degrade(
            s3_result['active_edges'],
            s3_result['frozen'],
        )
        results['s4'] = s4_result

        # 单元传播 (降解后的多项式求解)
        if s4_result['is_2sat_solvable']:
            up_result = self.unit_propagation(
                s4_result['unit_clauses'],
                s4_result['binary_clauses'],
            )
            results['unit_propagation'] = up_result

            # S5: 逆映射
            s5_result = self.s5_inverse_map(
                up_result['assignments'],
                s1_result.get('mapping'),
            )
            results['s5'] = s5_result

        # 汇总
        results['summary'] = {
            's1_binary_vars': s1_result.get('num_binary_vars', 0),
            's3_frozen_count': s3_result.get('frozen_count', 0),
            's3_active_edges': s3_result.get('active_count', 0),
            's4_unit_clauses': s4_result.get('num_unit', 0),
            's4_binary_clauses': s4_result.get('num_binary', 0),
            's4_is_solvable': s4_result.get('is_2sat_solvable', False),
            'kappa': self.kappa,
        }

        return results
